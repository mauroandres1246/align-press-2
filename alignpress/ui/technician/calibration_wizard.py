"""
Calibration wizard for camera calibration using chessboard patterns.

This wizard guides the user through:
1. Configuration (camera, pattern size, square size)
2. Image capture with live preview
3. Calibration calculation
4. Results review and save
"""

from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import numpy as np
import cv2

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QDoubleSpinBox, QPushButton,
    QGroupBox, QFormLayout, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QImage, QPixmap, QFont

from alignpress.cli.calibrate import CameraCalibrator


class CalibrationThread(QThread):
    """Background thread for calibration calculation."""

    progress = Signal(int)  # Progress percentage
    finished = Signal(bool, dict)  # Success, results
    status = Signal(str)  # Status message

    def __init__(self, calibrator: CameraCalibrator):
        super().__init__()
        self.calibrator = calibrator

    def run(self):
        """Run calibration calculation."""
        try:
            self.status.emit("Calculating calibration...")
            self.progress.emit(25)

            success = self.calibrator.calculate_calibration()

            self.progress.emit(75)

            if success:
                results = {
                    "homography": self.calibrator.homography,
                    "mm_per_px": self.calibrator.mm_per_px,
                    "quality_metrics": self.calibrator.quality_metrics
                }
                self.progress.emit(100)
                self.status.emit("Calibration complete!")
                self.finished.emit(True, results)
            else:
                self.progress.emit(0)
                self.status.emit("Calibration failed")
                self.finished.emit(False, {})

        except Exception as e:
            self.progress.emit(0)
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False, {})


