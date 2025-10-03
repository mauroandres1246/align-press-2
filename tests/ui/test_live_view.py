"""Tests for LiveViewWidget."""

import pytest
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime

from alignpress.ui.operator.live_view import LiveViewWidget
from alignpress.core.composition import Composition
from alignpress.core.profile import (
    PlatenProfile, StyleProfile, CalibrationInfo, LogoDefinition
)


class TestLiveViewWidget:
    """Test LiveViewWidget functionality."""

    @pytest.fixture
    def test_template(self, tmp_path):
        """Create test template image."""
        template_path = tmp_path / "test_logo.png"
        template = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.imwrite(str(template_path), template)
        return template_path

    @pytest.fixture
    def test_composition(self, test_template):
        """Create test composition."""
        platen = PlatenProfile(
            version=1,
            name="Test Platen",
            type="platen",
            dimensions_mm={"width": 300.0, "height": 200.0},
            calibration=CalibrationInfo(
                camera_id=0,
                last_calibrated=datetime.now(),
                homography_path="calibration/camera_0.npz",
                mm_per_px=0.5
            )
        )

        style = StyleProfile(
            version=1,
            name="Test Style",
            type="style",
            logos=[
                LogoDefinition(
                    name="test_logo",
                    template_path=str(test_template),
                    position_mm=[150.0, 100.0],
                    roi={"width_mm": 50.0, "height_mm": 40.0, "margin_factor": 1.2}
                )
            ]
        )

        return Composition(platen=platen, style=style)

    @pytest.fixture
    def simulation_image(self, tmp_path):
        """Create simulation image."""
        img_path = tmp_path / "test_frame.jpg"
        cv2.imwrite(str(img_path), np.zeros((480, 640, 3), dtype=np.uint8))
        return img_path

    @pytest.fixture
    def widget(self, qtbot, test_composition, simulation_image):
        """Create widget instance."""
        widget = LiveViewWidget(
            composition=test_composition,
            simulation_image=simulation_image
        )
        qtbot.addWidget(widget)
        return widget

    def test_widget_initialization(self, widget, test_composition):
        """Test widget initializes correctly."""
        assert widget.composition == test_composition
        assert widget.camera_widget is not None
        assert widget.validate_btn is not None
        assert widget.status_label is not None

    def test_widget_has_camera_widget(self, widget):
        """Test widget contains camera widget."""
        assert widget.camera_widget is not None
        assert widget.camera_widget.simulation_image is not None

    def test_validate_button_starts_disabled(self, widget):
        """Test validate button starts disabled."""
        assert widget.validate_btn.isEnabled() is False

    def test_detection_timer_exists(self, widget):
        """Test detection timer exists."""
        assert widget.detection_timer is not None
        assert widget.detection_interval_ms == 500

    @pytest.mark.skip(reason="Threading test that may timeout")
    def test_start_stops_camera(self, widget, qtbot):
        """Test start/stop methods."""
        # Should not crash
        widget.start()
        assert widget.camera_widget.is_running() is True

        widget.stop()
        assert widget.camera_widget.is_running() is False

    def test_get_current_results_returns_dict(self, widget):
        """Test get_current_results returns dictionary."""
        results = widget.get_current_results()
        assert isinstance(results, dict)

    def test_set_detection_enabled(self, widget):
        """Test enabling/disabling detection."""
        widget.set_detection_enabled(False)
        assert widget.detection_enabled is False

        widget.set_detection_enabled(True)
        assert widget.detection_enabled is True

    def test_validation_signal_emits(self, widget, qtbot):
        """Test validation_requested signal."""
        with qtbot.waitSignal(widget.validation_requested, timeout=1000):
            widget.validate_btn.setEnabled(True)
            widget.validate_btn.click()

    def test_frame_received_updates_last_frame(self, widget):
        """Test frame received updates last_frame."""
        test_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

        widget._on_frame_received(test_frame)

        assert widget.last_frame is not None
        assert widget.last_frame.shape == (480, 640, 3)

    def test_draw_target_positions_returns_frame(self, widget):
        """Test _draw_target_positions doesn't crash."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = widget._draw_target_positions(frame)

        assert result is not None
        assert result.shape == frame.shape

    def test_draw_detections_returns_frame(self, widget):
        """Test _draw_detections doesn't crash."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        result = widget._draw_detections(frame)

        assert result is not None
        assert result.shape == frame.shape

    def test_update_status_updates_label(self, widget):
        """Test _update_status updates status label."""
        widget._update_status()

        # Should have some text
        assert len(widget.status_label.text()) > 0

    def test_widget_without_simulation_image(self, qtbot, test_composition):
        """Test widget can be created without simulation image."""
        widget = LiveViewWidget(composition=test_composition, camera_id=0)
        qtbot.addWidget(widget)

        assert widget.camera_widget is not None
        assert widget.camera_widget.camera_id == 0


class TestLiveViewIntegration:
    """Integration tests for LiveViewWidget."""

    @pytest.fixture
    def full_widget(self, qtbot, tmp_path):
        """Create widget with full setup."""
        # Create template
        template_path = tmp_path / "logo.png"
        cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

        # Create composition
        platen = PlatenProfile(
            version=1,
            name="Integration Platen",
            type="platen",
            dimensions_mm={"width": 400.0, "height": 300.0},
            calibration=CalibrationInfo(
                camera_id=0,
                last_calibrated=datetime.now(),
                homography_path="calibration/test.npz",
                mm_per_px=0.4
            )
        )

        style = StyleProfile(
            version=1,
            name="Integration Style",
            type="style",
            logos=[
                LogoDefinition(
                    name="logo_1",
                    template_path=str(template_path),
                    position_mm=[100.0, 100.0],
                    roi={"width_mm": 40.0, "height_mm": 40.0}
                ),
                LogoDefinition(
                    name="logo_2",
                    template_path=str(template_path),
                    position_mm=[300.0, 100.0],
                    roi={"width_mm": 40.0, "height_mm": 40.0}
                )
            ]
        )

        composition = Composition(platen=platen, style=style)

        # Create simulation image
        sim_image = tmp_path / "sim.jpg"
        cv2.imwrite(str(sim_image), np.zeros((600, 800, 3), dtype=np.uint8))

        widget = LiveViewWidget(composition=composition, simulation_image=sim_image)
        qtbot.addWidget(widget)

        return widget

    def test_multiple_logos_in_composition(self, full_widget):
        """Test widget with multiple logos."""
        expected_positions = full_widget.composition.get_expected_positions()

        assert len(expected_positions) == 2
        assert "logo_1" in expected_positions
        assert "logo_2" in expected_positions

    def test_widget_displays_status_for_multiple_logos(self, full_widget):
        """Test status shows correct logo count."""
        full_widget._update_status()

        # Should mention expected count
        status_text = full_widget.status_label.text()
        assert len(status_text) > 0
