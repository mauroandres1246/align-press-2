"""Integration tests for complete workflow."""

import pytest
from pathlib import Path
import tempfile
import json

from alignpress.core.profile import ProfileLoader
from alignpress.core.composition import Composition
from alignpress.core.job_card import JobCard
from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import LogoResultSchema


class TestCompleteWorkflow:
    """Test complete system workflow end-to-end."""

    @pytest.fixture
    def loader(self):
        """Profile loader fixture."""
        return ProfileLoader()

    @pytest.fixture
    def profiles_exist(self):
        """Check if required profiles exist."""
        platen_path = Path("profiles/planchas/plancha_300x200.yaml")
        style_path = Path("profiles/estilos/polo_basico.yaml")

        if not platen_path.exists() or not style_path.exists():
            pytest.skip("Required profile files not found")
        return True

    def test_load_profiles_workflow(self, loader, profiles_exist):
        """Test loading profiles workflow."""
        # Load profiles
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")

        # Verify loaded correctly
        assert platen.name == "Plancha Estándar 300x200"
        assert platen.width_mm == 300.0
        assert style.name == "Polo Básico"
        assert len(style.logos) > 0

    def test_create_composition_workflow(self, loader, profiles_exist):
        """Test creating composition from profiles."""
        # Load profiles
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")

        # Create composition
        composition = Composition(platen, style)

        # Verify composition
        assert composition.platen == platen
        assert composition.style == style
        positions = composition.get_expected_positions()
        assert len(positions) == len(style.logos)

    def test_generate_detector_config_workflow(self, loader, profiles_exist):
        """Test generating detector configuration from composition."""
        # Load and compose
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)

        # Generate detector config
        config = composition.to_detector_config()

        # Verify config structure
        assert "plane" in config
        assert "logos" in config
        assert "thresholds" in config
        assert "features" in config

        # Verify plane config
        assert config["plane"]["width_mm"] == 300.0
        assert config["plane"]["height_mm"] == 200.0
        assert config["plane"]["mm_per_px"] == 0.5

        # Verify logos config
        assert len(config["logos"]) == 3  # polo_basico has 3 logos

    def test_initialize_detector_from_composition(self, loader, profiles_exist):
        """Test initializing detector from composition."""
        # Load and compose
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)

        # Generate config and create detector
        config = composition.to_detector_config()
        detector = PlanarLogoDetector(config)

        # Verify detector initialized
        assert detector is not None
        assert len(detector.config.logos) == 3
        assert detector.config.plane.width_mm == 300.0

    def test_create_job_card_workflow(self, loader, profiles_exist):
        """Test creating and finalizing job card."""
        # Setup
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)

        # Create job card
        job = JobCard.create(composition, operator="TestOperator")

        # Add mock results
        results = [
            LogoResultSchema(
                logo_name="pecho",
                found=True,
                position_mm=(150.0, 100.0),
                angle_deg=0.0,
                deviation_mm=0.5,
                angle_error_deg=1.0,
                confidence=0.85,
                inliers=50
            ),
            LogoResultSchema(
                logo_name="manga_izq",
                found=True,
                position_mm=(50.0, 60.0),
                angle_deg=0.0,
                deviation_mm=0.3,
                angle_error_deg=0.5,
                confidence=0.90,
                inliers=45
            ),
            LogoResultSchema(
                logo_name="manga_der",
                found=True,
                position_mm=(250.0, 60.0),
                angle_deg=0.0,
                deviation_mm=0.4,
                angle_error_deg=0.8,
                confidence=0.87,
                inliers=48
            )
        ]

        job.add_results(results)
        job.finalize(notes="Integration test completed")

        # Verify job card
        assert job.is_successful is True
        assert job.logos_found_count == 3
        assert job.logos_total_count == 3
        assert job.success_rate == 100.0
        assert job.notes == "Integration test completed"

    def test_save_job_card_workflow(self, loader, profiles_exist, tmp_path):
        """Test saving job card to disk."""
        # Setup and create job
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)
        job = JobCard.create(composition, operator="TestOp")

        # Add results and finalize
        results = [
            LogoResultSchema(logo_name="pecho", found=True, position_mm=(150, 100))
        ]
        job.add_results(results)
        job.finalize()

        # Save
        saved_path = job.save(output_dir=tmp_path)

        # Verify saved
        assert saved_path.exists()
        assert saved_path.suffix == ".json"

        # Verify content
        with open(saved_path) as f:
            data = json.load(f)
            assert data["job_id"] == job.job_id
            assert data["operator"] == "TestOp"
            assert data["composition"]["platen"] == "Plancha Estándar 300x200"
            assert data["composition"]["style"] == "Polo Básico"

    def test_full_system_workflow(self, loader, profiles_exist, tmp_path):
        """Test complete system workflow from profiles to saved job card."""
        # Step 1: Load profiles
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")

        # Step 2: Create composition
        composition = Composition(platen, style)

        # Step 3: Generate detector config and initialize
        config = composition.to_detector_config()
        detector = PlanarLogoDetector(config)

        # Step 4: Create job card
        job = JobCard.create(composition, operator="IntegrationTest")

        # Step 5: Simulate detection (mock results)
        mock_results = []
        for logo_name in composition.get_expected_positions().keys():
            mock_results.append(
                LogoResultSchema(
                    logo_name=logo_name,
                    found=True,
                    position_mm=(150.0, 100.0),
                    angle_deg=0.0,
                    deviation_mm=0.5,
                    angle_error_deg=1.0,
                    confidence=0.85,
                    inliers=50
                )
            )

        # Step 6: Add results and finalize
        job.add_results(mock_results)
        job.finalize(notes="Full workflow test")

        # Step 7: Save job card
        saved_path = job.save(output_dir=tmp_path)

        # Verify complete workflow
        assert saved_path.exists()
        assert job.is_successful
        assert job.logos_total_count == 3

        # Verify saved data
        with open(saved_path) as f:
            data = json.load(f)
            assert data["summary"]["successful"] is True
            assert len(data["results"]) == 3

    def test_profile_caching(self, loader, profiles_exist):
        """Test that profiles are cached correctly."""
        # Load same profile twice
        platen1 = loader.load_platen("plancha_300x200")
        platen2 = loader.load_platen("plancha_300x200")

        # Should be same object from cache
        assert platen1 is platen2

        # Clear cache and reload
        loader.clear_cache()
        platen3 = loader.load_platen("plancha_300x200")

        # Should be different object after cache clear
        assert platen1 is not platen3

    def test_calibration_validation(self, loader, profiles_exist):
        """Test calibration age validation."""
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)

        # Check calibration status
        is_valid = composition.is_calibration_valid(max_age_days=365)
        assert isinstance(is_valid, bool)

        # Check for warnings
        warning = composition.get_calibration_warning()
        # Warning may or may not exist depending on actual calibration age
        if warning:
            assert isinstance(warning, str)
            assert "Calibration" in warning

    def test_composition_serialization(self, loader, profiles_exist):
        """Test composition serialization."""
        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")
        composition = Composition(platen, style)

        # Serialize to dict
        data = composition.to_dict()

        # Verify structure
        assert "platen" in data
        assert "style" in data
        assert "logos" in data
        assert "calibration_age_days" in data
        assert "calibration_valid" in data

        # Verify values
        assert data["platen"] == "Plancha Estándar 300x200"
        assert data["style"] == "Polo Básico"
        assert isinstance(data["logos"], list)
        assert len(data["logos"]) == 3


