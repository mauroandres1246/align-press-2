"""Helper functions for creating feature-rich test templates and images."""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


def create_feature_rich_template(
    size: Tuple[int, int] = (100, 100),
    pattern: str = "checkerboard",
    output_path: Optional[Path] = None
) -> np.ndarray:
    """
    Create a template image with many features for ORB/AKAZE detection.

    Args:
        size: Template size (width, height)
        pattern: Pattern type - "checkerboard", "circles", "grid", or "mixed"
        output_path: Optional path to save the template

    Returns:
        Template image as numpy array (BGR)
    """
    width, height = size
    template = np.ones((height, width, 3), dtype=np.uint8) * 255

    if pattern == "checkerboard":
        # Create checkerboard pattern (many corners)
        square_size = min(width, height) // 8
        for i in range(0, height, square_size):
            for j in range(0, width, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    template[i:i+square_size, j:j+square_size] = [0, 0, 0]

    elif pattern == "circles":
        # Draw multiple circles (many edge features)
        center = (width // 2, height // 2)
        for radius in range(10, min(width, height) // 2, 10):
            cv2.circle(template, center, radius, (0, 0, 0), 2)

    elif pattern == "grid":
        # Draw grid lines (many intersections)
        grid_spacing = min(width, height) // 10
        for i in range(0, height, grid_spacing):
            cv2.line(template, (0, i), (width, i), (0, 0, 0), 2)
        for j in range(0, width, grid_spacing):
            cv2.line(template, (j, 0), (j, height), (0, 0, 0), 2)

    elif pattern == "mixed":
        # Combination of patterns for maximum features (>100)
        template[:] = [240, 240, 240]  # Light gray background

        # Dense checkerboard (many corners)
        square_size = max(4, min(width, height) // 16)
        for i in range(0, height, square_size):
            for j in range(0, width, square_size):
                if (i // square_size + j // square_size) % 2 == 0:
                    template[i:min(i+square_size, height), j:min(j+square_size, width)] = [0, 0, 0]

        # Add random dots for extra features
        np.random.seed(42)  # Reproducible
        for _ in range(30):
            x = np.random.randint(5, width - 5)
            y = np.random.randint(5, height - 5)
            cv2.circle(template, (x, y), 2, (100, 100, 100), -1)

        # Add some lines
        for i in range(4):
            x1 = np.random.randint(0, width)
            y1 = np.random.randint(0, height)
            x2 = np.random.randint(0, width)
            y2 = np.random.randint(0, height)
            cv2.line(template, (x1, y1), (x2, y2), (80, 80, 80), 1)

        # Add border frame
        cv2.rectangle(template, (2, 2), (width-3, height-3), (0, 0, 0), 2)

    if output_path:
        cv2.imwrite(str(output_path), template)

    return template


def create_plane_with_logo(
    plane_size: Tuple[int, int],
    logo_template: np.ndarray,
    position_px: Tuple[int, int],
    angle_deg: float = 0.0,
    scale: float = 1.0,
    background_color: Tuple[int, int, int] = (240, 240, 240)
) -> np.ndarray:
    """
    Create a plane image with a logo placed at a specific position.

    Args:
        plane_size: Size of the plane (width, height)
        logo_template: Logo template image
        position_px: Logo center position (x, y) in pixels
        angle_deg: Logo rotation angle in degrees
        scale: Logo scale factor
        background_color: Background color (BGR)

    Returns:
        Plane image with logo placed
    """
    width, height = plane_size
    plane = np.ones((height, width, 3), dtype=np.uint8)
    plane[:] = background_color

    # Get logo dimensions
    logo_h, logo_w = logo_template.shape[:2]

    # Apply transformations to logo
    if scale != 1.0:
        new_w = int(logo_w * scale)
        new_h = int(logo_h * scale)
        logo = cv2.resize(logo_template, (new_w, new_h))
    else:
        logo = logo_template.copy()

    if angle_deg != 0.0:
        center = (logo.shape[1] // 2, logo.shape[0] // 2)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        logo = cv2.warpAffine(logo, M, (logo.shape[1], logo.shape[0]),
                              borderValue=(255, 255, 255))

    # Place logo on plane
    logo_h, logo_w = logo.shape[:2]
    x, y = position_px

    # Calculate placement boundaries
    x1 = max(0, x - logo_w // 2)
    y1 = max(0, y - logo_h // 2)
    x2 = min(width, x + logo_w // 2)
    y2 = min(height, y + logo_h // 2)

    # Calculate logo crop if needed
    logo_x1 = max(0, logo_w // 2 - x)
    logo_y1 = max(0, logo_h // 2 - y)
    logo_x2 = logo_w - max(0, (x + logo_w // 2) - width)
    logo_y2 = logo_h - max(0, (y + logo_h // 2) - height)

    # Place logo (only non-white pixels)
    logo_crop = logo[logo_y1:logo_y2, logo_x1:logo_x2]
    mask = cv2.cvtColor(logo_crop, cv2.COLOR_BGR2GRAY) < 250

    plane_region = plane[y1:y2, x1:x2]
    plane_region[mask] = logo_crop[mask]

    return plane


def count_orb_features(image: np.ndarray, max_features: int = 500) -> int:
    """
    Count ORB features in an image.

    Args:
        image: Input image
        max_features: Maximum features to detect

    Returns:
        Number of features detected
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    orb = cv2.ORB_create(nfeatures=max_features)
    keypoints = orb.detect(gray, None)
    return len(keypoints)


def verify_template_quality(
    template: np.ndarray,
    min_features: int = 50,
    max_features: int = 500
) -> dict:
    """
    Verify that a template has sufficient quality for feature detection.

    Args:
        template: Template image
        min_features: Minimum required features
        max_features: Maximum features to detect

    Returns:
        Dictionary with quality metrics
    """
    orb_count = count_orb_features(template, max_features)

    # Check contrast
    gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
    contrast = gray.std()

    return {
        "orb_features": orb_count,
        "min_features": min_features,
        "has_enough_features": orb_count >= min_features,
        "contrast": float(contrast),
        "has_good_contrast": contrast > 20.0
    }
