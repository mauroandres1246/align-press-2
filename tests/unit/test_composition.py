"""Unit tests for composition module."""

import pytest
from pathlib import Path

from alignpress.core.profile import PlatenProfile, StyleProfile, SizeVariant, ProfileLoader
from alignpress.core.composition import Composition


class TestComposition:
    """Test Composition functionality."""

    @pytest.fixture
    def loader(self):
        """Profile loader fixture."""
        return ProfileLoader()

    @pytest.fixture
    def sample_platen(self, loader):
        """Load sample platen profile."""
        profile_path = Path("profiles/planchas/plancha_300x200.yaml")
        if profile_path.exists():
            return loader.load_platen("plancha_300x200")
        pytest.skip("Platen profile not found")

    @pytest.fixture
    def sample_style(self, loader):
        """Load sample style profile."""
        profile_path = Path("profiles/estilos/polo_basico.yaml")
        if profile_path.exists():
            return loader.load_style("polo_basico")
        pytest.skip("Style profile not found")

    def test_composition_creation(self, sample_platen, sample_style):
        """Test creating a valid composition."""
        composition = Composition(sample_platen, sample_style)

        assert composition.platen == sample_platen
        assert composition.style == sample_style
        assert composition.variant is None

    def test_get_expected_positions(self, sample_platen, sample_style):
        """Test getting expected logo positions."""
        composition = Composition(sample_platen, sample_style)
        positions = composition.get_expected_positions()

        assert isinstance(positions, dict)
        assert "pecho" in positions
        assert isinstance(positions["pecho"], tuple)
        assert len(positions["pecho"]) == 2

    def test_to_detector_config(self, sample_platen, sample_style):
        """Test generating detector configuration."""
        composition = Composition(sample_platen, sample_style)
        config = composition.to_detector_config()

        assert "plane" in config
        assert "logos" in config
        assert "thresholds" in config
        assert "features" in config
        assert config["plane"]["width_mm"] == sample_platen.width_mm
        assert len(config["logos"]) == len(sample_style.logos)

    def test_composition_to_dict(self, sample_platen, sample_style):
        """Test serializing composition to dict."""
        composition = Composition(sample_platen, sample_style)
        data = composition.to_dict()

        assert data["platen"] == sample_platen.name
        assert data["style"] == sample_style.name
        assert data["variant"] is None
        assert "logos" in data
        assert "calibration_age_days" in data

    def test_calibration_warning(self, sample_platen, sample_style):
        """Test calibration warning generation."""
        composition = Composition(sample_platen, sample_style)
        warning = composition.get_calibration_warning()

        # Warning depends on actual calibration age
        if warning:
            assert "Calibration" in warning
