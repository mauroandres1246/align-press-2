"""
Validation checklist dialog for operator mode.

Shows final validation results and allows operator to confirm or reject the job.
"""

from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget,
    QTextEdit, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
import cv2
import numpy as np

from alignpress.core.schemas import LogoResultSchema
from alignpress.core.composition import Composition
from alignpress.core.job_card import JobCard


class ValidationChecklistDialog(QDialog):
    """
    Dialog displaying validation checklist and job confirmation.

    Shows:
    - List of logos with detection status
    - Detailed metrics for each logo
    - Snapshot preview
    - Confirm/Reject buttons
    """

    job_confirmed = Signal(JobCard)  # Emitted when job is confirmed with JobCard
    job_rejected = Signal()  # Emitted when operator rejects and goes back

    def __init__(
        self,
        composition: Composition,
        results: Dict[str, LogoResultSchema],
        snapshot: Optional[np.ndarray] = None,
        operator: str = "Unknown",
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize validation checklist dialog.

        Args:
            composition: Composition used for detection
            results: Detection results by logo name
            snapshot: Optional snapshot image (BGR)
            operator: Operator name/ID
            parent: Parent widget
        """
        super().__init__(parent)

        self.composition = composition
        self.results = results
        self.snapshot = snapshot
        self.operator = operator
        self.job_card: Optional[JobCard] = None

        # Count statistics
        self.total_logos = len(composition.get_expected_positions())
        self.detected_count = sum(1 for r in results.values() if r.found)
        self.perfect_count = sum(1 for r in results.values() if r.status == "PERFECT")
        self.good_count = sum(1 for r in results.values() if r.status == "GOOD")
        self.needs_adjustment = self.detected_count - self.perfect_count - self.good_count

        self._setup_ui()
        self._populate_results()

    def _setup_ui(self) -> None:
        """Setup dialog UI."""
        self.setWindowTitle("Validación de Logos")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Validación de Detección de Logos")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Summary panel
        summary_group = self._create_summary_panel()
        layout.addWidget(summary_group)

        # Results list (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)

        self.results_container = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_container.setLayout(self.results_layout)
        scroll_area.setWidget(self.results_container)

        layout.addWidget(scroll_area)

        # Notes section
        notes_group = QGroupBox("Notas del Operador (Opcional)")
        notes_layout = QVBoxLayout()
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Agregar observaciones o comentarios...")
        self.notes_edit.setMaximumHeight(80)
        notes_layout.addWidget(self.notes_edit)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Back button
        back_btn = QPushButton("← Volver")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 10px 20px;
                font-size: 12pt;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        back_btn.clicked.connect(self._on_reject)
        button_layout.addWidget(back_btn)

        # Confirm button
        self.confirm_btn = QPushButton("✓ Confirmar y Guardar")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)

        # Enable confirm only if all logos detected
        self.confirm_btn.setEnabled(self.detected_count == self.total_logos)

        button_layout.addWidget(self.confirm_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _create_summary_panel(self) -> QGroupBox:
        """
        Create summary statistics panel.

        Returns:
            Summary panel group box
        """
        group = QGroupBox("Resumen")
        layout = QHBoxLayout()

        # Detection count
        detection_label = QLabel(f"Detectados: {self.detected_count}/{self.total_logos}")
        detection_font = QFont()
        detection_font.setPointSize(14)
        detection_font.setBold(True)
        detection_label.setFont(detection_font)
        layout.addWidget(detection_label)

        layout.addStretch()

        # Status indicators
        if self.perfect_count > 0:
            perfect_label = QLabel(f"🟢 Perfectos: {self.perfect_count}")
            perfect_label.setStyleSheet("font-size: 12pt; color: green; font-weight: bold;")
            layout.addWidget(perfect_label)

        if self.good_count > 0:
            good_label = QLabel(f"🟡 Buenos: {self.good_count}")
            good_label.setStyleSheet("font-size: 12pt; color: #FF9800; font-weight: bold;")
            layout.addWidget(good_label)

        if self.needs_adjustment > 0:
            adjust_label = QLabel(f"🔴 Requieren Ajuste: {self.needs_adjustment}")
            adjust_label.setStyleSheet("font-size: 12pt; color: red; font-weight: bold;")
            layout.addWidget(adjust_label)

        missing_count = self.total_logos - self.detected_count
        if missing_count > 0:
            missing_label = QLabel(f"⚫ No Detectados: {missing_count}")
            missing_label.setStyleSheet("font-size: 12pt; color: #424242; font-weight: bold;")
            layout.addWidget(missing_label)

        group.setLayout(layout)
        return group

    def _populate_results(self) -> None:
        """Populate results list with logo items."""
        expected_positions = self.composition.get_expected_positions()

        for logo_name in sorted(expected_positions.keys()):
            item = self._create_logo_item(logo_name)
            self.results_layout.addWidget(item)

        # Add stretch at the end
        self.results_layout.addStretch()

    def _create_logo_item(self, logo_name: str) -> QFrame:
        """
        Create a single logo item widget.

        Args:
            logo_name: Name of the logo

        Returns:
            Frame containing logo item
        """
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout()

        # Status emoji
        result = self.results.get(logo_name)
        if result is None or not result.found:
            emoji = "⚫"
            status_text = "NO DETECTADO"
            status_color = "#424242"
            metrics_text = "—"
        else:
            if result.status == "PERFECT":
                emoji = "🟢"
                status_text = "PERFECTO"
                status_color = "green"
            elif result.status == "GOOD":
                emoji = "🟡"
                status_text = "BUENO"
                status_color = "#FF9800"
            else:
                emoji = "🔴"
                status_text = "REQUIERE AJUSTE"
                status_color = "red"

            # Metrics
            metrics_text = f"Desv: {result.deviation_mm:.2f}mm | Ángulo: {result.angle_error_deg:.1f}°"

        # Emoji label
        emoji_label = QLabel(emoji)
        emoji_font = QFont()
        emoji_font.setPointSize(20)
        emoji_label.setFont(emoji_font)
        layout.addWidget(emoji_label)

        # Logo name
        name_label = QLabel(f"<b>{logo_name}</b>")
        name_font = QFont()
        name_font.setPointSize(12)
        name_label.setFont(name_font)
        name_label.setMinimumWidth(150)
        layout.addWidget(name_label)

        # Status
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 11pt;")
        status_label.setMinimumWidth(150)
        layout.addWidget(status_label)

        # Metrics
        metrics_label = QLabel(metrics_text)
        metrics_label.setStyleSheet("font-size: 10pt; color: #555;")
        layout.addWidget(metrics_label)

        layout.addStretch()

        frame.setLayout(layout)
        return frame

    def _on_confirm(self) -> None:
        """Handle confirm button click - create and save job card."""
        # Create job card
        self.job_card = JobCard.create(
            composition=self.composition,
            operator=self.operator
        )

        # Add results (convert dict to list)
        results_list = list(self.results.values())
        self.job_card.add_results(results_list)

        # Save snapshot if available
        snapshot_path = None
        if self.snapshot is not None:
            # Create snapshots directory
            snapshots_dir = Path("logs/snapshots")
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            # Save snapshot with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_filename = f"snapshot_{self.job_card.job_id}_{timestamp}.jpg"
            snapshot_path = snapshots_dir / snapshot_filename

            cv2.imwrite(str(snapshot_path), self.snapshot)

        # Finalize job card
        notes = self.notes_edit.toPlainText()
        self.job_card.finalize(snapshot_path=snapshot_path, notes=notes)

        # Save job card
        self._save_job_card()

        # Emit signal and close
        self.job_confirmed.emit(self.job_card)
        self.accept()

    def _save_job_card(self) -> None:
        """Save job card to disk."""
        if self.job_card is None:
            return

        # Create jobs directory
        jobs_dir = Path("logs/jobs")
        jobs_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        output_path = jobs_dir / f"{self.job_card.job_id}.json"

        try:
            self.job_card.save(output_path)
        except Exception as e:
            print(f"Error saving job card: {e}")

    def _on_reject(self) -> None:
        """Handle back/reject button click."""
        self.job_rejected.emit()
        self.reject()

    def get_job_card(self) -> Optional[JobCard]:
        """
        Get the created job card (after confirmation).

        Returns:
            JobCard if confirmed, None otherwise
        """
        return self.job_card
