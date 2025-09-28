"""
Unit tests for image utility functions.
"""

import pytest
import numpy as np
import cv2

from alignpress.utils.image_utils import (
    mm_to_px, px_to_mm, extract_roi, warp_perspective,
    resize_image, convert_color_safe, enhance_contrast,
    calculate_image_sharpness
)


class TestCoordinateConversion:
    """Test coordinate conversion functions."""

    def test_mm_to_px_basic(self):
        """Test basic millimeter to pixel conversion."""
        # Scale: 2 pixels per mm
        result = mm_to_px(10.0, 5.0, 2.0)
        assert result == (20, 10)

        # Scale: 0.5 pixels per mm
        result = mm_to_px(10.0, 20.0, 0.5)
        assert result == (5, 10)

    def test_mm_to_px_rounding(self):
        """Test rounding behavior."""
        result = mm_to_px(10.3, 5.7, 1.0)
        assert result == (10, 6)  # Should round to nearest integer

    def test_px_to_mm_basic(self):
        """Test basic pixel to millimeter conversion."""
        # Scale: 2 pixels per mm
        result = px_to_mm(20, 10, 2.0)
        assert abs(result[0] - 10.0) < 1e-6
        assert abs(result[1] - 5.0) < 1e-6

    def test_px_to_mm_invalid_scale(self):
        """Test error handling for invalid scale."""
        with pytest.raises(ValueError):
            px_to_mm(10, 10, 0.0)

        with pytest.raises(ValueError):
            px_to_mm(10, 10, -1.0)

    def test_coordinate_conversion_roundtrip(self):
        """Test roundtrip conversion accuracy."""
        original_mm = (15.3, 27.8)
        scale = 1.5

        # Convert to pixels and back
        px = mm_to_px(original_mm[0], original_mm[1], scale)
        back_to_mm = px_to_mm(px[0], px[1], scale)

        # Should be close to original (within rounding error)
        assert abs(back_to_mm[0] - original_mm[0]) < 1.0  # Within 1mm due to rounding
        assert abs(back_to_mm[1] - original_mm[1]) < 1.0


class TestExtractROI:
    """Test ROI extraction function."""

    def test_extract_roi_basic(self):
        """Test basic ROI extraction."""
        # Create test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[40:60, 40:60] = [255, 255, 255]  # White square in center

        # Extract ROI around center
        roi = extract_roi(img, (50, 50), (20, 20))

        assert roi.shape == (20, 20, 3)
        # Center should be white
        assert np.all(roi[10, 10] == [255, 255, 255])

    def test_extract_roi_out_of_bounds(self):
        """Test ROI extraction with out-of-bounds coordinates."""
        img = np.zeros((50, 50, 3), dtype=np.uint8)

        # ROI extending outside image boundaries
        roi = extract_roi(img, (10, 10), (30, 30))

        assert roi.shape == (30, 30, 3)
        # Should be padded with zeros (default border value)

    def test_extract_roi_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            extract_roi(np.array([]), (10, 10), (20, 20))

        with pytest.raises(ValueError):
            img = np.zeros((50, 50, 3), dtype=np.uint8)
            extract_roi(img, (10, 10), (0, 20))  # Invalid size

    def test_extract_roi_border_modes(self):
        """Test different border modes."""
        img = np.ones((20, 20, 3), dtype=np.uint8) * 100

        # Test constant border
        roi_const = extract_roi(img, (5, 5), (20, 20), cv2.BORDER_CONSTANT, 255)
        assert roi_const.shape == (20, 20, 3)

        # Test replicate border
        roi_repl = extract_roi(img, (5, 5), (20, 20), cv2.BORDER_REPLICATE)
        assert roi_repl.shape == (20, 20, 3)


class TestWarpPerspective:
    """Test perspective warping function."""

    def test_warp_perspective_identity(self):
        """Test warping with identity matrix."""
        img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        H = np.eye(3, dtype=np.float32)

        warped = warp_perspective(img, H, (50, 50))

        # Should be identical to original
        assert np.array_equal(warped, img)

    def test_warp_perspective_invalid_homography(self):
        """Test error handling for invalid homography."""
        img = np.zeros((50, 50, 3), dtype=np.uint8)

        # Wrong shape
        with pytest.raises(ValueError):
            H = np.eye(2, dtype=np.float32)
            warp_perspective(img, H, (50, 50))

        # Singular matrix
        with pytest.raises(ValueError):
            H = np.zeros((3, 3), dtype=np.float32)
            warp_perspective(img, H, (50, 50))


