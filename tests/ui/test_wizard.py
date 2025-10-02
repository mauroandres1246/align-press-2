"""Tests for SelectionWizard."""

import pytest
from pathlib import Path
from PySide6.QtWidgets import QWizard
from PySide6.QtCore import QSettings

from alignpress.ui.operator.wizard import (
    SelectionWizard,
    PlatenSelectionPage,
    StyleSelectionPage,
    SizeSelectionPage
)
from alignpress.core.profile import ProfileLoader
from alignpress.core.composition import Composition


class TestSelectionWizard:
    """Test SelectionWizard functionality."""

    @pytest.fixture
    def profiles_path(self):
        """Get profiles path."""
        return Path("profiles")

    @pytest.fixture
    def wizard(self, qtbot, profiles_path):
        """Create wizard instance."""
        wizard = SelectionWizard(profiles_path)
        qtbot.addWidget(wizard)
        return wizard

    def test_wizard_initialization(self, wizard):
        """Test wizard initializes correctly."""
        assert wizard.windowTitle() == "Selección de Trabajo"
        assert wizard.profiles_path == Path("profiles")
        assert wizard.loader is not None

    def test_wizard_has_three_pages(self, wizard):
        """Test wizard has 3 pages."""
        assert wizard.pageIds().__len__() == 3

    def test_wizard_pages_are_correct_type(self, wizard):
        """Test wizard pages are correct types."""
        page0 = wizard.page(0)
        page1 = wizard.page(1)
        page2 = wizard.page(2)

        assert isinstance(page0, PlatenSelectionPage)
        assert isinstance(page1, StyleSelectionPage)
        assert isinstance(page2, SizeSelectionPage)

    def test_wizard_emits_composition_on_finish(self, wizard, qtbot, monkeypatch, tmp_path):
        """Test wizard emits composition when finished."""
        # Mock ProfileLoader to avoid needing actual files
        from alignpress.core.profile import PlatenProfile, StyleProfile, CalibrationInfo, LogoDefinition
        from datetime import datetime
        import cv2
        import numpy as np

        # Create temporary template file
        template_path = tmp_path / "test_template.png"
        cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

        mock_platen = PlatenProfile(
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

        mock_style = StyleProfile(
            version=1,
            name="Test Style",
            type="style",
            logos=[
                LogoDefinition(
                    name="test_logo",
                    template_path=str(template_path),
                    position_mm=[150.0, 100.0],
                    roi={"width_mm": 50.0, "height_mm": 40.0, "margin_factor": 1.2}
                )
            ]
        )

        # Set selected items directly
        wizard.selected_platen = mock_platen
        wizard.selected_style = mock_style
        wizard.selected_variant = None

        # Track signal
        compositions_received = []

        def on_composition_created(comp):
            compositions_received.append(comp)

        wizard.composition_created.connect(on_composition_created)

        # Simulate finish
        wizard._on_wizard_finished(QWizard.DialogCode.Accepted)

        # Check signal was emitted
        assert len(compositions_received) == 1
        assert isinstance(compositions_received[0], Composition)


class TestPlatenSelectionPage:
    """Test PlatenSelectionPage."""

    @pytest.fixture
    def page(self, qtbot):
        """Create page instance."""
        loader = ProfileLoader(Path("profiles"))
        settings = QSettings("Align-Press-Test", "v2-test")
        page = PlatenSelectionPage(loader, settings)
        qtbot.addWidget(page)
        return page

    def test_page_initialization(self, page):
        """Test page initializes correctly."""
        assert page.title() == "Paso 1: Seleccionar Plancha"
        assert page.platen_list is not None
        assert page.info_label is not None

    def test_page_starts_incomplete(self, page):
        """Test page starts as incomplete."""
        assert page.isComplete() is False

    def test_page_becomes_complete_on_selection(self, page, qtbot, monkeypatch):
        """Test page becomes complete when platen is selected."""
        from alignpress.core.profile import PlatenProfile, CalibrationInfo
        from datetime import datetime

        # Create mock platen
        mock_platen = PlatenProfile(
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

        # Set selected platen directly
        page.selected_platen = mock_platen

        assert page.isComplete() is True


class TestStyleSelectionPage:
    """Test StyleSelectionPage."""

    @pytest.fixture
    def page(self, qtbot):
        """Create page instance."""
        loader = ProfileLoader(Path("profiles"))
        settings = QSettings("Align-Press-Test", "v2-test")
        page = StyleSelectionPage(loader, settings)
        qtbot.addWidget(page)
        return page

    def test_page_initialization(self, page):
        """Test page initializes correctly."""
        assert page.title() == "Paso 2: Seleccionar Estilo"
        assert page.style_list is not None
        assert page.info_label is not None

    def test_page_starts_incomplete(self, page):
        """Test page starts as incomplete."""
        assert page.isComplete() is False


class TestSizeSelectionPage:
    """Test SizeSelectionPage."""

    @pytest.fixture
    def page(self, qtbot):
        """Create page instance."""
        settings = QSettings("Align-Press-Test", "v2-test")
        page = SizeSelectionPage(settings)
        qtbot.addWidget(page)
        return page

    def test_page_initialization(self, page):
        """Test page initializes correctly."""
        assert page.title() == "Paso 3: Seleccionar Talla (Opcional)"
        assert page.button_group is not None
        assert page.no_variant_radio is not None

    def test_page_always_complete(self, page):
        """Test page is always complete (variant is optional)."""
        assert page.isComplete() is True

    def test_page_starts_with_no_variant(self, page):
        """Test page starts with no variant selected."""
        assert page.no_variant_radio.isChecked() is True
        assert page.selected_variant is None
