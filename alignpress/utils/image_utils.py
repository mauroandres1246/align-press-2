"""
Image processing utility functions for logo detection.

This module provides common image operations including coordinate conversions,
ROI extraction, perspective warping utilities, and PNG transparency support.
"""

from typing import Tuple, Optional, Union
import cv2
import numpy as np


def mm_to_px(x_mm: float, y_mm: float, scale: float) -> Tuple[int, int]:
    """
    Convert coordinates from millimeters to pixels.

    Args:
        x_mm: X coordinate in millimeters
        y_mm: Y coordinate in millimeters
        scale: Scale factor (pixels per millimeter)

    Returns:
        Pixel coordinates (x_px, y_px) as integers
    """
    return (int(round(x_mm * scale)), int(round(y_mm * scale)))


def px_to_mm(x_px: int, y_px: int, scale: float) -> Tuple[float, float]:
    """
    Convert coordinates from pixels to millimeters.

    Args:
        x_px: X coordinate in pixels
        y_px: Y coordinate in pixels
        scale: Scale factor (pixels per millimeter)

    Returns:
        Millimeter coordinates (x_mm, y_mm) as floats

    Raises:
        ValueError: If scale is zero or negative
    """
    if scale <= 0:
        raise ValueError(f"Scale must be positive, got {scale}")

    return (float(x_px) / scale, float(y_px) / scale)


