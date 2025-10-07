"""Tests for debug view."""

import pytest
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import QApplication

from alignpress.ui.technician.debug_view import (
    DebugView, DebugMetricsPanel, DebugVisualizationPanel
)
from alignpress.core.composition import Composition
from alignpress.core.profile import PlatenProfile, StyleProfile, CalibrationInfo, LogoDefinition
from alignpress.core.schemas import LogoResultSchema


@pytest.fixture
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_composition(tmp_path):
    """Create test composition."""
    # Create template
    template_path = tmp_path / "test_logo.png"
    template = np.zeros((50, 50, 3), dtype=np.uint8)
    cv2.imwrite(str(template_path), template)

    platen = PlatenProfile(
        version=1,
        name="Test Platen",
        type="platen",
        dimensions_mm={"width": 300.0, "height": 200.0},
        calibration=CalibrationInfo(
            camera_id=0,
            last_calibrated=datetime.now(),
            homography_path="calibration/test.npz",
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
                template_path=str(template_path),
                position_mm=[150.0, 100.0],
                roi={"width_mm": 50.0, "height_mm": 40.0}
            )
        ]
    )

    return Composition(platen=platen, style=style)


class TestDebugMetricsPanel:
    """Tests for DebugMetricsPanel."""

    def test_panel_initialization(self, qapp):
        """Test panel initializes correctly."""
        panel = DebugMetricsPanel()

        assert panel is not None
        assert panel.keypoints_label.text() == "—"
        assert panel.matches_label.text() == "—"
        assert panel.position_label.text() == "—"

    def test_update_metrics_with_result(self, qapp):
        """Test updating metrics with detection result."""
        panel = DebugMetricsPanel()

        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            position_mm=(150.0, 100.0),
            detected_position=(150.0, 100.0),
            expected_position=(150.0, 100.0),
            deviation_mm=0.5,
            angle_deg=0.2,
            angle_error_deg=0.2,
            inliers_count=50,
            total_keypoints=55,
            inlier_ratio=0.91,
            reproj_error_px=0.8,
            processing_time_ms=15.5
        )

        panel.update_metrics(result)

        # Check that labels were updated
        assert panel.keypoints_label.text() == "55"
        assert "50" in panel.inliers_label.text()
        assert "0.91" in panel.inlier_ratio_label.text() or "91" in panel.inlier_ratio_label.text()

    def test_clear_metrics_when_not_found(self, qapp):
        """Test clearing metrics when logo not found."""
        panel = DebugMetricsPanel()

        # First set some values
        result_found = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            total_keypoints=50,
            inliers_count=45
        )
        panel.update_metrics(result_found)

        # Then clear with not found result
        result_not_found = LogoResultSchema(
            logo_name="test_logo",
            found=False
        )
        panel.update_metrics(result_not_found)

        # Should be cleared
        assert panel.keypoints_label.text() == "—"


class TestDebugVisualizationPanel:
    """Tests for DebugVisualizationPanel."""

    def test_panel_initialization(self, qapp):
        """Test panel initializes correctly."""
        panel = DebugVisualizationPanel()

        assert panel is not None
        assert panel.show_keypoints_cb is not None
        assert panel.show_roi_cb is not None
        assert panel.logo_combo is not None

    def test_default_visualization_flags(self, qapp):
        """Test default visualization flags."""
        panel = DebugVisualizationPanel()

        flags = panel.get_visualization_flags()

        assert flags["show_keypoints"] is True
        assert flags["show_matches"] is True
        assert flags["show_roi"] is True
        assert flags["show_expected"] is True
        assert flags["show_homography"] is False


class TestDebugView:
    """Tests for DebugView."""

    def test_view_initialization(self, qapp, test_composition, tmp_path):
        """Test view initializes correctly."""
        # Create simulation image
        sim_image = tmp_path / "sim.jpg"
        cv2.imwrite(str(sim_image), np.zeros((480, 640, 3), dtype=np.uint8))

        view = DebugView(
            composition=test_composition,
            simulation_image=str(sim_image)
        )

        assert view is not None
        assert view.composition == test_composition
        assert view.camera_widget is not None
        assert view.metrics_panel is not None
        assert view.viz_panel is not None

    def test_view_has_all_tabs(self, qapp, test_composition, tmp_path):
        """Test view has all required tabs."""
        sim_image = tmp_path / "sim.jpg"
        cv2.imwrite(str(sim_image), np.zeros((480, 640, 3), dtype=np.uint8))

        view = DebugView(
            composition=test_composition,
            simulation_image=str(sim_image)
        )

        # Find the tab widget
        from PySide6.QtWidgets import QTabWidget
        tab_widget = view.findChild(QTabWidget)

        assert tab_widget is not None
        assert tab_widget.count() == 3  # Metrics, Visualization, Raw Data

    def test_view_logo_combo_populated(self, qapp, test_composition, tmp_path):
        """Test logo combo is populated with logos from composition."""
        sim_image = tmp_path / "sim.jpg"
        cv2.imwrite(str(sim_image), np.zeros((480, 640, 3), dtype=np.uint8))

        view = DebugView(
            composition=test_composition,
            simulation_image=str(sim_image)
        )

        # Check logo combo has items
        assert view.viz_panel.logo_combo.count() == 1
        assert view.viz_panel.logo_combo.itemText(0) == "test_logo"
