"""
Unit tests for PlanarLogoDetector.

Tests cover:
- Initialization and configuration loading
- Coordinate conversions (mm <-> px)
- Logo detection with various transformations
- Fallback template matching
- ROI extraction
- Error handling
"""

import pytest
import numpy as np
import cv2
from pathlib import Path

from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import (
    PlaneConfigSchema, LogoSpecSchema, ThresholdsSchema,
    FeatureParamsSchema, FallbackParamsSchema, ROIConfigSchema
)


# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CONFIGS_DIR = FIXTURES_DIR / "configs"
IMAGES_DIR = FIXTURES_DIR / "images"
TEMPLATES_DIR = FIXTURES_DIR / "templates"


@pytest.fixture
def detector_config():
    """Fixture: Detector configuration for testing."""
    return {
        "plane": {
            "width_mm": 300.0,
            "height_mm": 200.0,
            "mm_per_px": 0.5,
            "homography": None
        },
        "logos": [
            {
                "name": "logo_a",
                "template_path": str(TEMPLATES_DIR / "mock_template_a.png"),
                "position_mm": (150.0, 100.0),
                "angle_deg": 0.0,
                "roi": {
                    "width_mm": 80.0,
                    "height_mm": 60.0,
                    "margin_factor": 1.5
                }
            }
        ],
        "thresholds": {
            "max_position_error_mm": 3.0,
            "max_angle_error_deg": 5.0,
            "min_inliers": 15,
            "max_reproj_error_px": 3.0
        },
        "feature_params": {
            "type": "ORB",
            "nfeatures": 1500,
            "scaleFactor": 1.2,
            "nlevels": 8,
            "edgeThreshold": 31,
            "patchSize": 31
        },
        "matching_params": {
            "algorithm": "BF",
            "normType": "HAMMING",
            "crossCheck": True,
            "ratio_test_threshold": 0.75
        },
        "fallback": {
            "enabled": False,
            "scales": [0.8, 0.9, 1.0, 1.1, 1.2],
            "angles_deg": [-10, -5, 0, 5, 10],
            "match_threshold": 0.7
        }
    }


@pytest.fixture
def detector(detector_config):
    """Fixture: Initialized detector instance."""
    return PlanarLogoDetector(detector_config)


class TestDetectorInitialization:
    """Test detector initialization and configuration."""

    def test_detector_initialization_success(self, detector_config):
        """Test successful detector initialization."""
        detector = PlanarLogoDetector(detector_config)

        assert detector is not None
        assert len(detector.config.logos) == 1
        assert detector.config.plane.width_mm == 300.0
        assert detector.config.plane.height_mm == 200.0

    def test_detector_loads_templates(self, detector):
        """Test that templates are loaded correctly."""
        logo_name = "logo_a"
        assert logo_name in detector._templates
        template = detector._templates[logo_name]
        assert template is not None
        assert len(template.shape) == 2  # Grayscale
        assert template.dtype == np.uint8

    def test_detector_invalid_template_path(self, detector_config):
        """Test error handling for invalid template path."""
        detector_config["logos"][0]["template_path"] = "nonexistent.png"

        with pytest.raises(FileNotFoundError, match="Template not found"):
            PlanarLogoDetector(detector_config)

    def test_detector_missing_config_keys(self):
        """Test error handling for missing config keys."""
        invalid_config = {"plane": {"width_mm": 300.0}}

        with pytest.raises((KeyError, ValueError)):
            PlanarLogoDetector(invalid_config)

    def test_detector_feature_detector_initialization(self, detector):
        """Test that feature detector is initialized."""
        assert detector._feature_detector is not None
        # Should be ORB detector
        assert hasattr(detector._feature_detector, 'detect')

    def test_detector_matcher_initialization(self, detector):
        """Test that matcher is initialized."""
        assert detector._feature_matcher is not None
        assert hasattr(detector._feature_matcher, 'match')


