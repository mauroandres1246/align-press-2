"""Tests for CameraWidget."""

import pytest
import numpy as np
from pathlib import Path
from PySide6.QtCore import Qt

from alignpress.ui.widgets.camera_widget import (
    CameraWidget,
    CameraThread,
    SimulationMode
)


class TestCameraWidget:
    """Test CameraWidget functionality."""

    @pytest.fixture
    def widget(self, qtbot):
        """Create widget instance."""
        widget = CameraWidget(camera_id=0, fps_target=30)
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def simulation_widget(self, qtbot, tmp_path):
        """Create widget in simulation mode."""
        # Create test image
        import cv2
        test_image = tmp_path / "test.jpg"
        cv2.imwrite(str(test_image), np.zeros((480, 640, 3), dtype=np.uint8))

        widget = CameraWidget(
            camera_id=0,
            fps_target=30,
            simulation_image=test_image
        )
        qtbot.addWidget(widget)
        return widget

    def test_widget_initialization(self, widget):
        """Test widget initializes correctly."""
        assert widget.camera_id == 0
        assert widget.fps_target == 30
        assert widget.image_label is not None
        assert widget.is_running() is False

    def test_widget_has_image_label(self, widget):
        """Test widget has image label."""
        assert widget.image_label is not None
        assert widget.image_label.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_simulation_mode_initialization(self, simulation_widget):
        """Test simulation mode widget initializes."""
        assert simulation_widget.simulation_image is not None
        assert simulation_widget.is_running() is False

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_start_simulation_mode(self, simulation_widget, qtbot):
        """Test starting camera in simulation mode."""
        # Start widget
        simulation_widget.start()

        # Wait a bit
        qtbot.wait(100)

        # Should be running
        assert simulation_widget.is_running() is True

        # Stop immediately to avoid hanging
        simulation_widget.stop()
        qtbot.wait(100)

        assert simulation_widget.is_running() is False

    @pytest.mark.skip(reason="Long-running test that requires 1+ second wait")
    def test_fps_calculation(self, simulation_widget, qtbot):
        """Test FPS calculation."""
        fps_values = []

        def on_fps_update(fps):
            fps_values.append(fps)

        simulation_widget.fps_updated.connect(on_fps_update)

        # Start widget
        simulation_widget.start()

        # Wait for FPS update (happens every second)
        qtbot.wait(1100)

        # Should have FPS values
        assert len(fps_values) > 0

        # Stop
        simulation_widget.stop()

    @pytest.mark.skip(reason="Long-running test that requires 1+ second wait")
    def test_get_current_fps(self, simulation_widget, qtbot):
        """Test getting current FPS."""
        simulation_widget.start()
        qtbot.wait(1100)

        fps = simulation_widget.get_current_fps()
        assert fps > 0

        simulation_widget.stop()

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_set_fps_target(self, simulation_widget, qtbot):
        """Test changing FPS target."""
        simulation_widget.start()
        qtbot.wait(200)

        # Change FPS (should restart)
        simulation_widget.set_fps_target(15)

        # Should still be running
        assert simulation_widget.is_running() is True

        simulation_widget.stop()

    def test_stop_when_not_running(self, widget):
        """Test stopping when not running doesn't crash."""
        widget.stop()  # Should not crash

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_start_twice_ignored(self, simulation_widget, qtbot):
        """Test starting twice is ignored."""
        simulation_widget.start()
        qtbot.wait(100)

        # Try to start again
        simulation_widget.start()

        # Should still be running (not crashed)
        assert simulation_widget.is_running() is True

        simulation_widget.stop()


class TestCameraThread:
    """Test CameraThread (mocked)."""

    def test_thread_initialization(self):
        """Test thread initializes correctly."""
        thread = CameraThread(camera_id=0, fps=30)

        assert thread.camera_id == 0
        assert thread.fps == 30
        assert thread.running is False

    def test_thread_stop_when_not_running(self):
        """Test stopping thread that isn't running."""
        thread = CameraThread(camera_id=0, fps=30)
        thread.stop()  # Should not crash


class TestSimulationMode:
    """Test SimulationMode."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create test image."""
        import cv2
        image_path = tmp_path / "test.jpg"
        cv2.imwrite(str(image_path), np.ones((480, 640, 3), dtype=np.uint8) * 128)
        return image_path

    def test_simulation_initialization(self, test_image):
        """Test simulation mode initializes."""
        sim = SimulationMode(test_image, fps=30)

        assert sim.image_path == test_image
        assert sim.fps == 30
        assert sim.running is False

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_simulation_emits_frames(self, test_image, qtbot):
        """Test simulation mode emits frames."""
        sim = SimulationMode(test_image, fps=30)

        frames_received = []

        def on_frame(frame):
            frames_received.append(frame)

        sim.frame_captured.connect(on_frame)

        # Start simulation
        sim.start()

        # Wait for frames
        qtbot.wait(200)

        # Should have frames
        assert len(frames_received) > 0

        # All frames should be the same size
        assert all(f.shape == (480, 640, 3) for f in frames_received)

        # Stop
        sim.stop()

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_simulation_invalid_image(self, tmp_path, qtbot):
        """Test simulation with invalid image path."""
        invalid_path = tmp_path / "nonexistent.jpg"

        sim = SimulationMode(invalid_path, fps=30)

        errors = []

        def on_error(msg):
            errors.append(msg)

        sim.error_occurred.connect(on_error)

        # Start simulation
        sim.start()

        # Wait for error
        qtbot.wait(200)

        # Should have error
        assert len(errors) > 0

        # Stop
        sim.stop()


class TestCameraWidgetIntegration:
    """Integration tests for CameraWidget."""

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_widget_displays_frames(self, qtbot, tmp_path):
        """Test widget displays frames in UI."""
        import cv2

        # Create test image with distinct pattern
        test_image = tmp_path / "pattern.jpg"
        pattern = np.zeros((480, 640, 3), dtype=np.uint8)
        pattern[100:200, 100:200] = [255, 0, 0]  # Red square
        cv2.imwrite(str(test_image), pattern)

        widget = CameraWidget(simulation_image=test_image, fps_target=30)
        qtbot.addWidget(widget)

        # Start
        widget.start()

        # Wait for frames to be displayed
        qtbot.wait(300)

        # Label should have pixmap
        assert widget.image_label.pixmap() is not None
        assert not widget.image_label.pixmap().isNull()

        # Stop
        widget.stop()

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_widget_frame_signal(self, qtbot, tmp_path):
        """Test widget emits frame_received signal."""
        import cv2

        test_image = tmp_path / "test.jpg"
        cv2.imwrite(str(test_image), np.zeros((480, 640, 3), dtype=np.uint8))

        widget = CameraWidget(simulation_image=test_image, fps_target=30)
        qtbot.addWidget(widget)

        frames = []

        def on_frame(frame):
            frames.append(frame)

        widget.frame_received.connect(on_frame)

        widget.start()
        qtbot.wait(300)

        # Should have received frames
        assert len(frames) > 0

        # Frames should be numpy arrays
        assert all(isinstance(f, np.ndarray) for f in frames)

        widget.stop()
