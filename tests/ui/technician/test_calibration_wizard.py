"""Tests for calibration wizard."""

import pytest
from PySide6.QtWidgets import QApplication

from alignpress.ui.technician.calibration_wizard import (
    CalibrationWizard, ConfigurationPage, CapturePage,
    CalculationPage, ResultsPage
)


@pytest.fixture
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestCalibrationWizard:
    """Tests for CalibrationWizard."""

    def test_wizard_initialization(self, qapp):
        """Test wizard initializes correctly."""
        wizard = CalibrationWizard()

        assert wizard is not None
        assert wizard.windowTitle() == "Camera Calibration Wizard"
        assert wizard.pageIds() == [0, 1, 2, 3]  # 4 pages

        wizard.close()

    def test_wizard_has_all_pages(self, qapp):
        """Test wizard has all required pages."""
        wizard = CalibrationWizard()

        assert isinstance(wizard.page(0), ConfigurationPage)
        assert isinstance(wizard.page(1), CapturePage)
        assert isinstance(wizard.page(2), CalculationPage)
        assert isinstance(wizard.page(3), ResultsPage)

        wizard.close()


class TestConfigurationPage:
    """Tests for ConfigurationPage."""

    def test_page_initialization(self, qapp):
        """Test page initializes with default values."""
        page = ConfigurationPage()

        assert page.title() == "Calibration Configuration"
        assert page.camera_id_spin.value() == 0
        assert page.pattern_width_spin.value() == 9
        assert page.pattern_height_spin.value() == 6
        assert page.square_size_spin.value() == 25.0

    def test_page_fields_registered(self, qapp):
        """Test page fields are registered."""
        wizard = CalibrationWizard()
        page = wizard.page(0)

        # Change values
        page.camera_id_spin.setValue(1)
        page.pattern_width_spin.setValue(10)
        page.pattern_height_spin.setValue(7)
        page.square_size_spin.setValue(30.0)

        # Check fields are accessible via wizard
        assert wizard.field("camera_id") == 1
        assert wizard.field("pattern_width") == 10
        assert wizard.field("pattern_height") == 7
        assert wizard.field("square_size") == 30.0

        wizard.close()


class TestCapturePage:
    """Tests for CapturePage."""

    def test_page_initialization(self, qapp):
        """Test page initializes correctly."""
        page = CapturePage()

        assert page.title() == "Capture Calibration Images"
        assert page.calibrator is None
        assert page.preview_label is not None
        assert page.capture_btn is not None
        assert page.count_label.text() == "Captured: 0 / 10"

    def test_capture_button_starts_disabled(self, qapp):
        """Test capture button starts disabled."""
        page = CapturePage()

        assert not page.capture_btn.isEnabled()

    def test_page_not_complete_initially(self, qapp):
        """Test page is not complete without captures."""
        page = CapturePage()

        assert not page.isComplete()


class TestCalculationPage:
    """Tests for CalculationPage."""

    def test_page_initialization(self, qapp):
        """Test page initializes correctly."""
        page = CalculationPage()

        assert page.title() == "Calculate Calibration"
        assert page.calc_thread is None
        assert page.results == {}
        assert page.progress_bar is not None
        assert page.progress_bar.value() == 0

    def test_page_not_complete_initially(self, qapp):
        """Test page is not complete without results."""
        page = CalculationPage()

        assert not page.isComplete()


class TestResultsPage:
    """Tests for ResultsPage."""

    def test_page_initialization(self, qapp):
        """Test page initializes correctly."""
        page = ResultsPage()

        assert page.title() == "Calibration Results"
        assert page.mm_per_px_label.text() == "—"
        assert page.error_label.text() == "—"
        assert page.captures_label.text() == "—"
        assert page.homography_label.text() == "—"
        assert page.save_status_label.text() == "Not saved yet"