class TestCoordinateConversions:
    """Test coordinate conversion methods."""

    def test_mm_to_px_conversion(self, detector):
        """Test millimeter to pixel conversion."""
        # 0.5 mm/px means 2 pixels per mm
        x_px, y_px = detector.mm_to_px(10.0, 5.0)

        assert x_px == 20  # 10mm * 2px/mm
        assert y_px == 10  # 5mm * 2px/mm

    def test_px_to_mm_conversion(self, detector):
        """Test pixel to millimeter conversion."""
        # 0.5 mm/px
        x_mm, y_mm = detector.px_to_mm(20, 10)

        assert abs(x_mm - 10.0) < 1e-6
        assert abs(y_mm - 5.0) < 1e-6

    def test_conversion_roundtrip(self, detector):
        """Test roundtrip conversion accuracy."""
        original_mm = (15.3, 27.8)

        # Convert to pixels and back
        px = detector.mm_to_px(original_mm[0], original_mm[1])
        back_to_mm = detector.px_to_mm(px[0], px[1])

        # Should be close (within rounding error)
        assert abs(back_to_mm[0] - original_mm[0]) < 1.0
        assert abs(back_to_mm[1] - original_mm[1]) < 1.0

    def test_mm_to_px_edge_cases(self, detector):
        """Test edge cases for mm to px conversion."""
        # Zero values
        assert detector.mm_to_px(0.0, 0.0) == (0, 0)

        # Large values
        x_px, y_px = detector.mm_to_px(1000.0, 2000.0)
        assert x_px == 2000
        assert y_px == 4000


class TestLogoDetection:
    """Test logo detection functionality."""

    def test_detect_perfect_alignment(self, detector):
        """Test detection with perfectly aligned logo."""
        # Load image with logo in exact expected position
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        assert img is not None, "Failed to load test image"

        results = detector.detect(img)

        assert "logo_a" in results
        result = results["logo_a"]

        # Should be detected
        assert result["found"] is True

        # Position should be very close to expected
        detected_pos = result.get("detected_position_mm") or result.get("position_mm")
        expected_pos = (150.0, 100.0)
        error_x = abs(detected_pos[0] - expected_pos[0])
        error_y = abs(detected_pos[1] - expected_pos[1])

        assert error_x < 5.0, f"X error too large: {error_x}mm"
        assert error_y < 5.0, f"Y error too large: {error_y}mm"

        # Position error should be small
        assert result.get("error_mm", result.get("position_error_mm", 0)) < 5.0

        # Angle error should be small
        assert abs(result.get("angle_error_deg", 0)) < 5.0

    def test_detect_with_offset(self, detector):
        """Test detection with offset logo (5mm deviation)."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_offset.jpg"))
        assert img is not None

        results = detector.detect(img)
        result = results["logo_a"]

        # Should still detect
        assert result["found"] is True

        # Position error should reflect the 5mm offset
        # Allowing tolerance due to detector accuracy
        assert result["position_error_mm"] > 3.0  # At least 3mm error
        assert result["position_error_mm"] < 10.0  # But not too much

    def test_detect_with_rotation(self, detector):
        """Test detection with rotated logo (10 degrees)."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_rotated.jpg"))
        assert img is not None

        results = detector.detect(img)
        result = results["logo_a"]

        # Should detect even with rotation
        assert result["found"] is True

        # Angle error should reflect the 10-degree rotation
        assert abs(result["angle_error_deg"]) > 5.0
        assert abs(result["angle_error_deg"]) < 15.0

    def test_detect_no_logo(self, detector):
        """Test detection when logo is absent."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_empty.jpg"))
        assert img is not None

        results = detector.detect(img)
        result = results["logo_a"]

        # Should not detect
        assert result["found"] is False
        assert result["detected_position_mm"] is None

    def test_detect_single_logo_multi_config(self, detector_config):
        """Test detection with multiple logos configured but only one present."""
        # Add second logo to config
        detector_config["logos"].append({
            "name": "logo_b",
            "template_path": str(TEMPLATES_DIR / "mock_template_b.png"),
            "position_mm": (75.0, 50.0),
            "angle_deg": 0.0,
            "roi": {
                "width_mm": 60.0,
                "height_mm": 40.0,
                "margin_factor": 1.5
            }
        })

        detector = PlanarLogoDetector(detector_config)
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_single_logo.jpg"))

        results = detector.detect(img)

        # Logo A should be detected
        assert results["logo_a"]["found"] is True

        # Logo B should not be detected
        assert results["logo_b"]["found"] is False


class TestROIExtraction:
    """Test ROI extraction functionality."""

    def test_roi_centered_correctly(self, detector):
        """Test that ROI is centered around expected position."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        logo_name = "logo_a"

        # Get ROI for logo
        roi, roi_center = detector._extract_roi_for_logo(img, logo_name)

        assert roi is not None
        assert roi.size > 0

        # ROI should have reasonable dimensions
        assert roi.shape[0] > 50  # Height
        assert roi.shape[1] > 50  # Width

        # Center should be close to expected position in pixels
        expected_px = detector.mm_to_px(150.0, 100.0)
        assert abs(roi_center[0] - expected_px[0]) < 5
        assert abs(roi_center[1] - expected_px[1]) < 5

    def test_roi_with_margin_factor(self, detector):
        """Test that margin factor increases ROI size."""
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        logo_name = "logo_a"

        # Get default ROI
        roi1, _ = detector._extract_roi_for_logo(img, logo_name)

        # Increase margin factor
        original_margin = detector.logos[0].roi.margin_factor
        detector.logos[0].roi.margin_factor = 2.0

        roi2, _ = detector._extract_roi_for_logo(img, logo_name)

        # Restore original
        detector.logos[0].roi.margin_factor = original_margin

        # ROI with larger margin should be bigger
        assert roi2.shape[0] > roi1.shape[0]
        assert roi2.shape[1] > roi1.shape[1]


