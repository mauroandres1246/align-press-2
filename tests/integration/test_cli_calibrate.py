"""Integration tests for CLI calibration tool."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import numpy as np

from alignpress.cli.calibrate import CameraCalibrator


class TestCameraCalibrator:
    """Test CameraCalibrator class."""

    @pytest.fixture
    def calibrator(self):
        """Create calibrator instance."""
        return CameraCalibrator(
            camera_id=0,
            pattern_size=(9, 6),
            square_size_mm=25.0
        )

    def test_calibrator_initialization(self, calibrator):
        """Test calibrator initializes correctly."""
        assert calibrator.camera_id == 0
        assert calibrator.pattern_size == (9, 6)
        assert calibrator.square_size_mm == 25.0
        assert calibrator.cap is None
        assert len(calibrator.captured_frames) == 0
        assert len(calibrator.captured_corners) == 0
        assert calibrator.image_size is None
        assert calibrator.homography is None
        assert calibrator.mm_per_px is None
        assert calibrator.quality_metrics == {}

    @patch('cv2.VideoCapture')
    def test_open_camera_success(self, mock_capture, calibrator):
        """Test opening camera successfully."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_capture.return_value = mock_cap

        result = calibrator.open_camera()

        assert result is True
        assert calibrator.cap is not None
        # Check that camera properties were set
        assert mock_cap.set.call_count >= 3

    @patch('cv2.VideoCapture')
    def test_open_camera_failure(self, mock_capture, calibrator):
        """Test opening camera failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_capture.return_value = mock_cap

        result = calibrator.open_camera()

        assert result is False

    @patch('cv2.VideoCapture')
    def test_open_camera_exception(self, mock_capture, calibrator):
        """Test camera opening with exception."""
        mock_capture.side_effect = Exception("Camera error")

        result = calibrator.open_camera()

        assert result is False

    def test_close_camera(self, calibrator):
        """Test closing camera."""
        mock_cap = MagicMock()
        calibrator.cap = mock_cap

        calibrator.close_camera()

        mock_cap.release.assert_called_once()

    def test_close_camera_with_no_cap(self, calibrator):
        """Test closing camera when cap is None."""
        calibrator.cap = None

        # Should not crash
        calibrator.close_camera()

    @patch('cv2.findChessboardCorners')
    @patch('cv2.cvtColor')
    @patch('cv2.cornerSubPix')
    def test_detect_chessboard_found(self, mock_subpix, mock_cvtcolor, mock_find, calibrator):
        """Test detecting chessboard successfully."""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        gray = np.zeros((480, 640), dtype=np.uint8)
        corners = np.random.rand(54, 1, 2).astype(np.float32)
        refined_corners = corners * 1.01  # Slightly different

        mock_cvtcolor.return_value = gray
        mock_find.return_value = (True, corners)
        mock_subpix.return_value = refined_corners

        found, result_corners = calibrator.detect_chessboard(image)

        assert found is True
        assert result_corners is not None
        mock_subpix.assert_called_once()

    @patch('cv2.findChessboardCorners')
    @patch('cv2.cvtColor')
    def test_detect_chessboard_not_found(self, mock_cvtcolor, mock_find, calibrator):
        """Test chessboard not found."""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        gray = np.zeros((480, 640), dtype=np.uint8)

        mock_cvtcolor.return_value = gray
        mock_find.return_value = (False, None)

        found, corners = calibrator.detect_chessboard(image)

        assert found is False
        assert corners is None

    def test_calculate_calibration_insufficient_frames(self, calibrator):
        """Test calibration with insufficient frames."""
        calibrator.captured_frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        calibrator.captured_corners = [np.zeros((54, 1, 2), dtype=np.float32)]

        result = calibrator.calculate_calibration()

        assert result is False

    @patch('cv2.calibrateCamera')
    @patch('cv2.findHomography')
    @patch('cv2.projectPoints')
    def test_calculate_calibration_success(self, mock_project, mock_homography, mock_calibrate, calibrator):
        """Test successful calibration calculation."""
        # Setup captured data
        calibrator.captured_frames = [
            np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)
        ]
        calibrator.captured_corners = [
            np.random.rand(54, 1, 2).astype(np.float32) for _ in range(5)
        ]
        calibrator.image_size = (640, 480)

        # Mock calibrateCamera
        camera_matrix = np.eye(3)
        dist_coeffs = np.zeros(5)
        rvecs = [np.zeros((3, 1)) for _ in range(5)]
        tvecs = [np.zeros((3, 1)) for _ in range(5)]
        mock_calibrate.return_value = (True, camera_matrix, dist_coeffs, rvecs, tvecs)

        # Mock projectPoints for error calculation
        mock_project.return_value = (np.random.rand(54, 1, 2).astype(np.float32), None)

        # Mock homography
        mock_homography.return_value = (np.eye(3), np.ones((54, 1), dtype=np.uint8))

        result = calibrator.calculate_calibration()

        assert result is True
        assert calibrator.homography is not None
        assert calibrator.mm_per_px is not None
        assert len(calibrator.quality_metrics) > 0

    @patch('cv2.calibrateCamera')
    def test_calculate_calibration_camera_calibration_fails(self, mock_calibrate, calibrator):
        """Test calibration when camera calibration fails."""
        calibrator.captured_frames = [
            np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)
        ]
        calibrator.captured_corners = [
            np.random.rand(54, 1, 2).astype(np.float32) for _ in range(5)
        ]
        calibrator.image_size = (640, 480)

        mock_calibrate.return_value = (False, None, None, None, None)

        result = calibrator.calculate_calibration()

        assert result is False

    @patch('cv2.calibrateCamera')
    @patch('cv2.findHomography')
    @patch('cv2.projectPoints')
    def test_calculate_calibration_homography_fails(self, mock_project, mock_homography, mock_calibrate, calibrator):
        """Test calibration when homography calculation fails."""
        calibrator.captured_frames = [
            np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)
        ]
        calibrator.captured_corners = [
            np.random.rand(54, 1, 2).astype(np.float32) for _ in range(5)
        ]
        calibrator.image_size = (640, 480)

        mock_calibrate.return_value = (
            True, np.eye(3), np.zeros(5),
            [np.zeros((3, 1)) for _ in range(5)],
            [np.zeros((3, 1)) for _ in range(5)]
        )
        mock_project.return_value = (np.random.rand(54, 1, 2).astype(np.float32), None)
        mock_homography.return_value = (None, None)

        result = calibrator.calculate_calibration()

        assert result is False

    def test_check_scale_consistency(self, calibrator):
        """Test scale consistency check."""
        # Create mock corners with consistent spacing
        corners = np.array([[[i * 10.0, 0.0]] for i in range(20)], dtype=np.float32)
        calibrator.captured_corners = [corners]
        calibrator.square_size_mm = 25.0

        consistency = calibrator._check_scale_consistency()

        # Should be low (consistent)
        assert isinstance(consistency, float)
        assert consistency >= 0.0

    def test_check_scale_consistency_no_corners(self, calibrator):
        """Test scale consistency with no corners."""
        calibrator.captured_corners = []

        consistency = calibrator._check_scale_consistency()

        assert consistency == float('inf')

    def test_save_calibration_no_data(self, calibrator, tmp_path):
        """Test saving calibration without data."""
        output_path = tmp_path / "calibration.npz"

        result = calibrator.save_calibration(output_path, camera_id=0)

        assert result is False

    def test_save_calibration_success(self, calibrator, tmp_path):
        """Test successful calibration save."""
        output_path = tmp_path / "calibration.json"

        # Set calibration data
        calibrator.homography = np.eye(3)
        calibrator.mm_per_px = 0.5
        calibrator.pattern_size = (9, 6)
        calibrator.square_size_mm = 25.0
        calibrator.quality_metrics = {
            "reproj_error_px": 1.5,
            "corners_detected": 54,
            "corners_expected": 54,
            "captures_used": 5,
            "homography_condition": 10.0,
            "scale_consistency": 0.02
        }

        result = calibrator.save_calibration(output_path, camera_id=0)

        assert result is True
        assert output_path.exists()

        # Verify JSON content
        import json
        with open(output_path) as f:
            data = json.load(f)
            assert data["camera_id"] == 0
            assert "homography" in data
            assert data["mm_per_px"] == 0.5


class TestCalibratorIntegration:
    """Integration tests for calibrator workflow."""

    def test_full_workflow_without_camera(self, tmp_path):
        """Test full calibration workflow without actual camera."""
        calibrator = CameraCalibrator(
            camera_id=0,
            pattern_size=(9, 6),
            square_size_mm=25.0
        )

        # Simulate captured data
        calibrator.captured_frames = [
            np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)
        ]
        calibrator.captured_corners = [
            np.random.rand(54, 1, 2).astype(np.float32) for _ in range(5)
        ]
        calibrator.image_size = (640, 480)

        # Mock calibration methods
        with patch('cv2.calibrateCamera') as mock_cal, \
             patch('cv2.findHomography') as mock_hom, \
             patch('cv2.projectPoints') as mock_proj:

            mock_cal.return_value = (
                True, np.eye(3), np.zeros(5),
                [np.zeros((3, 1)) for _ in range(5)],
                [np.zeros((3, 1)) for _ in range(5)]
            )
            mock_proj.return_value = (np.random.rand(54, 1, 2).astype(np.float32), None)
            mock_hom.return_value = (np.eye(3), np.ones((54, 1), dtype=np.uint8))

            # Calculate calibration
            success = calibrator.calculate_calibration()
            assert success is True

            # Save calibration
            output_path = tmp_path / "test_calibration.json"
            calibrator.pattern_size = (9, 6)
            calibrator.square_size_mm = 25.0
            save_success = calibrator.save_calibration(output_path, camera_id=0)
            assert save_success is True
            assert output_path.exists()
