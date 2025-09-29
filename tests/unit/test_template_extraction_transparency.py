"""
Unit tests for template extraction with transparency support.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add the tools path for importing
sys.path.append(str(Path(__file__).parents[2] / "tools" / "testing"))

from extract_template import TemplateExtractor


class TestTemplateExtractorTransparency:
    """Test template extractor transparency functionality."""

    @pytest.fixture
    def extractor(self):
        """Create template extractor instance."""
        return TemplateExtractor()

    @pytest.fixture
    def sample_image_with_alpha(self, tmp_path):
        """Create sample RGBA image for testing."""
        # Create RGBA image with logo on transparent background
        image = np.zeros((100, 150, 4), dtype=np.uint8)

        # Add a logo (red rectangle) in the center
        cv2.rectangle(image, (50, 30), (100, 70), (0, 0, 255, 255), -1)

        # Add some transparency gradient
        for y in range(30, 70):
            for x in range(50, 100):
                dist_from_center = abs(x - 75) + abs(y - 50)
                alpha_val = max(0, 255 - dist_from_center * 5)
                image[y, x, 3] = alpha_val

        image_path = tmp_path / "sample_alpha.png"
        cv2.imwrite(str(image_path), image)
        return image_path

    @pytest.fixture
    def sample_image_without_alpha(self, tmp_path):
        """Create sample RGB image for testing."""
        # Create RGB image with logo
        image = np.ones((100, 150, 3), dtype=np.uint8) * 255  # White background

        # Add a logo (blue circle) in the center
        cv2.circle(image, (75, 50), 25, (255, 0, 0), -1)

        image_path = tmp_path / "sample_rgb.png"
        cv2.imwrite(str(image_path), image)
        return image_path

    def test_load_image_with_alpha_channel(self, extractor, sample_image_with_alpha):
        """Test loading image with alpha channel."""
        success = extractor.load_image(sample_image_with_alpha)

        assert success is True
        assert extractor.original_image is not None
        assert extractor.original_alpha is not None
        assert extractor.original_image.shape == (100, 150, 3)  # RGB
        assert extractor.original_alpha.shape == (100, 150)     # Single channel

    def test_load_image_without_alpha_channel(self, extractor, sample_image_without_alpha):
        """Test loading image without alpha channel."""
        success = extractor.load_image(sample_image_without_alpha)

        assert success is True
        assert extractor.original_image is not None
        assert extractor.original_alpha is None
        assert extractor.original_image.shape == (100, 150, 3)

    def test_interactive_roi_selection_preserves_alpha(self, extractor, sample_image_with_alpha):
        """Test that ROI selection preserves alpha channel."""
        extractor.load_image(sample_image_with_alpha)

        # Mock interactive selection to select center region
        with patch('cv2.selectROI', return_value=(40, 20, 60, 60)):
            success = extractor.interactive_roi_selection()

        assert success is True
        assert extractor.template is not None
        assert extractor.template_alpha is not None
        assert extractor.template.shape == (60, 60, 3)
        assert extractor.template_alpha.shape == (60, 60)

    def test_manual_roi_selection_preserves_alpha(self, extractor, sample_image_with_alpha):
        """Test that manual ROI selection preserves alpha channel."""
        extractor.load_image(sample_image_with_alpha)

        success = extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        assert success is True
        assert extractor.template is not None
        assert extractor.template_alpha is not None
        assert extractor.template.shape == (60, 60, 3)
        assert extractor.template_alpha.shape == (60, 60)

    def test_roi_selection_without_alpha(self, extractor, sample_image_without_alpha):
        """Test ROI selection on image without alpha."""
        extractor.load_image(sample_image_without_alpha)

        success = extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        assert success is True
        assert extractor.template is not None
        assert extractor.template_alpha is None
        assert extractor.template.shape == (60, 60, 3)

    def test_add_transparency_to_rgb_image(self, extractor, sample_image_without_alpha):
        """Test adding transparency to RGB image."""
        extractor.load_image(sample_image_without_alpha)
        extractor.manual_roi_selection(x=50, y=25, width=50, height=50)

        # Initially no alpha
        assert extractor.template_alpha is None

        # Add transparency using contour method
        success = extractor.add_transparency(method="contour")

        assert success is True
        assert extractor.template_alpha is not None
        assert extractor.template_alpha.shape == (50, 50)

    def test_add_transparency_different_methods(self, extractor, sample_image_without_alpha):
        """Test different transparency methods."""
        extractor.load_image(sample_image_without_alpha)
        extractor.manual_roi_selection(x=50, y=25, width=50, height=50)

        methods = ["contour", "threshold"]

        for method in methods:
            # Reset alpha
            extractor.template_alpha = None

            success = extractor.add_transparency(method=method)

            assert success is True, f"Method {method} failed"
            assert extractor.template_alpha is not None, f"Method {method} didn't create alpha"

    def test_add_transparency_already_has_alpha(self, extractor, sample_image_with_alpha):
        """Test adding transparency when image already has alpha."""
        extractor.load_image(sample_image_with_alpha)
        extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        # Should already have alpha
        assert extractor.template_alpha is not None
        original_alpha = extractor.template_alpha.copy()

        # Try to add transparency (should detect existing and skip)
        success = extractor.add_transparency(method="contour")

        assert success is True
        # Alpha should remain unchanged
        np.testing.assert_array_equal(extractor.template_alpha, original_alpha)

    def test_save_template_with_alpha(self, extractor, sample_image_with_alpha, tmp_path):
        """Test saving template with alpha channel."""
        extractor.load_image(sample_image_with_alpha)
        extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        output_path = tmp_path / "output_alpha.png"
        success = extractor.save_template(output_path)

        assert success is True
        assert output_path.exists()

        # Verify saved image has alpha
        saved_img = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        assert saved_img.shape[2] == 4  # RGBA

    def test_save_template_without_alpha(self, extractor, sample_image_without_alpha, tmp_path):
        """Test saving template without alpha channel."""
        extractor.load_image(sample_image_without_alpha)
        extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        output_path = tmp_path / "output_rgb.png"
        success = extractor.save_template(output_path)

        assert success is True
        assert output_path.exists()

        # Verify saved image doesn't have alpha
        saved_img = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        assert len(saved_img.shape) == 3  # RGB

    def test_template_quality_analysis_with_alpha(self, extractor, sample_image_with_alpha):
        """Test template quality analysis with alpha channel."""
        extractor.load_image(sample_image_with_alpha)
        extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        metrics = extractor.analyze_template_quality()

        assert isinstance(metrics, dict)
        assert "size" in metrics
        assert "sharpness" in metrics
        # Quality analysis should work regardless of alpha

    def test_enhance_template_with_alpha(self, extractor, sample_image_with_alpha):
        """Test template enhancement preserves alpha."""
        extractor.load_image(sample_image_with_alpha)
        extractor.manual_roi_selection(x=40, y=20, width=60, height=60)

        original_alpha = extractor.template_alpha.copy()

        # Mock user confirmation
        with patch('rich.prompt.Confirm.ask', return_value=True):
            success = extractor.enhance_template()

        assert success is True
        # Alpha should be preserved during enhancement
        np.testing.assert_array_equal(extractor.template_alpha, original_alpha)


class TestTemplateExtractorIntegration:
    """Integration tests for template extraction with transparency."""

    def create_complex_logo(self, tmp_path, with_alpha=True):
        """Create a complex logo for testing."""
        if with_alpha:
            # Create RGBA image with transparent background
            image = np.zeros((200, 300, 4), dtype=np.uint8)

            # Add complex logo elements
            # Main body (rectangle)
            cv2.rectangle(image, (100, 70), (200, 130), (0, 255, 0, 255), -1)

            # Logo text simulation (smaller rectangles)
            cv2.rectangle(image, (110, 80), (130, 90), (255, 255, 255, 255), -1)
            cv2.rectangle(image, (140, 80), (160, 90), (255, 255, 255, 255), -1)
            cv2.rectangle(image, (170, 80), (190, 90), (255, 255, 255, 255), -1)

            # Add transparency gradient at edges
            for y in range(200):
                for x in range(300):
                    if image[y, x, 3] > 0:  # If not transparent
                        edge_dist = min(x - 100, 200 - x, y - 70, 130 - y)
                        if edge_dist < 10:
                            alpha_val = max(0, int(255 * (edge_dist / 10.0)))
                            image[y, x, 3] = alpha_val

        else:
            # Create RGB image with white background
            image = np.ones((200, 300, 3), dtype=np.uint8) * 255

            # Add same logo elements
            cv2.rectangle(image, (100, 70), (200, 130), (0, 255, 0), -1)
            cv2.rectangle(image, (110, 80), (130, 90), (255, 255, 255), -1)
            cv2.rectangle(image, (140, 80), (160, 90), (255, 255, 255), -1)
            cv2.rectangle(image, (170, 80), (190, 90), (255, 255, 255), -1)

        suffix = "_alpha" if with_alpha else "_rgb"
        image_path = tmp_path / f"complex_logo{suffix}.png"
        cv2.imwrite(str(image_path), image)
        return image_path

    def test_full_extraction_workflow_with_alpha(self, tmp_path):
        """Test complete extraction workflow with alpha channel."""
        # Create complex logo with alpha
        logo_path = self.create_complex_logo(tmp_path, with_alpha=True)

        extractor = TemplateExtractor()

        # Load image
        success = extractor.load_image(logo_path)
        assert success is True
        assert extractor.original_alpha is not None

        # Extract ROI around the logo
        success = extractor.manual_roi_selection(x=90, y=60, width=120, height=80)
        assert success is True
        assert extractor.template_alpha is not None

        # Enhance template (mock user input)
        with patch('rich.prompt.Confirm.ask', return_value=True):
            success = extractor.enhance_template()
        assert success is True

        # Save template
        output_path = tmp_path / "extracted_logo_alpha.png"
        success = extractor.save_template(output_path)
        assert success is True

        # Verify output
        assert output_path.exists()
        saved_img = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        assert saved_img.shape[2] == 4  # Should have alpha channel

    def test_full_extraction_workflow_with_background_removal(self, tmp_path):
        """Test extraction workflow with automatic background removal."""
        # Create complex logo without alpha
        logo_path = self.create_complex_logo(tmp_path, with_alpha=False)

        extractor = TemplateExtractor()

        # Load image
        success = extractor.load_image(logo_path)
        assert success is True
        assert extractor.original_alpha is None

        # Extract ROI around the logo
        success = extractor.manual_roi_selection(x=90, y=60, width=120, height=80)
        assert success is True
        assert extractor.template_alpha is None

        # Add transparency using background removal
        success = extractor.add_transparency(method="contour")
        assert success is True
        assert extractor.template_alpha is not None

        # Save template
        output_path = tmp_path / "extracted_logo_bg_removed.png"
        success = extractor.save_template(output_path)
        assert success is True

        # Verify output has alpha
        assert output_path.exists()
        saved_img = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
        assert saved_img.shape[2] == 4  # Should have alpha channel

    def test_extraction_with_multiple_processing_steps(self, tmp_path):
        """Test extraction with multiple processing steps."""
        logo_path = self.create_complex_logo(tmp_path, with_alpha=False)

        extractor = TemplateExtractor()
        extractor.load_image(logo_path)
        extractor.manual_roi_selection(x=90, y=60, width=120, height=80)

        # Test different background removal methods
        original_template = extractor.template.copy()

        # Try contour method
        extractor.add_transparency(method="contour")
        alpha_contour = extractor.template_alpha.copy()

        # Reset and try threshold method
        extractor.template = original_template.copy()
        extractor.template_alpha = None

        extractor.add_transparency(method="threshold")
        alpha_threshold = extractor.template_alpha

        # Both methods should create alpha masks
        assert alpha_contour is not None
        assert alpha_threshold is not None

        # Results might be different
        assert alpha_contour.shape == alpha_threshold.shape