class TestFeatureMatching:
    """Test feature matching functionality."""

    def test_match_logo_returns_valid_result(self, detector):
        """Test that logo matching returns valid result structure."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        logo_name = "logo_a"

        roi, roi_center = detector._extract_roi_for_logo(img, logo_name)
        result = detector._match_logo(roi, logo_name, roi_center)

        # Should have all required keys
        assert "found" in result
        assert "detected_position_mm" in result
        assert "position_error_mm" in result
        assert "detected_angle_deg" in result
        assert "angle_error_deg" in result

        if result["found"]:
            assert "confidence" in result
            assert "inliers" in result
            assert result["confidence"] >= 0.0
            assert result["confidence"] <= 1.0

    def test_match_with_insufficient_features(self, detector):
        """Test matching with image that has too few features."""
        # Uniform image (no features)
        uniform_roi = np.ones((100, 100), dtype=np.uint8) * 128
        logo_name = "logo_a"
        roi_center = (300, 200)

        result = detector._match_logo(uniform_roi, logo_name, roi_center)

        # Should not detect
        assert result["found"] is False

    def test_match_computes_inliers(self, detector):
        """Test that matching computes inlier count."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        logo_name = "logo_a"

        roi, roi_center = detector._extract_roi_for_logo(img, logo_name)
        result = detector._match_logo(roi, logo_name, roi_center)

        if result["found"]:
            assert "inliers" in result
            assert result["inliers"] > 0
            # Should have reasonable number of inliers
            assert result["inliers"] >= detector.thresholds.min_inliers


