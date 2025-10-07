"""Tests for metrics panel widget."""

import pytest
from PySide6.QtWidgets import QApplication

from alignpress.ui.widgets.metrics_panel import MetricsPanel, LogoMetricWidget
from alignpress.core.schemas import LogoResultSchema


@pytest.fixture
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestLogoMetricWidget:
    """Tests for LogoMetricWidget."""

    def test_widget_initialization(self, qapp):
        """Test widget initializes correctly."""
        widget = LogoMetricWidget("test_logo")

        assert widget.logo_name == "test_logo"
        assert widget.led_label is not None
        assert widget.status_label is not None
        assert widget.deviation_label is not None
        assert widget.angle_label is not None

    def test_initial_state_is_no_detection(self, qapp):
        """Test widget starts in 'no detection' state."""
        widget = LogoMetricWidget("test_logo")

        assert widget.led_label.text() == "⚫"
        assert widget.status_label.text() == "No detectado"
        assert "—" in widget.deviation_label.text()
        assert "—" in widget.angle_label.text()

    def test_update_with_perfect_result(self, qapp):
        """Test widget updates correctly with PERFECT result."""
        widget = LogoMetricWidget("test_logo")

        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            status="PERFECT",
            detected_position=(100.0, 100.0),
            expected_position=(100.0, 100.0),
            deviation_mm=0.5,
            angle_deg=0.0,
            angle_error_deg=0.2,
            inliers_count=50,
            total_keypoints=55,
            inlier_ratio=0.91,
            reproj_error_px=0.8
        )

        widget.update_result(result)

        assert widget.led_label.text() == "🟢"
        assert widget.status_label.text() == "PERFECTO"
        assert "0.50" in widget.deviation_label.text()
        assert "0.2" in widget.angle_label.text()

    def test_update_with_good_result(self, qapp):
        """Test widget updates correctly with GOOD result."""
        widget = LogoMetricWidget("test_logo")

        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            detected_position=(101.5, 100.5),
            expected_position=(100.0, 100.0),
            deviation_mm=3.0,  # Between 2.0 (perfect) and 4.0 (good) -> GOOD
            angle_deg=1.5,
            angle_error_deg=1.5,
            inliers_count=45,
            total_keypoints=55,
            inlier_ratio=0.82,
            reproj_error_px=1.2
        )

        widget.update_result(result)

        assert widget.led_label.text() == "🟡"
        assert widget.status_label.text() == "BUENO"
        assert "3.00" in widget.deviation_label.text()
        assert "1.5" in widget.angle_label.text()

    def test_update_with_needs_adjustment_result(self, qapp):
        """Test widget updates correctly with NEEDS_ADJUSTMENT result."""
        widget = LogoMetricWidget("test_logo")

        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            status="NEEDS_ADJUSTMENT",
            detected_position=(105.0, 102.0),
            expected_position=(100.0, 100.0),
            deviation_mm=5.4,
            angle_deg=3.2,
            angle_error_deg=3.2,
            inliers_count=38,
            total_keypoints=50,
            inlier_ratio=0.76,
            reproj_error_px=2.1
        )

        widget.update_result(result)

        assert widget.led_label.text() == "🔴"
        assert widget.status_label.text() == "AJUSTAR"
        assert "5.40" in widget.deviation_label.text()
        assert "3.2" in widget.angle_label.text()

    def test_update_with_not_found_result(self, qapp):
        """Test widget updates correctly with not found result."""
        widget = LogoMetricWidget("test_logo")

        result = LogoResultSchema(
            logo_name="test_logo",
            found=False,
            status="NOT_FOUND",
            detected_position=(0.0, 0.0),
            expected_position=(100.0, 100.0),
            deviation_mm=0.0,
            angle_deg=0.0,
            angle_error_deg=0.0,
            inliers_count=0,
            total_keypoints=0,
            inlier_ratio=0.0,
            reproj_error_px=0.0
        )

        widget.update_result(result)

        # Should go back to 'no detection' state
        assert widget.led_label.text() == "⚫"
        assert widget.status_label.text() == "No detectado"

    def test_set_no_detection(self, qapp):
        """Test set_no_detection method."""
        widget = LogoMetricWidget("test_logo")

        # First set to some state
        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            status="PERFECT",
            detected_position=(100.0, 100.0),
            expected_position=(100.0, 100.0),
            deviation_mm=0.5,
            angle_deg=0.0,
            angle_error_deg=0.2,
            inliers_count=50,
            total_keypoints=55,
            inlier_ratio=0.91,
            reproj_error_px=0.8
        )
        widget.update_result(result)

        # Now reset
        widget.set_no_detection()

        assert widget.led_label.text() == "⚫"
        assert widget.status_label.text() == "No detectado"
        assert "—" in widget.deviation_label.text()
        assert "—" in widget.angle_label.text()