class ConfigurationPage(QWizardPage):
    """Page 1: Configuration of calibration parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Calibration Configuration")
        self.setSubTitle("Configure camera and chessboard pattern parameters")

        layout = QVBoxLayout()

        # Camera settings
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QFormLayout()

        self.camera_id_spin = QSpinBox()
        self.camera_id_spin.setRange(0, 10)
        self.camera_id_spin.setValue(0)
        self.camera_id_spin.setToolTip("Camera device ID (usually 0 for default camera)")
        camera_layout.addRow("Camera ID:", self.camera_id_spin)

        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)

        # Pattern settings
        pattern_group = QGroupBox("Chessboard Pattern")
        pattern_layout = QFormLayout()

        self.pattern_width_spin = QSpinBox()
        self.pattern_width_spin.setRange(3, 20)
        self.pattern_width_spin.setValue(9)
        self.pattern_width_spin.setToolTip("Number of inner corners (width)")
        pattern_layout.addRow("Pattern Width (corners):", self.pattern_width_spin)

        self.pattern_height_spin = QSpinBox()
        self.pattern_height_spin.setRange(3, 20)
        self.pattern_height_spin.setValue(6)
        self.pattern_height_spin.setToolTip("Number of inner corners (height)")
        pattern_layout.addRow("Pattern Height (corners):", self.pattern_height_spin)

        self.square_size_spin = QDoubleSpinBox()
        self.square_size_spin.setRange(1.0, 1000.0)
        self.square_size_spin.setValue(25.0)
        self.square_size_spin.setSuffix(" mm")
        self.square_size_spin.setDecimals(2)
        self.square_size_spin.setToolTip("Size of each square in millimeters")
        pattern_layout.addRow("Square Size:", self.square_size_spin)

        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)

        # Info label
        info_label = QLabel(
            "<b>Note:</b> You'll need a printed chessboard pattern. "
            "Standard pattern is 9x6 inner corners with 25mm squares."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #E3F2FD; border-radius: 5px;")
        layout.addWidget(info_label)

        layout.addStretch()
        self.setLayout(layout)

        # Register fields
        self.registerField("camera_id", self.camera_id_spin)
        self.registerField("pattern_width", self.pattern_width_spin)
        self.registerField("pattern_height", self.pattern_height_spin)
        self.registerField("square_size", self.square_size_spin)


class CapturePage(QWizardPage):
    """Page 2: Capture calibration images."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Capture Calibration Images")
        self.setSubTitle("Position the chessboard pattern and capture from different angles")

        self.calibrator: Optional[CameraCalibrator] = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 2px solid #ccc; background-color: #000;")
        layout.addWidget(self.preview_label)

        # Status and controls
        controls_layout = QHBoxLayout()

        # Status
        self.status_label = QLabel("Initializing camera...")
        self.status_label.setStyleSheet("font-size: 11pt; padding: 5px;")
        controls_layout.addWidget(self.status_label)

        controls_layout.addStretch()

        # Capture count
        self.count_label = QLabel("Captured: 0 / 10")
        count_font = QFont()
        count_font.setPointSize(12)
        count_font.setBold(True)
        self.count_label.setFont(count_font)
        controls_layout.addWidget(self.count_label)

        # Capture button
        self.capture_btn = QPushButton("📷 Capture (SPACE)")
        self.capture_btn.setMinimumHeight(50)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.capture_btn.clicked.connect(self._capture_frame)
        self.capture_btn.setEnabled(False)
        controls_layout.addWidget(self.capture_btn)

        layout.addLayout(controls_layout)

        # Instructions
        instructions = QLabel(
            "<b>Instructions:</b><br>"
            "• Position the chessboard pattern so all corners are visible<br>"
            "• When the pattern is detected, press SPACE or the Capture button<br>"
            "• Capture at least 5 images from different angles and distances<br>"
            "• More captures = better calibration accuracy"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("padding: 10px; background-color: #FFF9C4; border-radius: 5px; margin-top: 10px;")
        layout.addWidget(instructions)

        self.setLayout(layout)

    def initializePage(self):
        """Initialize page when shown."""
        # Get configuration from previous page
        camera_id = self.field("camera_id")
        pattern_width = self.field("pattern_width")
        pattern_height = self.field("pattern_height")
        square_size = self.field("square_size")

        # Create calibrator
        self.calibrator = CameraCalibrator(
            camera_id=camera_id,
            pattern_size=(pattern_width, pattern_height),
            square_size_mm=square_size
        )

        # Open camera
        if self.calibrator.open_camera():
            self.status_label.setText("Camera ready - position chessboard pattern")
            self.timer.start(33)  # ~30 FPS
        else:
            self.status_label.setText("❌ Failed to open camera")
            QMessageBox.critical(self, "Camera Error", "Could not open camera. Please check camera connection.")

    def cleanupPage(self):
        """Cleanup when leaving page."""
        self.timer.stop()
        if self.calibrator:
            self.calibrator.close_camera()

    def _update_frame(self):
        """Update camera preview."""
        if not self.calibrator or not self.calibrator.cap:
            return

        ret, frame = self.calibrator.cap.read()
        if not ret:
            return

        # Detect chessboard
        found, corners = self.calibrator.detect_chessboard(frame)

        # Draw visualization
        display_frame = frame.copy()

        if found:
            cv2.drawChessboardCorners(display_frame, self.calibrator.pattern_size, corners, found)
            self.status_label.setText("✅ Pattern detected - press SPACE to capture")
            self.status_label.setStyleSheet("font-size: 11pt; padding: 5px; color: green; font-weight: bold;")
            self.capture_btn.setEnabled(True)
        else:
            self.status_label.setText("Position chessboard pattern in view")
            self.status_label.setStyleSheet("font-size: 11pt; padding: 5px; color: orange;")
            self.capture_btn.setEnabled(False)

        # Convert to QImage and display
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Scale to fit preview label
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled_pixmap)

    def _capture_frame(self):
        """Capture current frame."""
        if not self.calibrator or not self.calibrator.cap:
            return

        ret, frame = self.calibrator.cap.read()
        if not ret:
            return

        found, corners = self.calibrator.detect_chessboard(frame)
        if found:
            self.calibrator.captured_frames.append(frame.copy())
            self.calibrator.captured_corners.append(corners)

            count = len(self.calibrator.captured_frames)
            self.count_label.setText(f"Captured: {count} / 10")

            if count >= 5:
                # Enable next button
                self.completeChanged.emit()

    def isComplete(self):
        """Check if page is complete."""
        if self.calibrator:
            return len(self.calibrator.captured_frames) >= 5
        return False

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key.Key_Space and self.capture_btn.isEnabled():
            self._capture_frame()
        else:
            super().keyPressEvent(event)