class TestFallbackTemplateMatching:
    """Test fallback template matching."""

    def test_fallback_enabled(self, detector_config):
        """Test detector with fallback enabled."""
        detector_config["fallback"]["enabled"] = True
        detector = PlanarLogoDetector(detector_config)

        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        results = detector.detect(img)

        # Should still detect with fallback available
        assert results["logo_a"]["found"] is True

    def test_fallback_template_match_basic(self, detector):
        """Test basic fallback template matching."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        logo_name = "logo_a"

        roi, roi_center = detector._extract_roi_for_logo(img, logo_name)

        # Force fallback by using it directly
        if hasattr(detector, '_fallback_template_match'):
            result = detector._fallback_template_match(roi, logo_name, roi_center)

            # Fallback should find something
            assert result is not None
            if result["found"]:
                assert "match_score" in result
                assert result["match_score"] > 0


class TestErrorHandling:
    """Test error handling in detector."""

    def test_detect_with_none_image(self, detector):
        """Test detection with None image."""
        with pytest.raises((ValueError, AttributeError)):
            detector.detect(None)

    def test_detect_with_empty_image(self, detector):
        """Test detection with empty image."""
        empty_img = np.array([])

        with pytest.raises(ValueError):
            detector.detect(empty_img)

    def test_detect_with_wrong_dimensions(self, detector):
        """Test detection with wrong image dimensions."""
        # 1D array
        with pytest.raises(ValueError):
            detector.detect(np.zeros(100, dtype=np.uint8))

        # 4D array
        with pytest.raises(ValueError):
            detector.detect(np.zeros((10, 10, 3, 3), dtype=np.uint8))

    def test_detect_with_small_image(self, detector):
        """Test detection with image smaller than ROI."""
        tiny_img = np.zeros((10, 10, 3), dtype=np.uint8)

        # Should handle gracefully (not detect)
        results = detector.detect(tiny_img)
        assert results["logo_a"]["found"] is False


class TestDetectorConfiguration:
    """Test different detector configurations."""

    def test_detector_with_custom_thresholds(self, detector_config):
        """Test detector with custom thresholds."""
        detector_config["thresholds"]["max_position_error_mm"] = 10.0
        detector_config["thresholds"]["max_angle_error_deg"] = 15.0

        detector = PlanarLogoDetector(detector_config)

        assert detector.thresholds.max_position_error_mm == 10.0
        assert detector.thresholds.max_angle_error_deg == 15.0

    def test_detector_with_akaze_features(self, detector_config):
        """Test detector with AKAZE features."""
        detector_config["feature_params"]["type"] = "AKAZE"

        detector = PlanarLogoDetector(detector_config)

        # Should initialize successfully
        assert detector.feature_detector is not None

    def test_detector_with_flann_matcher(self, detector_config):
        """Test detector with FLANN matcher."""
        detector_config["matching_params"]["algorithm"] = "FLANN"

        detector = PlanarLogoDetector(detector_config)

        # Should initialize successfully
        assert detector.matcher is not None


class TestResultFormat:
    """Test result format and structure."""

    def test_result_has_all_required_fields(self, detector):
        """Test that results have all required fields."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        results = detector.detect(img)

        assert "logo_a" in results
        result = results["logo_a"]

        required_fields = [
            "found",
            "detected_position_mm",
            "expected_position_mm",
            "position_error_mm",
            "detected_angle_deg",
            "expected_angle_deg",
            "angle_error_deg"
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_result_types_are_correct(self, detector):
        """Test that result field types are correct."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        results = detector.detect(img)
        result = results["logo_a"]

        assert isinstance(result["found"], bool)

        if result["found"]:
            assert isinstance(result["detected_position_mm"], (list, tuple))
            assert len(result["detected_position_mm"]) == 2

            assert isinstance(result["position_error_mm"], (int, float))
            assert result["position_error_mm"] >= 0

            assert isinstance(result["detected_angle_deg"], (int, float))
            assert isinstance(result["angle_error_deg"], (int, float))

    def test_result_not_found_has_nulls(self, detector):
        """Test that unfound logos have appropriate null values."""
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_empty.jpg"))
        results = detector.detect(img)
        result = results["logo_a"]

        assert result["found"] is False
        assert result["detected_position_mm"] is None


# Integration-style test
class TestFullDetectionPipeline:
    """Test full detection pipeline end-to-end."""

    def test_full_pipeline_perfect_case(self, detector_config):
        """Test complete detection pipeline with perfect alignment."""
        # Initialize detector
        detector = PlanarLogoDetector(detector_config)

        # Load image
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))
        assert img is not None

        # Run detection
        results = detector.detect(img)

        # Verify results
        assert "logo_a" in results
        assert results["logo_a"]["found"] is True
        assert results["logo_a"]["position_error_mm"] < 5.0
        assert abs(results["logo_a"]["angle_error_deg"]) < 5.0

    def test_full_pipeline_multiple_logos(self, detector_config):
        """Test pipeline with multiple logos."""
        # Add second logo
        detector_config["logos"].append({
            "name": "logo_b",
            "template_path": str(TEMPLATES_DIR / "mock_template_b.png"),
            "position_mm": (75.0, 50.0),
            "angle_deg": 0.0,
            "roi": {
                "width_mm": 60.0,
                "height_mm": 40.0,
                "margin_factor": 1.5
            }
        })

        detector = PlanarLogoDetector(detector_config)
        img = cv2.imread(str(IMAGES_DIR / "mock_plane_perfect.jpg"))

        results = detector.detect(img)

        # Should have results for both logos
        assert "logo_a" in results
        assert "logo_b" in results

        # At least one should be detected
        detected_count = sum(1 for r in results.values() if r["found"])
        assert detected_count >= 1