class TestResizeImage:
    """Test image resizing function."""

    def test_resize_with_target_size(self):
        """Test resizing with target size."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        resized, scale = resize_image(img, target_size=(100, 50))

        assert resized.shape == (50, 100, 3)
        assert scale == 0.5  # Limiting factor is height: 50/100 = 0.5

    def test_resize_with_scale_factor(self):
        """Test resizing with scale factor."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        resized, scale = resize_image(img, scale_factor=0.5)

        assert resized.shape == (50, 100, 3)
        assert scale == 0.5

    def test_resize_with_max_size(self):
        """Test resizing with maximum size constraint."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        resized, scale = resize_image(img, max_size=150)

        # Should scale down so largest dimension is 150
        assert max(resized.shape[:2]) == 150
        assert scale == 0.75  # 150/200 = 0.75

    def test_resize_invalid_options(self):
        """Test error handling for invalid options."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)

        # No options provided
        with pytest.raises(ValueError):
            resize_image(img)

        # Multiple options provided
        with pytest.raises(ValueError):
            resize_image(img, target_size=(100, 50), scale_factor=0.5)

    def test_resize_invalid_values(self):
        """Test error handling for invalid values."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)

        with pytest.raises(ValueError):
            resize_image(img, scale_factor=-0.5)

        with pytest.raises(ValueError):
            resize_image(img, max_size=-100)


class TestConvertColorSafe:
    """Test safe color conversion function."""

    def test_convert_color_basic(self):
        """Test basic color conversion."""
        # Create BGR image
        bgr = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        # Convert to grayscale
        gray = convert_color_safe(bgr, cv2.COLOR_BGR2GRAY)

        assert len(gray.shape) == 2
        assert gray.shape == (50, 50)

    def test_convert_color_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            convert_color_safe(np.array([]), cv2.COLOR_BGR2GRAY)

    def test_convert_color_invalid_conversion(self):
        """Test error handling for invalid conversion."""
        # Try to convert grayscale to BGR (invalid)
        gray = np.zeros((50, 50), dtype=np.uint8)

        with pytest.raises(ValueError):
            convert_color_safe(gray, cv2.COLOR_BGR2GRAY)


class TestEnhanceContrast:
    """Test contrast enhancement function."""

    def test_enhance_contrast_basic(self):
        """Test basic contrast enhancement."""
        # Create low-contrast image
        img = np.ones((100, 100), dtype=np.uint8) * 128
        img[25:75, 25:75] = 100  # Slightly darker square

        enhanced = enhance_contrast(img)

        assert enhanced.shape == img.shape
        assert enhanced.dtype == img.dtype

    def test_enhance_contrast_invalid_input(self):
        """Test error handling for invalid input."""
        # Color image (should be grayscale)
        with pytest.raises(ValueError):
            color_img = np.zeros((50, 50, 3), dtype=np.uint8)
            enhance_contrast(color_img)

        # Empty image
        with pytest.raises(ValueError):
            enhance_contrast(np.array([]))


class TestCalculateImageSharpness:
    """Test image sharpness calculation."""

    def test_calculate_sharpness_basic(self):
        """Test basic sharpness calculation."""
        # Create sharp image with edges
        img = np.zeros((100, 100), dtype=np.uint8)
        img[25:75, 25:75] = 255  # White square on black background

        sharpness = calculate_image_sharpness(img)

        assert isinstance(sharpness, float)
        assert sharpness > 0

    def test_calculate_sharpness_color_image(self):
        """Test sharpness calculation with color image."""
        # Should automatically convert to grayscale
        img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)

        sharpness = calculate_image_sharpness(img)

        assert isinstance(sharpness, float)
        assert sharpness >= 0

    def test_calculate_sharpness_uniform_image(self):
        """Test sharpness of uniform image (should be low)."""
        # Uniform gray image (no edges)
        img = np.ones((100, 100), dtype=np.uint8) * 128

        sharpness = calculate_image_sharpness(img)

        assert sharpness == 0.0  # No variation = zero sharpness

    def test_calculate_sharpness_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            calculate_image_sharpness(np.array([]))