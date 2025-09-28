#!/usr/bin/env python3
"""
Generate synthetic template images for testing.

This script creates simple template images with distinctive features
that can be detected by ORB feature detector.
"""

import cv2
import numpy as np
from pathlib import Path


def create_logo_template(
    name: str,
    size: tuple = (100, 80),
    shape: str = "circle",
    color: tuple = (0, 0, 0),
    bg_color: tuple = (255, 255, 255)
) -> np.ndarray:
    """
    Create a synthetic logo template with distinctive features.

    Args:
        name: Logo name for text overlay
        size: Template size (width, height)
        shape: Shape type ("circle", "square", "triangle")
        color: Foreground color (B, G, R)
        bg_color: Background color (B, G, R)

    Returns:
        Template image
    """
    width, height = size
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    center_x, center_y = width // 2, height // 2

    if shape == "circle":
        radius = min(width, height) // 4
        cv2.circle(img, (center_x, center_y), radius, color, -1)
        # Add some texture with smaller circles
        for i in range(3):
            offset_x = (i - 1) * radius // 2
            cv2.circle(img, (center_x + offset_x, center_y), radius // 4, bg_color, -1)

    elif shape == "square":
        size_sq = min(width, height) // 3
        top_left = (center_x - size_sq // 2, center_y - size_sq // 2)
        bottom_right = (center_x + size_sq // 2, center_y + size_sq // 2)
        cv2.rectangle(img, top_left, bottom_right, color, -1)
        # Add internal pattern
        cv2.rectangle(img,
                     (top_left[0] + size_sq // 4, top_left[1] + size_sq // 4),
                     (bottom_right[0] - size_sq // 4, bottom_right[1] - size_sq // 4),
                     bg_color, 2)

    elif shape == "triangle":
        pts = np.array([
            [center_x, center_y - height // 3],
            [center_x - width // 3, center_y + height // 4],
            [center_x + width // 3, center_y + height // 4]
        ], np.int32)
        cv2.fillPoly(img, [pts], color)
        # Add internal lines
        cv2.line(img, tuple(pts[0]), tuple(pts[1]), bg_color, 2)
        cv2.line(img, tuple(pts[1]), tuple(pts[2]), bg_color, 2)
        cv2.line(img, tuple(pts[2]), tuple(pts[0]), bg_color, 2)

    # Add text label
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    text_color = (128, 128, 128)  # Gray text

    # Calculate text size and position
    (text_width, text_height), _ = cv2.getTextSize(name, font, font_scale, 1)
    text_x = (width - text_width) // 2
    text_y = height - 10

    cv2.putText(img, name, (text_x, text_y), font, font_scale, text_color, 1)

    # Add some noise/texture for better feature detection
    noise = np.random.randint(-10, 10, (height, width, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


def main():
    """Create test templates."""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    # Create templates for different logos
    templates = [
        ("logo_pecho", (100, 80), "circle", (0, 100, 200)),     # Orange circle
        ("logo_manga_izq", (60, 50), "square", (200, 0, 0)),   # Blue square
        ("logo_manga_der", (60, 50), "triangle", (0, 200, 0)), # Green triangle
    ]

    for name, size, shape, color in templates:
        print(f"Creating template: {name}")

        template = create_logo_template(name, size, shape, color)

        # Save template
        output_path = templates_dir / f"{name}.png"
        cv2.imwrite(str(output_path), template)

        print(f"  Saved: {output_path}")

        # Also create a rotated version for testing
        rotated_name = f"{name}_rotated"
        M = cv2.getRotationMatrix2D((size[0]//2, size[1]//2), 15, 1.0)
        rotated = cv2.warpAffine(template, M, size)

        rotated_path = templates_dir / f"{rotated_name}.png"
        cv2.imwrite(str(rotated_path), rotated)
        print(f"  Saved rotated: {rotated_path}")

    print(f"\nCreated {len(templates) * 2} template images in {templates_dir}")


if __name__ == "__main__":
    main()