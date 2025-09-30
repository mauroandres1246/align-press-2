"""
Unit tests for detector transparency support.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import Mock, patch

from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import (
    DetectorConfigSchema, PlaneConfigSchema, FeatureParamsSchema,
    ROIConfigSchema, LogoSpecSchema
)


class TestDetectorTransparencySupport:
    """Test detector's alpha channel support."""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create sample configuration for testing."""
        # Create test template with alpha
        template_rgba = np.random.randint(0, 255, (50, 50, 4), dtype=np.uint8)
        template_path = tmp_path / "test_logo.png"
        cv2.imwrite(str(template_path), template_rgba)

        return DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            features=FeatureParamsSchema(
                feature_type="ORB",
                nfeatures=1000
            ),
            logos=[
                LogoSpecSchema(
                    name="test_logo",
                    template_path=template_path,
                    position_mm=(150.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    ),
                    has_transparency=True,
                    transparency_method="contour"
                )
            ]
        )

    def test_detector_loads_template_with_alpha(self, sample_config):
        """Test that detector can load templates with alpha channels."""
        detector = PlanarLogoDetector(sample_config)

        # Check that the template was loaded
        assert "test_logo" in detector._templates
        assert "test_logo" in detector._template_alpha_masks

        # Check that alpha mask was stored
        alpha_mask = detector._template_alpha_masks["test_logo"]
        assert alpha_mask is not None
        assert alpha_mask.shape == (50, 50)

    def test_detector_loads_template_without_alpha(self, tmp_path):
        """Test that detector handles templates without alpha channels."""
        # Create test template without alpha
        template_rgb = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        template_path = tmp_path / "test_logo_no_alpha.png"
        cv2.imwrite(str(template_path), template_rgb)

        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            features=FeatureParamsSchema(
                feature_type="ORB",
                nfeatures=1000
            ),
            logos=[
                LogoSpecSchema(
                    name="test_logo_no_alpha",
                    template_path=template_path,
                    position_mm=(150.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    ),
                    has_transparency=False
                )
            ]
        )

        detector = PlanarLogoDetector(config)

        # Check that the template was loaded
        assert "test_logo_no_alpha" in detector._templates
        assert "test_logo_no_alpha" in detector._template_alpha_masks

        # Check that alpha mask is None
        alpha_mask = detector._template_alpha_masks["test_logo_no_alpha"]
        assert alpha_mask is None

    def test_detector_enhance_logo_contrast_called(self, sample_config):
        """Test that enhance_logo_contrast is called during template loading."""
        with patch('alignpress.core.detector.enhance_logo_contrast') as mock_enhance:
            mock_enhance.return_value = np.random.randint(0, 255, (50, 50), dtype=np.uint8)

            detector = PlanarLogoDetector(sample_config)

            # Verify enhance_logo_contrast was called with alpha mask
            mock_enhance.assert_called()
            args, kwargs = mock_enhance.call_args_list[0]
            assert len(args) == 2  # template_gray, alpha_mask
            assert args[1] is not None  # alpha_mask should be provided

    def test_detector_handles_invalid_template_path(self, tmp_path):
        """Test error handling for invalid template paths."""
        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            features=FeatureParamsSchema(
                feature_type="ORB",
                nfeatures=1000
            ),
            logos=[
                LogoSpecSchema(
                    name="invalid_logo",
                    template_path=tmp_path / "nonexistent.png",
                    position_mm=(150.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    )
                )
            ]
        )

        with pytest.raises(FileNotFoundError):
            PlanarLogoDetector(config)

    def test_detector_template_data_consistency(self, sample_config):
        """Test that all template data structures are consistent."""
        detector = PlanarLogoDetector(sample_config)

        logo_name = "test_logo"

        # All data structures should have the same keys
        assert logo_name in detector._templates
        assert logo_name in detector._template_keypoints
        assert logo_name in detector._template_descriptors
        assert logo_name in detector._template_alpha_masks

        # Template should be grayscale enhanced version
        template = detector._templates[logo_name]
        assert len(template.shape) == 2  # Grayscale
        assert template.dtype == np.uint8

    @pytest.fixture
    def detector_with_alpha_template(self, sample_config):
        """Create detector with alpha template for testing."""
        return PlanarLogoDetector(sample_config)

    def test_alpha_mask_preserved_during_processing(self, detector_with_alpha_template):
        """Test that alpha mask is preserved during template processing."""
        detector = detector_with_alpha_template
        logo_name = "test_logo"

        alpha_mask = detector._template_alpha_masks[logo_name]

        # Alpha mask should be single channel
        assert len(alpha_mask.shape) == 2
        assert alpha_mask.dtype == np.uint8

        # Alpha mask should have same dimensions as template
        template = detector._templates[logo_name]
        assert alpha_mask.shape == template.shape


