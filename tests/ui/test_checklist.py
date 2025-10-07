"""Tests for validation checklist dialog."""

import pytest
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from alignpress.ui.operator.checklist import ValidationChecklistDialog
from alignpress.core.composition import Composition
from alignpress.core.profile import PlatenProfile, StyleProfile
from alignpress.core.schemas import LogoResultSchema


@pytest.fixture
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_composition(tmp_path):
    """Create mock composition for testing."""
    from datetime import datetime
    from alignpress.core.profile import CalibrationInfo, LogoDefinition

    # Create dummy template files
    template_a = tmp_path / "logo_a.png"
    template_b = tmp_path / "logo_b.png"
    import cv2
    import numpy as np
    cv2.imwrite(str(template_a), np.zeros((50, 50, 3), dtype=np.uint8))
    cv2.imwrite(str(template_b), np.zeros((50, 50, 3), dtype=np.uint8))

    # Create mock platen
    platen = PlatenProfile(
        name="test_platen",
        version=1,
        type="platen",
        dimensions_mm={"width": 300.0, "height": 200.0},
        calibration=CalibrationInfo(
            camera_id=0,
            last_calibrated=datetime.now(),
            homography_path="calibration/test.npz",
            mm_per_px=0.5
        )
    )

    # Create mock style
    style = StyleProfile(
        name="test_style",
        version=1,
        type="style",
        logos=[
            LogoDefinition(
                name="logo_a",
                template_path=str(template_a),
                position_mm=[100.0, 100.0],
                roi={"width_mm": 50.0, "height_mm": 50.0}
            ),
            LogoDefinition(
                name="logo_b",
                template_path=str(template_b),
                position_mm=[200.0, 100.0],
                roi={"width_mm": 50.0, "height_mm": 50.0}
            )
        ]
    )

    return Composition(platen=platen, style=style, variant=None)


@pytest.fixture
def mock_results_all_perfect():
    """Create mock results with all logos perfect."""
    return {
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
            status="PERFECT",
            detected_position=(200.0, 100.0),
            expected_position=(200.0, 100.0),
            deviation_mm=0.3,
            angle_deg=0.0,
            angle_error_deg=0.1,
            inliers_count=48,
            total_keypoints=52,
            inlier_ratio=0.92,
            reproj_error_px=0.7
        )
    }


@pytest.fixture
def mock_results_mixed():
    """Create mock results with mixed status."""
    return {
        "logo_a": LogoResultSchema(
            logo_name="logo_a",
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
        ),
        "logo_b": LogoResultSchema(
            logo_name="logo_b",
            found=True,
            detected_position=(205.0, 102.0),
            expected_position=(200.0, 100.0),
            deviation_mm=5.4,  # > 4.0 (good threshold) -> NEEDS_ADJUSTMENT
            angle_deg=3.2,
            angle_error_deg=3.2,
            inliers_count=38,
            total_keypoints=50,
            inlier_ratio=0.76,
            reproj_error_px=2.1
        )
    }


@pytest.fixture
def mock_snapshot():
    """Create mock snapshot image."""
    # Create simple test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (50, 50, 100)  # Dark blue background
    return img


class TestValidationChecklistDialog:
    """Tests for ValidationChecklistDialog."""

    def test_dialog_initialization(self, qapp, mock_composition, mock_results_all_perfect):
        """Test dialog initializes correctly."""
        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            operator="test_operator"
        )

        assert dialog.composition == mock_composition
        assert dialog.results == mock_results_all_perfect
        assert dialog.operator == "test_operator"
        assert dialog.total_logos == 2
        assert dialog.detected_count == 2
        assert dialog.perfect_count == 2

        dialog.close()

    def test_all_perfect_enables_confirm(self, qapp, mock_composition, mock_results_all_perfect):
        """Test confirm button enabled when all logos perfect."""
        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            operator="test_operator"
        )

        assert dialog.confirm_btn.isEnabled()
        assert dialog.detected_count == dialog.total_logos

        dialog.close()

    def test_missing_detection_disables_confirm(self, qapp, mock_composition):
        """Test confirm button disabled when logos missing."""
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
            # logo_b is missing
        }

        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=results,
            operator="test_operator"
        )

        assert not dialog.confirm_btn.isEnabled()
        assert dialog.detected_count < dialog.total_logos

        dialog.close()

    def test_statistics_calculation(self, qapp, mock_composition, mock_results_mixed):
        """Test statistics are calculated correctly."""
        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_mixed,
            operator="test_operator"
        )

        assert dialog.total_logos == 2
        assert dialog.detected_count == 2
        assert dialog.perfect_count == 0
        assert dialog.good_count == 1
        assert dialog.needs_adjustment == 1

        dialog.close()

    def test_logo_items_created(self, qapp, mock_composition, mock_results_all_perfect):
        """Test logo items are created for each logo."""
        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            operator="test_operator"
        )

        # Check that items were created (2 logo items + 1 stretch)
        assert dialog.results_layout.count() >= 2

        dialog.close()

    def test_reject_emits_signal(self, qapp, mock_composition, mock_results_all_perfect):
        """Test reject button emits signal."""
        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            operator="test_operator"
        )

        rejected = False

        def on_rejected():
            nonlocal rejected
            rejected = True

        dialog.job_rejected.connect(on_rejected)

        # Simulate back button click
        dialog._on_reject()

        assert rejected

        dialog.close()

    def test_confirm_creates_job_card(self, qapp, mock_composition, mock_results_all_perfect, tmp_path, monkeypatch):
        """Test confirm creates and saves job card."""
        # Change to temp directory for test
        monkeypatch.chdir(tmp_path)

        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            snapshot=None,
            operator="test_operator"
        )

        confirmed = False
        captured_job_card = None

        def on_confirmed(job_card):
            nonlocal confirmed, captured_job_card
            confirmed = True
            captured_job_card = job_card

        dialog.job_confirmed.connect(on_confirmed)

        # Add some notes
        dialog.notes_edit.setPlainText("Test notes")

        # Simulate confirm
        dialog._on_confirm()

        assert confirmed
        assert captured_job_card is not None
        assert captured_job_card.operator == "test_operator"
        assert len(captured_job_card.results) == 2
        assert captured_job_card.notes == "Test notes"

        dialog.close()

    def test_snapshot_saved(self, qapp, mock_composition, mock_results_all_perfect, mock_snapshot, tmp_path, monkeypatch):
        """Test snapshot is saved when provided."""
        # Change to temp directory for test
        monkeypatch.chdir(tmp_path)

        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            snapshot=mock_snapshot,
            operator="test_operator"
        )

        # Simulate confirm
        dialog._on_confirm()

        # Check snapshot directory was created
        snapshots_dir = tmp_path / "logs" / "snapshots"
        assert snapshots_dir.exists()

        # Check that a snapshot file exists
        snapshot_files = list(snapshots_dir.glob("*.jpg"))
        assert len(snapshot_files) > 0

        dialog.close()

    def test_job_card_json_saved(self, qapp, mock_composition, mock_results_all_perfect, tmp_path, monkeypatch):
        """Test job card JSON is saved."""
        # Change to temp directory for test
        monkeypatch.chdir(tmp_path)

        dialog = ValidationChecklistDialog(
            composition=mock_composition,
            results=mock_results_all_perfect,
            operator="test_operator"
        )

        # Simulate confirm
        dialog._on_confirm()

        # Check jobs directory was created
        jobs_dir = tmp_path / "logs" / "jobs"
        assert jobs_dir.exists()

        # Check that a job card JSON exists
        job_files = list(jobs_dir.glob("*.json"))
        assert len(job_files) > 0

        dialog.close()