class TestErrorHandling:
    """Test error handling in workflows."""

    def test_missing_profile_error(self):
        """Test error when profile doesn't exist."""
        loader = ProfileLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_platen("nonexistent_platen")

    def test_invalid_composition_validation(self):
        """Test that invalid compositions are rejected."""
        # This would require creating profiles programmatically
        # with logos outside platen boundaries
        pass  # Skip for now - would need mock profiles

    def test_job_card_partial_success(self):
        """Test job card with partial detection success."""
        # Create a mock composition (simplified)
        from alignpress.core.profile import PlatenProfile, StyleProfile, LogoDefinition
        from datetime import datetime

        platen = PlatenProfile(
            version=1,
            name="Test Platen",
            type="platen",
            dimensions_mm={"width": 300, "height": 200},
            calibration={
                "camera_id": 0,
                "last_calibrated": datetime.now(),
                "homography_path": "test.json",
                "mm_per_px": 0.5
            }
        )

        style = StyleProfile(
            version=1,
            name="Test Style",
            type="style",
            logos=[
                LogoDefinition(
                    name="logo1",
                    template_path="test1.png",
                    position_mm=[100, 100],
                    roi={"width_mm": 50, "height_mm": 50, "margin_factor": 1.5}
                ),
                LogoDefinition(
                    name="logo2",
                    template_path="test2.png",
                    position_mm=[200, 100],
                    roi={"width_mm": 50, "height_mm": 50, "margin_factor": 1.5}
                )
            ]
        )

        composition = Composition(platen, style)
        job = JobCard.create(composition)

        # Add partial results (one found, one not found)
        results = [
            LogoResultSchema(logo_name="logo1", found=True, position_mm=(100, 100)),
            LogoResultSchema(logo_name="logo2", found=False, position_mm=None)
        ]

        job.add_results(results)
        job.finalize()

        # Verify partial success
        assert job.is_successful is False
        assert job.logos_found_count == 1
        assert job.logos_total_count == 2
        assert job.success_rate == 50.0