class CalculationPage(QWizardPage):
    """Page 3: Calculate calibration."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Calculate Calibration")
        self.setSubTitle("Processing captured images...")

        self.calc_thread: Optional[CalibrationThread] = None
        self.results: dict = {}

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Status
        self.status_label = QLabel("Ready to calculate calibration")
        status_font = QFont()
        status_font.setPointSize(14)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                font-size: 12pt;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Details
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        layout.addWidget(self.details_text)

        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        """Start calibration when page is shown."""
        # Get calibrator from previous page
        prev_page = self.wizard().page(1)  # CapturePage
        calibrator = prev_page.calibrator

        if not calibrator:
            self.status_label.setText("❌ Error: No calibrator available")
            return

        # Start calculation in background thread
        self.calc_thread = CalibrationThread(calibrator)
        self.calc_thread.progress.connect(self.progress_bar.setValue)
        self.calc_thread.status.connect(self.status_label.setText)
        self.calc_thread.finished.connect(self._on_calculation_finished)

        self.calc_thread.start()

        self.details_text.append(f"Processing {len(calibrator.captured_frames)} captured images...")
        self.details_text.append(f"Pattern: {calibrator.pattern_size[0]}x{calibrator.pattern_size[1]}")
        self.details_text.append(f"Square size: {calibrator.square_size_mm}mm\n")

    def _on_calculation_finished(self, success: bool, results: dict):
        """Handle calculation completion."""
        if success:
            self.results = results
            self.details_text.append("\n✅ Calibration successful!")
            self.details_text.append(f"\nResults:")
            self.details_text.append(f"• mm/px: {results['mm_per_px']:.4f}")
            self.details_text.append(f"• Reprojection error: {results['quality_metrics']['reproj_error_px']:.2f} px")
            self.details_text.append(f"• Captures used: {results['quality_metrics']['captures_used']}")
            self.completeChanged.emit()
        else:
            self.details_text.append("\n❌ Calibration failed!")
            self.details_text.append("Please go back and capture more images.")

    def isComplete(self):
        """Check if calculation is complete."""
        return bool(self.results)


class ResultsPage(QWizardPage):
    """Page 4: Review results and save."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Calibration Results")
        self.setSubTitle("Review and save calibration data")

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Results display
        results_group = QGroupBox("Calibration Data")
        results_layout = QFormLayout()

        self.mm_per_px_label = QLabel("—")
        results_layout.addRow("Scale (mm/px):", self.mm_per_px_label)

        self.error_label = QLabel("—")
        results_layout.addRow("Reprojection Error:", self.error_label)

        self.captures_label = QLabel("—")
        results_layout.addRow("Captures Used:", self.captures_label)

        self.homography_label = QLabel("—")
        results_layout.addRow("Homography Available:", self.homography_label)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Save section
        save_group = QGroupBox("Save Calibration")
        save_layout = QVBoxLayout()

        save_btn = QPushButton("💾 Save Calibration Data")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save_calibration)
        save_layout.addWidget(save_btn)

        self.save_status_label = QLabel("Not saved yet")
        self.save_status_label.setStyleSheet("padding: 5px; font-style: italic;")
        save_layout.addWidget(self.save_status_label)

        save_group.setLayout(save_layout)
        layout.addWidget(save_group)

        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        """Populate results when page is shown."""
        # Get results from calculation page
        calc_page = self.wizard().page(2)  # CalculationPage
        results = calc_page.results

        if results:
            self.mm_per_px_label.setText(f"{results['mm_per_px']:.6f}")
            self.error_label.setText(f"{results['quality_metrics']['reproj_error_px']:.2f} pixels")
            self.captures_label.setText(str(results['quality_metrics']['captures_used']))
            self.homography_label.setText("✅ Yes" if results['homography'] is not None else "❌ No")

    def _save_calibration(self):
        """Save calibration data to file."""
        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Calibration",
            f"calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npz",
            "NumPy Archive (*.npz)"
        )

        if not file_path:
            return

        # Get results
        calc_page = self.wizard().page(2)
        results = calc_page.results

        try:
            # Save homography and scale
            np.savez(
                file_path,
                homography=results['homography'],
                mm_per_px=results['mm_per_px'],
                reproj_error_px=results['quality_metrics']['reproj_error_px'],
                captures_used=results['quality_metrics']['captures_used']
            )

            self.save_status_label.setText(f"✅ Saved to: {file_path}")
            self.save_status_label.setStyleSheet("padding: 5px; color: green; font-weight: bold;")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save calibration:\n{str(e)}")


class CalibrationWizard(QWizard):
    """
    Wizard for camera calibration process.

    Guides the user through:
    1. Configuration
    2. Image capture
    3. Calculation
    4. Results and save
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Camera Calibration Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(900, 700)

        # Add pages
        self.addPage(ConfigurationPage())
        self.addPage(CapturePage())
        self.addPage(CalculationPage())
        self.addPage(ResultsPage())

        # Configure buttons
        self.setButtonText(QWizard.WizardButton.FinishButton, "Close")
