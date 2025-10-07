"""
Advanced debug view for logo detection.

Provides detailed visualization of:
- Detected keypoints
- Feature matches
- ROI boundaries
- Homography transformations
- Detection metrics
"""

from typing import Optional, Dict
import numpy as np
import cv2

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QFormLayout, QCheckBox, QSpinBox,
    QSplitter, QTabWidget, QTextEdit, QComboBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QFont

from alignpress.ui.widgets.camera_widget import CameraWidget
from alignpress.core.composition import Composition
from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import LogoResultSchema


class DebugMetricsPanel(QWidget):
    """Panel showing detailed detection metrics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Detection metrics
        metrics_group = QGroupBox("Detection Metrics")
        metrics_layout = QFormLayout()

        self.keypoints_label = QLabel("—")
        metrics_layout.addRow("Keypoints Detected:", self.keypoints_label)

        self.matches_label = QLabel("—")
        metrics_layout.addRow("Matches Found:", self.matches_label)

        self.inliers_label = QLabel("—")
        metrics_layout.addRow("RANSAC Inliers:", self.inliers_label)

        self.inlier_ratio_label = QLabel("—")
        metrics_layout.addRow("Inlier Ratio:", self.inlier_ratio_label)

        self.reproj_error_label = QLabel("—")
        metrics_layout.addRow("Reproj Error:", self.reproj_error_label)

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # Position metrics
        position_group = QGroupBox("Position & Orientation")
        position_layout = QFormLayout()

        self.position_label = QLabel("—")
        position_layout.addRow("Position (mm):", self.position_label)

        self.deviation_label = QLabel("—")
        position_layout.addRow("Deviation:", self.deviation_label)

        self.angle_label = QLabel("—")
        position_layout.addRow("Angle (deg):", self.angle_label)

        self.angle_error_label = QLabel("—")
        position_layout.addRow("Angle Error:", self.angle_error_label)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # Performance metrics
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout()

        self.processing_time_label = QLabel("—")
        perf_layout.addRow("Processing Time:", self.processing_time_label)

        self.fps_label = QLabel("—")
        perf_layout.addRow("FPS:", self.fps_label)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()
        self.setLayout(layout)

    def update_metrics(self, result: LogoResultSchema):
        """Update metrics from detection result."""
        if not result.found:
            self._clear_metrics()
            return

        # Detection metrics
        if result.total_keypoints:
            self.keypoints_label.setText(str(result.total_keypoints))
        if result.inliers_count:
            self.matches_label.setText(f"{result.inliers_count}")
            self.inliers_label.setText(str(result.inliers_count))
        if result.inlier_ratio:
            self.inlier_ratio_label.setText(f"{result.inlier_ratio:.2%}")
        if result.reproj_error_px:
            self.reproj_error_label.setText(f"{result.reproj_error_px:.2f} px")

        # Position metrics
        if result.position_mm:
            self.position_label.setText(f"({result.position_mm[0]:.1f}, {result.position_mm[1]:.1f})")
        if result.deviation_mm:
            self.deviation_label.setText(f"{result.deviation_mm:.2f} mm")
        if result.angle_deg is not None:
            self.angle_label.setText(f"{result.angle_deg:.1f}°")
        if result.angle_error_deg is not None:
            self.angle_error_label.setText(f"{result.angle_error_deg:.1f}°")

        # Performance
        if result.processing_time_ms:
            self.processing_time_label.setText(f"{result.processing_time_ms:.1f} ms")
            fps = 1000.0 / result.processing_time_ms if result.processing_time_ms > 0 else 0
            self.fps_label.setText(f"{fps:.1f}")

    def _clear_metrics(self):
        """Clear all metrics."""
        self.keypoints_label.setText("—")
        self.matches_label.setText("—")
        self.inliers_label.setText("—")
        self.inlier_ratio_label.setText("—")
        self.reproj_error_label.setText("—")
        self.position_label.setText("—")
        self.deviation_label.setText("—")
        self.angle_label.setText("—")
        self.angle_error_label.setText("—")
        self.processing_time_label.setText("—")
        self.fps_label.setText("—")


class DebugVisualizationPanel(QWidget):
    """Panel with visualization controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Visualization options
        viz_group = QGroupBox("Visualization Options")
        viz_layout = QVBoxLayout()

        self.show_keypoints_cb = QCheckBox("Show Keypoints")
        self.show_keypoints_cb.setChecked(True)
        viz_layout.addWidget(self.show_keypoints_cb)

        self.show_matches_cb = QCheckBox("Show Matches")
        self.show_matches_cb.setChecked(True)
        viz_layout.addWidget(self.show_matches_cb)

        self.show_roi_cb = QCheckBox("Show ROI")
        self.show_roi_cb.setChecked(True)
        viz_layout.addWidget(self.show_roi_cb)

        self.show_expected_cb = QCheckBox("Show Expected Position")
        self.show_expected_cb.setChecked(True)
        viz_layout.addWidget(self.show_expected_cb)

        self.show_homography_cb = QCheckBox("Show Homography Grid")
        self.show_homography_cb.setChecked(False)
        viz_layout.addWidget(self.show_homography_cb)

        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)

        # Logo selection
        logo_group = QGroupBox("Logo Selection")
        logo_layout = QFormLayout()

        self.logo_combo = QComboBox()
        logo_layout.addRow("Active Logo:", self.logo_combo)

        logo_group.setLayout(logo_layout)
        layout.addWidget(logo_group)

        # Detection parameters
        params_group = QGroupBox("Detection Parameters")
        params_layout = QFormLayout()

        self.feature_count_spin = QSpinBox()
        self.feature_count_spin.setRange(100, 5000)
        self.feature_count_spin.setValue(1500)
        params_layout.addRow("Max Features:", self.feature_count_spin)

        self.match_ratio_spin = QSpinBox()
        self.match_ratio_spin.setRange(50, 100)
        self.match_ratio_spin.setValue(75)
        self.match_ratio_spin.setSuffix("%")
        params_layout.addRow("Match Ratio:", self.match_ratio_spin)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        layout.addStretch()
        self.setLayout(layout)

    def get_visualization_flags(self) -> Dict[str, bool]:
        """Get current visualization flags."""
        return {
            "show_keypoints": self.show_keypoints_cb.isChecked(),
            "show_matches": self.show_matches_cb.isChecked(),
            "show_roi": self.show_roi_cb.isChecked(),
            "show_expected": self.show_expected_cb.isChecked(),
            "show_homography": self.show_homography_cb.isChecked(),
        }


