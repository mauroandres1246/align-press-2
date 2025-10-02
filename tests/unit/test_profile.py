"""Unit tests for profile management."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from alignpress.core.profile import (
    PlatenProfile, StyleProfile, SizeVariant, ProfileLoader,
    CalibrationInfo, LogoDefinition
)


class TestPlatenProfile:
    """Test PlatenProfile functionality."""

    def test_load_valid_profile(self):
        """Test loading a valid platen profile."""
        profile_path = Path("profiles/planchas/plancha_300x200.yaml")
        if not profile_path.exists():
            pytest.skip("Profile file not found")

        profile = PlatenProfile.from_file(profile_path)

        assert profile.name == "Plancha Estándar 300x200"
        assert profile.type == "platen"
        assert profile.width_mm == 300.0
        assert profile.height_mm == 200.0
        assert profile.calibration.mm_per_px == 0.5

    def test_calibration_age(self):
        """Test calibration age calculation."""
        old_date = datetime.now() - timedelta(days=45)
        calib = CalibrationInfo(
            camera_id=0,
            last_calibrated=old_date,
            homography_path="test.json",
            mm_per_px=0.5
        )

        assert calib.age_days >= 45
        assert calib.is_expired(max_age_days=30) is True
        assert calib.is_expired(max_age_days=60) is False


class TestStyleProfile:
    """Test StyleProfile functionality."""

    def test_load_valid_style(self):
        """Test loading a valid style profile."""
        profile_path = Path("profiles/estilos/polo_basico.yaml")
        if not profile_path.exists():
            pytest.skip("Profile file not found")

        style = StyleProfile.from_file(profile_path)

        assert style.name == "Polo Básico"
        assert style.type == "style"
        assert len(style.logos) == 3
        assert style.logos[0].name == "pecho"

    def test_style_requires_logos(self):
        """Test that style must have at least one logo."""
        with pytest.raises(ValueError, match="at least one logo"):
            StyleProfile(
                version=1,
                name="Empty Style",
                type="style",
                logos=[]
            )


class TestSizeVariant:
    """Test SizeVariant functionality."""

    def test_load_valid_variant(self):
        """Test loading a valid size variant."""
        variant_path = Path("profiles/variantes/talla_m.yaml")
        if not variant_path.exists():
            pytest.skip("Variant file not found")

        variant = SizeVariant.from_file(variant_path)

        assert variant.type == "variant"
        assert variant.size == "M"

    def test_get_offset(self):
        """Test getting offset for a logo."""
        variant = SizeVariant(
            version=1,
            name="Test Variant",
            type="variant",
            size="L",
            offsets={
                "pecho": [5.0, 10.0],
                "manga": [0.0, 2.0]
            }
        )

        assert variant.get_offset("pecho") == (5.0, 10.0)
        assert variant.get_offset("manga") == (0.0, 2.0)
        assert variant.get_offset("nonexistent") == (0.0, 0.0)


class TestProfileLoader:
    """Test ProfileLoader functionality."""

    def test_loader_initialization(self):
        """Test profile loader initialization."""
        loader = ProfileLoader()
        assert loader.base_dir == Path("profiles")

    def test_loader_caching(self):
        """Test that profiles are cached."""
        loader = ProfileLoader()

        profile_path = Path("profiles/planchas/plancha_300x200.yaml")
        if not profile_path.exists():
            pytest.skip("Profile file not found")

        # Load twice
        profile1 = loader.load_platen("plancha_300x200")
        profile2 = loader.load_platen("plancha_300x200")

        # Should be same object from cache
        assert profile1 is profile2

    def test_clear_cache(self):
        """Test cache clearing."""
        loader = ProfileLoader()

        profile_path = Path("profiles/planchas/plancha_300x200.yaml")
        if not profile_path.exists():
            pytest.skip("Profile file not found")

        profile1 = loader.load_platen("plancha_300x200")
        loader.clear_cache()
        profile2 = loader.load_platen("plancha_300x200")

        # Should be different objects after cache clear
        assert profile1 is not profile2