class TestDetectorWithRealAlphaTemplates:
    """Test detector with more realistic alpha templates."""

    def create_logo_with_transparency(self, tmp_path, name: str, size: tuple = (60, 40)):
        """Create a realistic logo with transparency."""
        height, width = size

        # Create RGBA image
        logo = np.zeros((height, width, 4), dtype=np.uint8)

        # Create logo content (e.g., circle or rectangle)
        center_x, center_y = width // 2, height // 2
        if name == "circle_logo":
            cv2.circle(logo, (center_x, center_y), min(width, height) // 3,
                      (255, 0, 0, 255), -1)  # Red circle with full alpha
        elif name == "rect_logo":
            cv2.rectangle(logo, (width//4, height//4), (3*width//4, 3*height//4),
                         (0, 255, 0, 255), -1)  # Green rectangle with full alpha

        # Add some transparency gradient
        for y in range(height):
            for x in range(width):
                if logo[y, x, 3] > 0:  # If pixel is not transparent
                    # Add gradient transparency based on distance from center
                    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                    max_dist = np.sqrt(center_x**2 + center_y**2)
                    alpha_val = max(0, 255 - int(dist / max_dist * 100))
                    logo[y, x, 3] = alpha_val

        logo_path = tmp_path / f"{name}.png"
        cv2.imwrite(str(logo_path), logo)
        return logo_path

    def test_detector_with_circle_logo(self, tmp_path):
        """Test detector with circular logo having alpha channel."""
        logo_path = self.create_logo_with_transparency(tmp_path, "circle_logo")

        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            features=FeatureParamsSchema(
                feature_type="ORB",
                nfeatures=1000
            ),
            logos=[
                LogoSpecSchema(
                    name="circle_logo",
                    template_path=logo_path,
                    position_mm=(150.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    ),
                    has_transparency=True,
                    transparency_method="contour"
                )
            ]
        )

        detector = PlanarLogoDetector(config)

        # Verify template was loaded successfully
        assert "circle_logo" in detector._templates
        alpha_mask = detector._template_alpha_masks["circle_logo"]
        assert alpha_mask is not None

        # Alpha mask should have varying transparency values
        unique_values = np.unique(alpha_mask)
        assert len(unique_values) > 2  # Should have gradient, not just 0 and 255

    def test_detector_with_multiple_alpha_templates(self, tmp_path):
        """Test detector with multiple templates having alpha channels."""
        circle_path = self.create_logo_with_transparency(tmp_path, "circle_logo")
        rect_path = self.create_logo_with_transparency(tmp_path, "rect_logo")

        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            features=FeatureParamsSchema(
                feature_type="ORB",
                nfeatures=1000
            ),
            logos=[
                LogoSpecSchema(
                    name="circle_logo",
                    template_path=circle_path,
                    position_mm=(100.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    ),
                    has_transparency=True,
                    transparency_method="contour"
                ),
                LogoSpecSchema(
                    name="rect_logo",
                    template_path=rect_path,
                    position_mm=(200.0, 100.0),
                    roi=ROIConfigSchema(
                        width_mm=50.0,
                        height_mm=40.0,
                        margin_factor=1.2
                    ),
                    has_transparency=True,
                    transparency_method="threshold"
                )
            ]
        )

        detector = PlanarLogoDetector(config)

        # Verify both templates were loaded
        assert "circle_logo" in detector._templates
        assert "rect_logo" in detector._templates

        # Both should have alpha masks
        assert detector._template_alpha_masks["circle_logo"] is not None
        assert detector._template_alpha_masks["rect_logo"] is not None

        # Templates should be processed separately
        circle_template = detector._templates["circle_logo"]
        rect_template = detector._templates["rect_logo"]
        assert not np.array_equal(circle_template, rect_template)