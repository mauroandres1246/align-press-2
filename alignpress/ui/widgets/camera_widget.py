"""
Camera widget with threaded video capture.

Provides a Qt widget that wraps cv2.VideoCapture with threading support
to avoid blocking the UI thread.
"""

from typing import Optional
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QImage, QPixmap


class CameraThread(QThread):
    """
    Thread for capturing frames from camera.

    Runs in background to avoid blocking UI thread.
    """

    frame_captured = Signal(np.ndarray)  # Emits new frames
    error_occurred = Signal(str)  # Emits error messages

    def __init__(self, camera_id: int = 0, fps: int = 30) -> None:
        """
        Initialize camera thread.

        Args:
            camera_id: Camera device ID
            fps: Target frames per second
        """
        super().__init__()

        self.camera_id = camera_id
        self.fps = fps
        self.running = False
        self.cap: Optional[cv2.VideoCapture] = None

    def run(self) -> None:
        """Run the camera capture loop."""
        self.running = True

        # Open camera
        self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap.isOpened():
            self.error_occurred.emit(f"No se pudo abrir la cámara {self.camera_id}")
            return

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Calculate delay between frames (in ms)
        delay_ms = int(1000 / self.fps)

        while self.running:
            ret, frame = self.cap.read()

            if ret:
                # Emit frame
                self.frame_captured.emit(frame)
            else:
                self.error_occurred.emit("Error al capturar frame de la cámara")
                break

            # Wait to maintain FPS
            self.msleep(delay_ms)

        # Cleanup
        if self.cap:
            self.cap.release()

    def stop(self) -> None:
        """Stop the camera capture."""
        self.running = False
        self.wait()  # Wait for thread to finish


class SimulationMode(QThread):
    """
    Simulation mode that loads a static image.

    Used for testing without physical camera.
    """

    frame_captured = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, image_path: Path, fps: int = 30) -> None:
        """
        Initialize simulation mode.

        Args:
            image_path: Path to image file
            fps: Frames per second to emit
        """
        super().__init__()

        self.image_path = image_path
        self.fps = fps
        self.running = False
        self.image: Optional[np.ndarray] = None

    def run(self) -> None:
        """Run the simulation loop."""
        self.running = True

        # Load image
        self.image = cv2.imread(str(self.image_path))

        if self.image is None:
            self.error_occurred.emit(f"No se pudo cargar la imagen: {self.image_path}")
            return

        # Calculate delay between frames (in ms)
        delay_ms = int(1000 / self.fps)

        while self.running:
            # Emit same frame repeatedly
            self.frame_captured.emit(self.image.copy())

            # Wait to maintain FPS
            self.msleep(delay_ms)

    def stop(self) -> None:
        """Stop the simulation."""
        self.running = False
        self.wait()


class CameraWidget(QWidget):
    """
    Widget that displays camera feed.

    Supports both real camera and simulation mode.
    """

    frame_received = Signal(np.ndarray)  # Emitted when new frame is received
    fps_updated = Signal(float)  # Emitted with current FPS

    def __init__(
        self,
        camera_id: int = 0,
        fps_target: int = 30,
        simulation_image: Optional[Path] = None,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        Initialize camera widget.

        Args:
            camera_id: Camera device ID (ignored if simulation_image is set)
            fps_target: Target frames per second
            simulation_image: If set, uses simulation mode with this image
            parent: Parent widget
        """
        super().__init__(parent)

        self.camera_id = camera_id
        self.fps_target = fps_target
        self.simulation_image = simulation_image
        self.thread: Optional[QThread] = None

        # FPS calculation
        self.frame_count = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self._update_fps)
        self.current_fps = 0.0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Label to display camera feed
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setScaledContents(False)

        layout.addWidget(self.image_label)
        self.setLayout(layout)

    def start(self) -> None:
        """Start camera capture."""
        if self.thread and self.thread.isRunning():
            return

        # Create appropriate thread
        if self.simulation_image:
            self.thread = SimulationMode(self.simulation_image, self.fps_target)
        else:
            self.thread = CameraThread(self.camera_id, self.fps_target)

        # Connect signals
        self.thread.frame_captured.connect(self._on_frame_captured)
        self.thread.error_occurred.connect(self._on_error)

        # Start thread
        self.thread.start()

        # Start FPS timer (update every second)
        self.fps_timer.start(1000)

    def stop(self) -> None:
        """Stop camera capture."""
        if self.thread:
            self.thread.stop()
            self.thread = None

        self.fps_timer.stop()

    def _on_frame_captured(self, frame: np.ndarray) -> None:
        """
        Handle captured frame.

        Args:
            frame: Captured frame (BGR format)
        """
        self.frame_count += 1

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Convert to QImage
        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width
        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Display
        self.image_label.setPixmap(scaled_pixmap)

        # Emit signal for external processing
        self.frame_received.emit(frame)

    def _on_error(self, error_msg: str) -> None:
        """
        Handle error from camera thread.

        Args:
            error_msg: Error message
        """
        self.image_label.setText(f"Error: {error_msg}")
        self.stop()

    def _update_fps(self) -> None:
        """Update FPS calculation."""
        self.current_fps = float(self.frame_count)
        self.frame_count = 0

        self.fps_updated.emit(self.current_fps)

    def get_current_fps(self) -> float:
        """
        Get current FPS.

        Returns:
            Current frames per second
        """
        return self.current_fps

    def is_running(self) -> bool:
        """
        Check if camera is running.

        Returns:
            True if camera is capturing
        """
        return self.thread is not None and self.thread.isRunning()

    def set_fps_target(self, fps: int) -> None:
        """
        Set target FPS.

        Args:
            fps: Target frames per second

        Note:
            Requires restart to take effect
        """
        self.fps_target = fps

        if self.is_running():
            # Restart with new FPS
            self.stop()
            self.start()

    def resizeEvent(self, event) -> None:
        """Handle resize event to scale image."""
        super().resizeEvent(event)

        # Re-scale current pixmap if it exists
        if not self.image_label.pixmap() or self.image_label.pixmap().isNull():
            return

        # This will be handled by next frame capture