class TestMetricsPanel:
    """Tests for MetricsPanel."""

    def test_panel_initialization(self, qapp):
        """Test panel initializes correctly."""
        logo_names = ["logo_a", "logo_b", "logo_c"]
        panel = MetricsPanel(logo_names)

        assert len(panel.logo_widgets) == 3
        assert "logo_a" in panel.logo_widgets
        assert "logo_b" in panel.logo_widgets
        assert "logo_c" in panel.logo_widgets

    def test_panel_creates_widgets_for_each_logo(self, qapp):
        """Test panel creates widget for each logo."""
        logo_names = ["logo_a", "logo_b"]
        panel = MetricsPanel(logo_names)

        assert isinstance(panel.logo_widgets["logo_a"], LogoMetricWidget)
        assert isinstance(panel.logo_widgets["logo_b"], LogoMetricWidget)

    def test_update_results(self, qapp):
        """Test panel updates with new results."""
        logo_names = ["logo_a", "logo_b"]
        panel = MetricsPanel(logo_names)

        results = {
            "logo_a": LogoResultSchema(
                logo_name="logo_a",
                found=True,
                detected_position=(100.0, 100.0),
                expected_position=(100.0, 100.0),
                deviation_mm=0.5,
                angle_deg=0.0,
                angle_error_deg=0.2,
                inliers_count=50,
                total_keypoints=55,
                inlier_ratio=0.91,
                reproj_error_px=0.8
            ),
            "logo_b": LogoResultSchema(
                logo_name="logo_b",
                found=True,
                detected_position=(201.5, 100.5),
                expected_position=(200.0, 100.0),
                deviation_mm=3.0,  # Between 2.0 (perfect) and 4.0 (good) -> GOOD
                angle_deg=1.5,
                angle_error_deg=1.5,
                inliers_count=45,
                total_keypoints=55,
                inlier_ratio=0.82,
                reproj_error_px=1.2
            )
        }

        panel.update_results(results)

        # Check that widgets were updated
        assert panel.logo_widgets["logo_a"].led_label.text() == "🟢"
        assert panel.logo_widgets["logo_b"].led_label.text() == "🟡"

    def test_update_with_partial_results(self, qapp):
        """Test panel updates correctly with partial results."""
        logo_names = ["logo_a", "logo_b", "logo_c"]
        panel = MetricsPanel(logo_names)

        # Only provide results for logo_a
        results = {
            "logo_a": LogoResultSchema(
                logo_name="logo_a",
                found=True,
                status="PERFECT",
                detected_position=(100.0, 100.0),
                expected_position=(100.0, 100.0),
                deviation_mm=0.5,
                angle_deg=0.0,
                angle_error_deg=0.2,
                inliers_count=50,
                total_keypoints=55,
                inlier_ratio=0.91,
                reproj_error_px=0.8
            )
        }

        panel.update_results(results)

        # logo_a should be updated
        assert panel.logo_widgets["logo_a"].led_label.text() == "🟢"

        # logo_b and logo_c should be in 'no detection' state
        assert panel.logo_widgets["logo_b"].led_label.text() == "⚫"
        assert panel.logo_widgets["logo_c"].led_label.text() == "⚫"

    def test_clear_method(self, qapp):
        """Test clear method resets all widgets."""
        logo_names = ["logo_a", "logo_b"]
        panel = MetricsPanel(logo_names)

        # First set some results
        results = {
            "logo_a": LogoResultSchema(
                logo_name="logo_a",
                found=True,
                status="PERFECT",
                detected_position=(100.0, 100.0),
                expected_position=(100.0, 100.0),
                deviation_mm=0.5,
                angle_deg=0.0,
                angle_error_deg=0.2,
                inliers_count=50,
                total_keypoints=55,
                inlier_ratio=0.91,
                reproj_error_px=0.8
            ),
            "logo_b": LogoResultSchema(
                logo_name="logo_b",
                found=True,
                status="GOOD",
                detected_position=(201.5, 100.5),
                expected_position=(200.0, 100.0),
                deviation_mm=1.8,
                angle_deg=1.5,
                angle_error_deg=1.5,
                inliers_count=45,
                total_keypoints=55,
                inlier_ratio=0.82,
                reproj_error_px=1.2
            )
        }
        panel.update_results(results)

        # Now clear
        panel.clear()

        # All widgets should be in 'no detection' state
        for widget in panel.logo_widgets.values():
            assert widget.led_label.text() == "⚫"
            assert widget.status_label.text() == "No detectado"