class DebugView(QWidget):
    """
    Advanced debug view for logo detection.

    Features:
    - Real-time camera feed with overlays
    - Detailed detection metrics
    - Visualization controls
    - Keypoint and match visualization
    - ROI debugging
    """

    def __init__(
        self,
        composition: Composition,
        detector: Optional[PlanarLogoDetector] = None,
        camera_id: int = 0,
        simulation_image: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)

        self.composition = composition
        self.detector = detector
        self.camera_id = camera_id
        self.simulation_image = simulation_image

        self.current_results: Dict[str, LogoResultSchema] = {}
        self.last_frame: Optional[np.ndarray] = None

        self._setup_ui()

        # Detection timer
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self._run_detection)
        self.detection_interval_ms = 500

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Camera view with tabs
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Camera widget
        self.camera_widget = CameraWidget(
            camera_id=self.camera_id,
            fps_target=30,
            simulation_image=self.simulation_image
        )
        self.camera_widget.frame_received.connect(self._on_frame_received)
        left_layout.addWidget(self.camera_widget)

        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        left_layout.addWidget(self.status_label)

        left_widget.setLayout(left_layout)
        main_splitter.addWidget(left_widget)

        # Right: Controls and metrics tabs
        right_tabs = QTabWidget()

        # Metrics tab
        self.metrics_panel = DebugMetricsPanel()
        right_tabs.addTab(self.metrics_panel, "📊 Metrics")

        # Visualization tab
        self.viz_panel = DebugVisualizationPanel()

        # Populate logo combo
        logo_names = list(self.composition.get_expected_positions().keys())
        self.viz_panel.logo_combo.addItems(logo_names)

        right_tabs.addTab(self.viz_panel, "🎨 Visualization")

        # Raw data tab
        raw_tab = QWidget()
        raw_layout = QVBoxLayout()
        self.raw_data_text = QTextEdit()
        self.raw_data_text.setReadOnly(True)
        self.raw_data_text.setFont(QFont("Courier New", 9))
        raw_layout.addWidget(self.raw_data_text)
        raw_tab.setLayout(raw_layout)
        right_tabs.addTab(raw_tab, "🔍 Raw Data")

        main_splitter.addWidget(right_tabs)

        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)
        self.setLayout(layout)

    def start(self):
        """Start debug view."""
        self.camera_widget.start()
        self.detection_timer.start(self.detection_interval_ms)

    def stop(self):
        """Stop debug view."""
        self.detection_timer.stop()
        self.camera_widget.stop()

    def _on_frame_received(self, frame: np.ndarray):
        """Handle new camera frame."""
        self.last_frame = frame

    def _run_detection(self):
        """Run detection on current frame."""
        if self.last_frame is None or self.detector is None:
            return

        try:
            # Run detection
            results = self.detector.detect(self.last_frame)
            self.current_results = {r.logo_name: r for r in results}

            # Update metrics for selected logo
            selected_logo = self.viz_panel.logo_combo.currentText()
            if selected_logo in self.current_results:
                result = self.current_results[selected_logo]
                self.metrics_panel.update_metrics(result)

                # Update raw data
                self._update_raw_data(result)

            # Update status
            detected_count = sum(1 for r in results if r.found)
            total_count = len(results)
            self.status_label.setText(f"Detected: {detected_count}/{total_count} logos")

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")

    def _update_raw_data(self, result: LogoResultSchema):
        """Update raw data view."""
        import json

        data = {
            "logo_name": result.logo_name,
            "found": result.found,
            "position_mm": result.position_mm,
            "angle_deg": result.angle_deg,
            "deviation_mm": result.deviation_mm,
            "angle_error_deg": result.angle_error_deg,
            "inliers_count": result.inliers_count,
            "total_keypoints": result.total_keypoints,
            "inlier_ratio": result.inlier_ratio,
            "reproj_error_px": result.reproj_error_px,
            "processing_time_ms": result.processing_time_ms,
        }

        formatted = json.dumps(data, indent=2, default=str)
        self.raw_data_text.setPlainText(formatted)
