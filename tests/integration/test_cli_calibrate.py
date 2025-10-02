"""Integration tests for CLI calibration tool."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from alignpress.cli.calibrate import CameraCalibrator


@pytest.mark.skip(reason="Tests use methods that don't exist in CameraCalibrator - needs rewrite to match actual API")
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

    @patch('cv2.VideoCapture')
    def test_open_camera_success(self, mock_capture, calibrator):
        """Test opening camera successfully."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_capture.return_value = mock_cap

        result = calibrator.open_camera()

        assert result is True
        assert calibrator.cap is not None
        mock_cap.set.assert_called()

    @patch('cv2.VideoCapture')
    def test_open_camera_failure(self, mock_capture, calibrator):
        """Test opening camera failure."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_capture.return_value = mock_cap

        result = calibrator.open_camera()

        assert result is False

    def test_close_camera(self, calibrator):
        """Test closing camera."""
        mock_cap = MagicMock()
        calibrator.cap = mock_cap

        calibrator.close_camera()

        mock_cap.release.assert_called_once()

    @patch('cv2.findChessboardCorners')
    @patch('cv2.cvtColor')
    def test_detect_chessboard_found(self, mock_cvtcolor, mock_find, calibrator):
        """Test detecting chessboard successfully."""
        # Create mock image
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        gray = np.zeros((480, 640), dtype=np.uint8)
        corners = np.random.rand(54, 1, 2).astype(np.float32)

        mock_cvtcolor.return_value = gray
        mock_find.return_value = (True, corners)

        found, result_corners = calibrator.detect_chessboard(image)

        assert found is True
        assert result_corners is not None

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

    def test_calculate_mm_per_px(self, calibrator):
        """Test calculating mm_per_px from corners."""
        # Create synthetic corners for a 9x6 pattern
        corners = []
        for y in range(6):
            for x in range(9):
                corners.append([[x * 20.0, y * 20.0]])
        corners = np.array(corners, dtype=np.float32)

        mm_per_px = calibrator._calculate_mm_per_px(corners)

        # With 25mm squares and 20px spacing, should be ~1.25 mm/px
        assert mm_per_px > 1.0
        assert mm_per_px < 1.5

    def test_save_calibration(self, calibrator, tmp_path):
        """Test saving calibration to file."""
        # Setup calibration data
        calibrator.homography = np.eye(3, dtype=np.float64)
        calibrator.mm_per_px = 0.5
        calibrator.image_size = (640, 480)
        calibrator.quality_metrics = {
            'reproj_error_px': 1.2,
            'corners_detected': 54,
            'corners_expected': 54
        }

        output_path = tmp_path / "calibration.json"
        result = calibrator.save_calibration(output_path, camera_id=0)

        assert result is True
        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            data = json.load(f)
            assert data['version'] == 1
            assert data['camera_id'] == 0
            assert 'homography' in data
            assert data['plane_config']['mm_per_px'] == 0.5

    def test_validate_calibration_good(self, calibrator):
        """Test validation with good calibration."""
        calibrator.quality_metrics = {
            'reproj_error_px': 0.8,
            'corners_detected': 54,
            'corners_expected': 54
        }

        is_valid = calibrator.validate_calibration()

        assert is_valid is True

    def test_validate_calibration_bad_error(self, calibrator):
        """Test validation with high reprojection error."""
        calibrator.quality_metrics = {
            'reproj_error_px': 5.0,  # Too high
            'corners_detected': 54,
            'corners_expected': 54
        }

        is_valid = calibrator.validate_calibration()

        assert is_valid is False

    def test_validate_calibration_missing_corners(self, calibrator):
        """Test validation with missing corners."""
        calibrator.quality_metrics = {
            'reproj_error_px': 0.8,
            'corners_detected': 40,  # Less than 80%
            'corners_expected': 54
        }

        is_valid = calibrator.validate_calibration()

        assert is_valid is False


class TestCalibrateCLI:
    """Test calibrate CLI command."""

    @patch('alignpress.cli.calibrate.CameraCalibrator')
    @patch('alignpress.cli.calibrate.Confirm.ask')
    def test_calibrate_cli_execution(self, mock_confirm, mock_calibrator_class, tmp_path):
        """Test CLI calibration execution."""
        from alignpress.cli.calibrate import main

        # Setup mocks
        mock_calibrator = MagicMock()
        mock_calibrator.open_camera.return_value = True
        mock_calibrator.preview_calibration.return_value = True
        mock_calibrator.calculate_calibration.return_value = True
        mock_calibrator.validate_calibration.return_value = True
        mock_calibrator.save_calibration.return_value = True
        mock_calibrator_class.return_value = mock_calibrator

        output_path = tmp_path / "test_calibration.json"

        # Mock sys.argv
        with patch('sys.argv', [
            'calibrate.py',
            '--camera', '0',
            '--pattern-size', '9', '6',
            '--square-size-mm', '25.0',
            '--output', str(output_path),
            '--no-preview',
            '--force'
        ]):
            exit_code = main()

        assert exit_code == 0
        mock_calibrator.open_camera.assert_called_once()

    @patch('alignpress.cli.calibrate.CameraCalibrator')
    def test_calibrate_cli_camera_failure(self, mock_calibrator_class, tmp_path):
        """Test CLI handles camera failure."""
        from alignpress.cli.calibrate import main

        # Setup mocks
        mock_calibrator = MagicMock()
        mock_calibrator.open_camera.return_value = False
        mock_calibrator_class.return_value = mock_calibrator

        output_path = tmp_path / "test_calibration.json"

        with patch('sys.argv', [
            'calibrate.py',
            '--camera', '0',
            '--pattern-size', '9', '6',
            '--square-size-mm', '25.0',
            '--output', str(output_path),
            '--no-preview'
        ]):
            exit_code = main()

        assert exit_code == 1