def extract_roi(
    img: np.ndarray,
    center: Tuple[float, float],
    size: Tuple[int, int],
    border_mode: int = cv2.BORDER_CONSTANT,
    border_value: Union[int, Tuple[int, ...]] = 0
) -> np.ndarray:
    """
    Extract Region of Interest (ROI) from image with proper boundary handling.

    Args:
        img: Input image
        center: Center of ROI (x, y) in pixels
        size: ROI size (width, height) in pixels
        border_mode: OpenCV border mode for out-of-bounds areas
        border_value: Border fill value (for BORDER_CONSTANT mode)

    Returns:
        Extracted ROI image

    Raises:
        ValueError: If image is empty or size is invalid
    """
    if img.size == 0:
        raise ValueError("Input image is empty")

    if size[0] <= 0 or size[1] <= 0:
        raise ValueError(f"ROI size must be positive, got {size}")

    h, w = img.shape[:2]
    cx, cy = center
    w_roi, h_roi = size

    # Calculate ROI bounds
    x1 = int(cx - w_roi // 2)
    y1 = int(cy - h_roi // 2)
    x2 = x1 + w_roi
    y2 = y1 + h_roi

    # Handle out-of-bounds cases with padding
    pad_left = max(0, -x1)
    pad_top = max(0, -y1)
    pad_right = max(0, x2 - w)
    pad_bottom = max(0, y2 - h)

    if pad_left > 0 or pad_top > 0 or pad_right > 0 or pad_bottom > 0:
        # Need padding - use cv2.copyMakeBorder
        padded_img = cv2.copyMakeBorder(
            img, pad_top, pad_bottom, pad_left, pad_right,
            border_mode, value=border_value
        )
        # Adjust coordinates for padded image
        x1 += pad_left
        y1 += pad_top
        x2 += pad_left
        y2 += pad_top
        roi = padded_img[y1:y2, x1:x2]
    else:
        # No padding needed
        roi = img[y1:y2, x1:x2]

    return roi


def warp_perspective(
    img: np.ndarray,
    H: np.ndarray,
    size: Tuple[int, int],
    flags: int = cv2.INTER_LINEAR,
    border_mode: int = cv2.BORDER_CONSTANT,
    border_value: Union[int, Tuple[int, ...]] = 0
) -> np.ndarray:
    """
    Apply perspective transformation to image with optimized settings.

    Args:
        img: Input image
        H: 3x3 homography matrix
        size: Output size (width, height)
        flags: Interpolation method
        border_mode: Border handling mode
        border_value: Border fill value

    Returns:
        Warped image

    Raises:
        ValueError: If homography matrix is invalid
    """
    if H.shape != (3, 3):
        raise ValueError(f"Homography must be 3x3 matrix, got shape {H.shape}")

    if np.linalg.det(H) == 0:
        raise ValueError("Homography matrix is singular (determinant = 0)")

    return cv2.warpPerspective(
        img, H, size,
        flags=flags,
        borderMode=border_mode,
        borderValue=border_value
    )


def resize_image(
    img: np.ndarray,
    target_size: Optional[Tuple[int, int]] = None,
    scale_factor: Optional[float] = None,
    max_size: Optional[int] = None,
    interpolation: int = cv2.INTER_LINEAR
) -> Tuple[np.ndarray, float]:
    """
    Resize image with various sizing options.

    Args:
        img: Input image
        target_size: Exact target size (width, height)
        scale_factor: Scale factor (alternative to target_size)
        max_size: Maximum dimension (maintains aspect ratio)
        interpolation: OpenCV interpolation method

    Returns:
        Tuple of (resized_image, actual_scale_factor)

    Raises:
        ValueError: If multiple or no sizing options are provided
    """
    if img.size == 0:
        raise ValueError("Input image is empty")

    options_count = sum(x is not None for x in [target_size, scale_factor, max_size])
    if options_count != 1:
        raise ValueError("Provide exactly one sizing option")

    h, w = img.shape[:2]

    if target_size is not None:
        new_w, new_h = target_size
        actual_scale = min(new_w / w, new_h / h)

    elif scale_factor is not None:
        if scale_factor <= 0:
            raise ValueError(f"Scale factor must be positive, got {scale_factor}")
        actual_scale = scale_factor
        new_w, new_h = int(w * scale_factor), int(h * scale_factor)

    else:  # max_size is not None
        if max_size <= 0:
            raise ValueError(f"Max size must be positive, got {max_size}")
        actual_scale = min(max_size / w, max_size / h, 1.0)  # Don't upscale
        new_w, new_h = int(w * actual_scale), int(h * actual_scale)

    if new_w <= 0 or new_h <= 0:
        raise ValueError(f"Calculated size is invalid: {new_w}x{new_h}")

    resized = cv2.resize(img, (new_w, new_h), interpolation=interpolation)
    return resized, actual_scale


def convert_color_safe(
    img: np.ndarray,
    conversion_code: int
) -> np.ndarray:
    """
    Safely convert image color space with error handling.

    Args:
        img: Input image
        conversion_code: OpenCV color conversion code (e.g., cv2.COLOR_BGR2GRAY)

    Returns:
        Converted image

    Raises:
        ValueError: If conversion is not possible
    """
    if img.size == 0:
        raise ValueError("Input image is empty")

    try:
        return cv2.cvtColor(img, conversion_code)
    except cv2.error as e:
        raise ValueError(f"Color conversion failed: {e}")


def enhance_contrast(
    img: np.ndarray,
    clip_limit: float = 2.0,
    tile_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Args:
        img: Input grayscale image
        clip_limit: Clipping limit for contrast enhancement
        tile_size: Size of neighborhood for adaptive enhancement

    Returns:
        Contrast-enhanced image

    Raises:
        ValueError: If image is not grayscale
    """
    if len(img.shape) != 2:
        raise ValueError("Image must be grayscale (single channel)")

    if img.size == 0:
        raise ValueError("Input image is empty")

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    return clahe.apply(img)


def draw_detection_overlay(
    img: np.ndarray,
    center: Tuple[float, float],
    expected_center: Tuple[float, float],
    deviation_mm: float,
    angle_deg: float,
    tolerance_mm: float = 3.0,
    angle_tolerance_deg: float = 5.0
) -> np.ndarray:
    """
    Draw detection results overlay on image for debugging/visualization.

    Args:
        img: Input image (will be copied)
        center: Detected center position (x, y)
        expected_center: Expected center position (x, y)
        deviation_mm: Position deviation in millimeters
        angle_deg: Detected angle in degrees
        tolerance_mm: Position tolerance for color coding
        angle_tolerance_deg: Angle tolerance for color coding

    Returns:
        Image with overlay drawn
    """
    overlay = img.copy()

    # Color coding based on tolerances
    pos_color = (0, 255, 0) if deviation_mm <= tolerance_mm else (0, 165, 255)  # Green or Orange
    angle_color = (0, 255, 0) if abs(angle_deg) <= angle_tolerance_deg else (0, 165, 255)

    # Draw expected position (blue circle)
    cv2.circle(overlay, (int(expected_center[0]), int(expected_center[1])),
               10, (255, 0, 0), 2)

    # Draw detected position (colored circle)
    cv2.circle(overlay, (int(center[0]), int(center[1])),
               8, pos_color, -1)

    # Draw connection line
    cv2.line(overlay,
             (int(expected_center[0]), int(expected_center[1])),
             (int(center[0]), int(center[1])),
             (255, 255, 255), 2)

    # Draw angle indicator
    length = 30
    end_x = int(center[0] + length * np.cos(np.radians(angle_deg)))
    end_y = int(center[1] + length * np.sin(np.radians(angle_deg)))
    cv2.arrowedLine(overlay, (int(center[0]), int(center[1])),
                    (end_x, end_y), angle_color, 2)

    return overlay


def calculate_image_sharpness(img: np.ndarray) -> float:
    """
    Calculate image sharpness using Laplacian variance.

    Args:
        img: Input image (grayscale or color)

    Returns:
        Sharpness score (higher = sharper)

    Raises:
        ValueError: If image is empty
    """
    if img.size == 0:
        raise ValueError("Input image is empty")

    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Calculate Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return laplacian.var()


# ============================================================================
# PNG Transparency Support Functions
# ============================================================================

def load_image_with_alpha(image_path: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Load image preserving alpha channel if present.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (image, alpha_mask) where:
        - image: RGB/BGR image (3 channels)
        - alpha_mask: Alpha channel as mask (None if no alpha)
    """
    # Load with all channels
    img_with_alpha = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    if img_with_alpha is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Check if image has alpha channel
    if len(img_with_alpha.shape) == 3 and img_with_alpha.shape[2] == 4:
        # RGBA image - separate RGB and alpha
        rgb_image = img_with_alpha[:, :, :3]  # First 3 channels (BGR)
        alpha_channel = img_with_alpha[:, :, 3]  # Alpha channel

        # Create binary mask from alpha (transparent areas = 0, opaque = 255)
        alpha_mask = np.where(alpha_channel > 127, 255, 0).astype(np.uint8)

        return rgb_image, alpha_mask

    elif len(img_with_alpha.shape) == 3 and img_with_alpha.shape[2] == 3:
        # RGB image - no alpha channel
        return img_with_alpha, None

    elif len(img_with_alpha.shape) == 2:
        # Grayscale image - convert to 3 channel
        rgb_image = cv2.cvtColor(img_with_alpha, cv2.COLOR_GRAY2BGR)
        return rgb_image, None

    else:
        raise ValueError(f"Unsupported image format: {img_with_alpha.shape}")


def create_mask_from_alpha(alpha_channel: np.ndarray, threshold: int = 127) -> np.ndarray:
    """
    Create binary mask from alpha channel.

    Args:
        alpha_channel: Alpha channel (0-255)
        threshold: Threshold for transparency (default: 127)

    Returns:
        Binary mask (0 or 255)
    """
    return np.where(alpha_channel > threshold, 255, 0).astype(np.uint8)


def remove_background_auto(image: np.ndarray, method: str = "contour") -> Tuple[np.ndarray, np.ndarray]:
    """
    Automatically remove background from logo image.

    Args:
        image: Input BGR image
        method: Method to use ("contour", "grabcut", "threshold")

    Returns:
        Tuple of (processed_image, mask) where:
        - processed_image: Image with background removed (transparent PNG)
        - mask: Binary mask of foreground
    """
    if method == "contour":
        return _remove_background_contour(image)
    elif method == "grabcut":
        return _remove_background_grabcut(image)
    elif method == "threshold":
        return _remove_background_threshold(image)
    else:
        raise ValueError(f"Unknown background removal method: {method}")


def _remove_background_contour(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Remove background using contour detection."""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply threshold to get binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        # If no contours found, return original image
        mask = np.ones(gray.shape, dtype=np.uint8) * 255
        return image, mask

    # Find largest contour (assuming it's the logo)
    largest_contour = max(contours, key=cv2.contourArea)

    # Create mask from contour
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [largest_contour], 255)

    # Apply morphological operations to clean up mask
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Create result image with alpha channel
    result = np.dstack([image, mask])

    return result, mask


def _remove_background_threshold(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Remove background using adaptive thresholding."""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Use adaptive threshold to separate foreground/background
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Invert if background is darker than foreground
    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)

    # Clean up with morphological operations
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Create result with alpha
    result = np.dstack([image, mask])

    return result, mask


def _remove_background_grabcut(image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Remove background using GrabCut algorithm."""
    height, width = image.shape[:2]

    # Create rectangle around image center (assuming logo is centered)
    margin = min(width, height) // 8
    rect = (margin, margin, width - 2*margin, height - 2*margin)

    # Initialize mask
    mask = np.zeros((height, width), np.uint8)

    # GrabCut background and foreground models
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Run GrabCut
    cv2.grabCut(image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)

    # Create final mask
    final_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)

    # Create result with alpha
    result = np.dstack([image, final_mask])

    return result, final_mask


def enhance_logo_contrast(image: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Enhance contrast specifically for logo detection.

    Args:
        image: Input image (grayscale or BGR)
        mask: Optional mask to limit enhancement to specific regions

    Returns:
        Enhanced image (same format as input)
    """
    if len(image.shape) not in [2, 3]:
        raise ValueError("Image must be grayscale or color")

    # Apply CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    if len(image.shape) == 2:
        # Grayscale image
        if mask is not None:
            # Apply enhancement only to masked regions
            enhanced = image.copy()
            mask_indices = mask > 0
            if np.any(mask_indices):
                enhanced[mask_indices] = clahe.apply(image[mask_indices].reshape(-1)).reshape(-1)
        else:
            # Apply to entire image
            enhanced = clahe.apply(image)
        return enhanced

    else:
        # Color image - convert to LAB color space for better contrast enhancement
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        if mask is not None:
            # Apply enhancement only to masked regions
            l_enhanced = l.copy()
            mask_indices = mask > 0
            if np.any(mask_indices):
                l_enhanced[mask_indices] = clahe.apply(l[mask_indices].reshape(-1)).reshape(-1)
        else:
            # Apply to entire image
            l_enhanced = clahe.apply(l)

        # Merge channels and convert back
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        return enhanced_bgr


def save_image_with_alpha(image: np.ndarray, output_path: str, alpha_mask: Optional[np.ndarray] = None) -> bool:
    """
    Save image with alpha channel as PNG.

    Args:
        image: BGR image (3 channels)
        output_path: Output file path (should be .png)
        alpha_mask: Optional alpha mask (0-255)

    Returns:
        True if saved successfully
    """
    try:
        if alpha_mask is not None:
            # Combine BGR image with alpha mask
            rgba_image = np.dstack([image, alpha_mask])
            success = cv2.imwrite(output_path, rgba_image)
        else:
            # Save as regular BGR image
            success = cv2.imwrite(output_path, image)

        return success
    except Exception:
        return False


def has_transparency(image_path: str) -> bool:
    """
    Check if image file has transparency (alpha channel).

    Args:
        image_path: Path to image file

    Returns:
        True if image has alpha channel
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return False

        # Check if 4 channels (RGBA)
        return len(img.shape) == 3 and img.shape[2] == 4
    except Exception:
        return False


def get_image_info(image_path: str) -> dict:
    """
    Get comprehensive information about an image file.

    Args:
        image_path: Path to image file

    Returns:
        Dictionary with image information
    """
    try:
        # Load with all channels preserved
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return {"error": "Could not load image"}

        info = {
            "path": image_path,
            "shape": img.shape,
            "dtype": str(img.dtype),
            "has_alpha": len(img.shape) == 3 and img.shape[2] == 4,
            "is_grayscale": len(img.shape) == 2,
            "is_color": len(img.shape) == 3 and img.shape[2] >= 3,
        }

        # Additional info for color images
        if info["is_color"]:
            info["channels"] = img.shape[2]
            if info["has_alpha"]:
                alpha_channel = img[:, :, 3]
                info["alpha_stats"] = {
                    "min": int(alpha_channel.min()),
                    "max": int(alpha_channel.max()),
                    "mean": float(alpha_channel.mean()),
                    "has_transparency": alpha_channel.min() < 255
                }

        return info

    except Exception as e:
        return {"error": str(e)}