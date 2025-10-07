"""
Live view widget for operator mode.

Displays camera feed with overlays for target positions and detections.
"""

from typing import Optional, Dict, Tuple, List
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont

from alignpress.ui.widgets.camera_widget import CameraWidget
from alignpress.ui.widgets.metrics_panel import MetricsPanel
from alignpress.core.composition import Composition
from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import LogoResultSchema
from alignpress.utils.image_utils import mm_to_px, px_to_mm


class LiveViewWidget(QWidget):
    """
    Widget displaying live camera feed with detection overlays.

    Shows:
    - Camera feed
    - Target positions (ghost overlay)
    - Real-time detections
    - Validation button
    """

    validation_requested = Signal()  # Emitted when user wants to validate

    def __init__(
        self,
        composition: Composition,
        camera_id: int = 0,
        simulation_image: Optional[Path] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize live view widget.

        Args:
            composition: Composition with platen, style, variant
            camera_id: Camera device ID
            simulation_image: Optional image for simulation mode
            parent: Parent widget
        """
        super().__init__(parent)

        self.composition = composition
        self.camera_id = camera_id
        self.simulation_image = simulation_image

        # Detector
        self.detector: Optional[PlanarLogoDetector] = None
        self.current_results: Dict[str, LogoResultSchema] = {}

        # Detection state
        self.detection_enabled = True
        self.detection_interval_ms = 500  # Run detection every 500ms
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self._run_detection)

        # Last frame for processing
        self.last_frame: Optional[np.ndarray] = None

        self._setup_ui()
        self._initialize_detector()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Content layout (camera + metrics panel)
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Camera widget with overlay
        self.camera_widget = CameraWidget(
            camera_id=self.camera_id,
            fps_target=30,
            simulation_image=self.simulation_image
        )
        self.camera_widget.frame_received.connect(self._on_frame_received)
        content_layout.addWidget(self.camera_widget, stretch=3)

        # Metrics panel (right side)
        logo_names = list(self.composition.get_expected_positions().keys())
        self.metrics_panel = MetricsPanel(logo_names)
        content_layout.addWidget(self.metrics_panel, stretch=1)

        main_layout.addLayout(content_layout)

        # Bottom toolbar
        toolbar_layout = QHBoxLayout()

        # Status label
        self.status_label = QLabel("Inicializando...")
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold;")
        toolbar_layout.addWidget(self.status_label)

        toolbar_layout.addStretch()

        # Validate button
        self.validate_btn = QPushButton("✓ Validar Todo")
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-size: 14pt;
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
        self.validate_btn.clicked.connect(self._on_validate_clicked)
        self.validate_btn.setEnabled(False)
        toolbar_layout.addWidget(self.validate_btn)

        main_layout.addLayout(toolbar_layout)
        self.setLayout(main_layout)

    def _initialize_detector(self) -> None:
        """Initialize detector with composition config."""
        try:
            config = self.composition.to_detector_config()

            # Load homography if exists
            homography_path = Path(self.composition.get_calibration_path())
            if homography_path.exists():
                data = np.load(str(homography_path))
                config["plane"]["homography"] = data["homography"]

            self.detector = PlanarLogoDetector(config)
            self.status_label.setText("Listo - Esperando detecciones...")

        except Exception as e:
            self.status_label.setText(f"Error inicializando detector: {e}")
            self.status_label.setStyleSheet("padding: 5px; font-weight: bold; color: red;")

    def start(self) -> None:
        """Start camera and detection."""
        self.camera_widget.start()
        self.detection_timer.start(self.detection_interval_ms)

    def stop(self) -> None:
        """Stop camera and detection."""
        self.camera_widget.stop()
        self.detection_timer.stop()

    def __del__(self) -> None:
        """Destructor - ensure camera thread is stopped."""
        self.stop()

    def _on_frame_received(self, frame: np.ndarray) -> None:
        """
        Handle new frame from camera.

        Args:
            frame: Camera frame (BGR)
        """
        self.last_frame = frame.copy()

    def _run_detection(self) -> None:
        """Run detection on last frame."""
        if self.last_frame is None or self.detector is None:
            return

        if not self.detection_enabled:
            return

        try:
            # Run detection
            results = self.detector.detect(self.last_frame)

            # Update results
            self.current_results = {r.logo_name: r for r in results}

            # Draw overlays
            frame_with_overlay = self._draw_overlays(self.last_frame.copy())

            # Update camera widget display
            self._update_camera_display(frame_with_overlay)

            # Update metrics panel
            self.metrics_panel.update_results(self.current_results)

            # Update status
            self._update_status()

        except Exception as e:
            self.status_label.setText(f"Error en detección: {e}")
            self.status_label.setStyleSheet("padding: 5px; font-weight: bold; color: red;")

    def _draw_overlays(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection overlays on frame.

        Args:
            frame: Input frame

        Returns:
            Frame with overlays
        """
        # Draw target positions (ghost)
        frame = self._draw_target_positions(frame)

        # Draw detections
        frame = self._draw_detections(frame)

        return frame

    def _draw_target_positions(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw target positions as semi-transparent circles.

        Args:
            frame: Input frame

        Returns:
            Frame with target overlays
        """
        if self.detector is None:
            return frame

        overlay = frame.copy()
        expected_positions = self.composition.get_expected_positions()

        for logo_name, pos_mm in expected_positions.items():
            # Convert mm to px
            scale = self.detector.config.plane.mm_per_px
            pos_px = mm_to_px(pos_mm[0], pos_mm[1], scale)

            # Draw semi-transparent circle
            cv2.circle(
                overlay,
                (int(pos_px[0]), int(pos_px[1])),
                20,
                (255, 255, 255),  # White
                2,
                cv2.LINE_AA
            )

            # Draw crosshair
            cv2.line(
                overlay,
                (int(pos_px[0]) - 10, int(pos_px[1])),
                (int(pos_px[0]) + 10, int(pos_px[1])),
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )
            cv2.line(
                overlay,
                (int(pos_px[0]), int(pos_px[1]) - 10),
                (int(pos_px[0]), int(pos_px[1]) + 10),
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

            # Draw label
            cv2.putText(
                overlay,
                logo_name,
                (int(pos_px[0]) + 25, int(pos_px[1]) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Blend overlay with frame
        alpha = 0.5
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        return frame

    def _draw_detections(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw detection results with color coding.

        Args:
            frame: Input frame

        Returns:
            Frame with detection overlays
        """
        if self.detector is None:
            return frame

        for logo_name, result in self.current_results.items():
            if not result.found:
                continue

            # Color based on status
            if result.status == "PERFECT":
                color = (0, 255, 0)  # Green
            elif result.status == "GOOD":
                color = (255, 255, 0)  # Yellow
            else:
                color = (0, 0, 255)  # Red

            # Convert detected position to px
            scale = self.detector.config.plane.mm_per_px
            pos_px = mm_to_px(result.detected_position[0], result.detected_position[1], scale)

            # Draw filled circle
            cv2.circle(
                frame,
                (int(pos_px[0]), int(pos_px[1])),
                15,
                color,
                -1,
                cv2.LINE_AA
            )

            # Draw border
            cv2.circle(
                frame,
                (int(pos_px[0]), int(pos_px[1])),
                15,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

            # Draw deviation vector
            expected_mm = self.composition.get_expected_positions()[logo_name]
            expected_px = mm_to_px(expected_mm[0], expected_mm[1], scale)

            cv2.arrowedLine(
                frame,
                (int(expected_px[0]), int(expected_px[1])),
                (int(pos_px[0]), int(pos_px[1])),
                (255, 0, 255),
                2,
                cv2.LINE_AA,
                tipLength=0.3
            )

            # Draw metrics
            metrics_text = f"{result.deviation_mm:.1f}mm"
            cv2.putText(
                frame,
                metrics_text,
                (int(pos_px[0]) + 20, int(pos_px[1]) + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA
            )

        return frame

    def _update_camera_display(self, frame: np.ndarray) -> None:
        """
        Update camera widget with processed frame.

        Args:
            frame: Processed frame with overlays
        """
        # Convert to RGB and update display
        from PySide6.QtGui import QImage, QPixmap

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_widget.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.camera_widget.image_label.setPixmap(scaled_pixmap)

    def _update_status(self) -> None:
        """Update status label and validate button."""
        expected_count = len(self.composition.get_expected_positions())
        detected_count = sum(1 for r in self.current_results.values() if r.found)
        perfect_count = sum(1 for r in self.current_results.values() if r.status == "PERFECT")
        good_count = sum(1 for r in self.current_results.values() if r.status == "GOOD")

        # Update status text
        status_parts = []
        if detected_count > 0:
            status_parts.append(f"Detectados: {detected_count}/{expected_count}")
            if perfect_count > 0:
                status_parts.append(f"🟢 {perfect_count}")
            if good_count > 0:
                status_parts.append(f"🟡 {good_count}")
            if detected_count - perfect_count - good_count > 0:
                status_parts.append(f"🔴 {detected_count - perfect_count - good_count}")
        else:
            status_parts.append("Esperando detecciones...")

        self.status_label.setText(" | ".join(status_parts))
        self.status_label.setStyleSheet("padding: 5px; font-weight: bold;")

        # Enable validate button if all logos detected
        self.validate_btn.setEnabled(detected_count == expected_count)

    def _on_validate_clicked(self) -> None:
        """Handle validate button click."""
        self.validation_requested.emit()

    def get_current_results(self) -> Dict[str, LogoResultSchema]:
        """
        Get current detection results.

        Returns:
            Dictionary mapping logo name to result
        """
        return self.current_results.copy()

    def set_detection_enabled(self, enabled: bool) -> None:
        """
        Enable/disable detection.

        Args:
            enabled: Whether to enable detection
        """
        self.detection_enabled = enabled
