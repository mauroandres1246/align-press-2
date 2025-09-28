"""
Image processing utility functions for logo detection.

This module provides common image operations including coordinate conversions,
ROI extraction, and perspective warping utilities.
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