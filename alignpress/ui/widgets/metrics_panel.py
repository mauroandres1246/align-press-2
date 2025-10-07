"""
Metrics panel widget for displaying real-time logo detection metrics.

Shows status and metrics for each logo with visual indicators (LEDs).
"""

from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from alignpress.core.schemas import LogoResultSchema


class LogoMetricWidget(QWidget):
    """
    Widget displaying metrics for a single logo.

    Shows:
    - LED indicator (🟢🟡🔴⚫)
    - Logo name
    - Deviation (dx, dy)
    - Angle error
    """

    def __init__(self, logo_name: str, parent: Optional[QWidget] = None) -> None:
        """
        Initialize logo metric widget.

        Args:
            logo_name: Name of the logo
            parent: Parent widget
        """
        super().__init__(parent)

        self.logo_name = logo_name
        self._setup_ui()
        self.set_no_detection()

    def _setup_ui(self) -> None:
        """Setup widget UI."""
        # Main frame
        self.frame = QFrame()
        self.frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.frame.setLineWidth(2)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header: LED + Logo name
        header_layout = QHBoxLayout()

        self.led_label = QLabel("⚫")
        led_font = QFont()
        led_font.setPointSize(16)
        self.led_label.setFont(led_font)
        header_layout.addWidget(self.led_label)

        name_label = QLabel(f"<b>{self.logo_name}</b>")
        name_font = QFont()
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Status label
        self.status_label = QLabel("No detectado")
        self.status_label.setStyleSheet("color: #757575; font-size: 9pt;")
        layout.addWidget(self.status_label)

        # Metrics labels
        self.deviation_label = QLabel("Desv: —")
        self.deviation_label.setStyleSheet("font-size: 9pt; font-family: monospace;")
        layout.addWidget(self.deviation_label)

        self.angle_label = QLabel("Ángulo: —")
        self.angle_label.setStyleSheet("font-size: 9pt; font-family: monospace;")
        layout.addWidget(self.angle_label)

        self.frame.setLayout(layout)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)

    def update_result(self, result: LogoResultSchema) -> None:
        """
        Update widget with detection result.

        Args:
            result: Detection result for this logo
        """
        if not result.found:
            self.set_no_detection()
            return

        # Update LED and status based on result status
        if result.status == "PERFECT":
            self.led_label.setText("🟢")
            self.status_label.setText("PERFECTO")
            self.status_label.setStyleSheet("color: green; font-size: 9pt; font-weight: bold;")
            self.frame.setStyleSheet("QFrame { border: 2px solid green; border-radius: 5px; }")
        elif result.status == "GOOD":
            self.led_label.setText("🟡")
            self.status_label.setText("BUENO")
            self.status_label.setStyleSheet("color: #FF9800; font-size: 9pt; font-weight: bold;")
            self.frame.setStyleSheet("QFrame { border: 2px solid #FF9800; border-radius: 5px; }")
        else:
            self.led_label.setText("🔴")
            self.status_label.setText("AJUSTAR")
            self.status_label.setStyleSheet("color: red; font-size: 9pt; font-weight: bold;")
            self.frame.setStyleSheet("QFrame { border: 2px solid red; border-radius: 5px; }")

        # Update metrics
        self.deviation_label.setText(f"Desv: {result.deviation_mm:.2f} mm")
        self.angle_label.setText(f"Ángulo: {result.angle_error_deg:.1f}°")

    def set_no_detection(self) -> None:
        """Set widget to 'no detection' state."""
        self.led_label.setText("⚫")
        self.status_label.setText("No detectado")
        self.status_label.setStyleSheet("color: #757575; font-size: 9pt;")
        self.deviation_label.setText("Desv: —")
        self.angle_label.setText("Ángulo: —")
        self.frame.setStyleSheet("QFrame { border: 2px solid #BDBDBD; border-radius: 5px; }")


class MetricsPanel(QWidget):
    """
    Panel displaying metrics for all logos in composition.

    Shows real-time status and metrics for each logo with visual indicators.
    """

    def __init__(
        self,
        logo_names: list[str],
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize metrics panel.

        Args:
            logo_names: List of logo names to display
            parent: Parent widget
        """
        super().__init__(parent)

        self.logo_names = logo_names
        self.logo_widgets: Dict[str, LogoMetricWidget] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup panel UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Title
        title_label = QLabel("<b>Estado de Logos</b>")
        title_font = QFont()
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Scroll area for logo widgets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(250)
        scroll_area.setMaximumWidth(300)

        container = QWidget()
        self.logos_layout = QVBoxLayout()
        self.logos_layout.setSpacing(10)

        # Create widget for each logo
        for logo_name in self.logo_names:
            widget = LogoMetricWidget(logo_name)
            self.logo_widgets[logo_name] = widget
            self.logos_layout.addWidget(widget)

        # Add stretch at the end
        self.logos_layout.addStretch()

        container.setLayout(self.logos_layout)
        scroll_area.setWidget(container)

        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def update_results(self, results: Dict[str, LogoResultSchema]) -> None:
        """
        Update panel with new detection results.

        Args:
            results: Dictionary mapping logo name to detection result
        """
        for logo_name, widget in self.logo_widgets.items():
            result = results.get(logo_name)
            if result:
                widget.update_result(result)
            else:
                widget.set_no_detection()

    def clear(self) -> None:
        """Clear all metrics and set to 'no detection' state."""
        for widget in self.logo_widgets.values():
            widget.set_no_detection()
