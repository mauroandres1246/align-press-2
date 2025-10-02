"""Unit tests for job card module."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import json

from alignpress.core.job_card import JobCard
from alignpress.core.profile import ProfileLoader
from alignpress.core.composition import Composition
from alignpress.core.schemas import LogoResultSchema


class TestJobCard:
    """Test JobCard functionality."""

    @pytest.fixture
    def sample_composition(self):
        """Create sample composition."""
        loader = ProfileLoader()

        platen_path = Path("profiles/planchas/plancha_300x200.yaml")
        style_path = Path("profiles/estilos/polo_basico.yaml")

        if not platen_path.exists() or not style_path.exists():
            pytest.skip("Profile files not found")

        platen = loader.load_platen("plancha_300x200")
        style = loader.load_style("polo_basico")

        return Composition(platen, style)

    @pytest.fixture
    def sample_results(self):
        """Create sample detection results."""
        return [
            LogoResultSchema(
                logo_name="pecho",
                found=True,
                position_mm=(150.2, 100.5),
                angle_deg=0.5,
                deviation_mm=0.3,
                angle_error_deg=0.5,
                confidence=0.85,
                inliers=50
            ),
            LogoResultSchema(
                logo_name="manga_izq",
                found=True,
                position_mm=(50.1, 60.2),
                angle_deg=-1.0,
                deviation_mm=0.5,
                angle_error_deg=1.0,
                confidence=0.78,
                inliers=35
            )
        ]

    def test_job_card_creation(self, sample_composition):
        """Test creating a new job card."""
        job = JobCard.create(sample_composition, operator="Juan")

        assert job.job_id.startswith("JOB-")
        assert job.operator == "Juan"
        assert job.composition == sample_composition
        assert len(job.results) == 0
        assert job.timestamp_end is None

    def test_add_results(self, sample_composition, sample_results):
        """Test adding results to job card."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)

        assert len(job.results) == 2
        assert job.logos_total_count == 2
        assert job.logos_found_count == 2

    def test_finalize_job(self, sample_composition, sample_results):
        """Test finalizing a job."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)
        job.finalize(notes="Test job completed")

        assert job.timestamp_end is not None
        assert job.duration_seconds is not None
        assert job.duration_seconds >= 0
        assert job.notes == "Test job completed"

    def test_is_successful(self, sample_composition, sample_results):
        """Test success detection."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)

        assert job.is_successful is True
        assert job.success_rate == 100.0

    def test_partial_success(self, sample_composition):
        """Test partial success scenario."""
        results = [
            LogoResultSchema(logo_name="logo1", found=True, position_mm=(10, 10)),
            LogoResultSchema(logo_name="logo2", found=False, position_mm=None)
        ]

        job = JobCard.create(sample_composition)
        job.add_results(results)

        assert job.is_successful is False
        assert job.logos_found_count == 1
        assert job.logos_total_count == 2
        assert job.success_rate == 50.0

    def test_to_dict(self, sample_composition, sample_results):
        """Test converting job card to dictionary."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)
        job.finalize()

        data = job.to_dict()

        assert data["job_id"] == job.job_id
        assert data["operator"] == job.operator
        assert "composition" in data
        assert "results" in data
        assert data["summary"]["successful"] is True

    def test_to_json(self, sample_composition, sample_results):
        """Test JSON serialization."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)

        json_str = job.to_json()
        parsed = json.loads(json_str)

        assert parsed["job_id"] == job.job_id
        assert len(parsed["results"]) == 2

    def test_save_job_card(self, sample_composition, sample_results, tmp_path):
        """Test saving job card to file."""
        job = JobCard.create(sample_composition)
        job.add_results(sample_results)
        job.finalize()

        saved_path = job.save(output_dir=tmp_path)

        assert saved_path.exists()
        assert saved_path.name == f"{job.job_id}.json"

        # Verify file content
        with open(saved_path) as f:
            data = json.load(f)
            assert data["job_id"] == job.job_id

    def test_get_summary(self, sample_composition, sample_results):
        """Test getting job summary."""
        job = JobCard.create(sample_composition, operator="Maria")
        job.add_results(sample_results)
        job.finalize()

        summary = job.get_summary()

        assert summary["job_id"] == job.job_id
        assert summary["operator"] == "Maria"
        assert summary["logos_found"] == "2/2"
        assert summary["status"] == "SUCCESS"
