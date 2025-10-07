"""Pytest configuration and fixtures for test helpers."""

import pytest
import cv2
import numpy as np
from pathlib import Path

from .test_helpers import create_feature_rich_template, create_plane_with_logo


FIXTURES_DIR = Path(__file__).parent
TEMPLATES_DIR = FIXTURES_DIR / "templates"
IMAGES_DIR = FIXTURES_DIR / "images"


@pytest.fixture(scope="session", autouse=True)
def create_feature_rich_templates():
    """Create feature-rich templates for testing (session scope)."""
    # Create directories
    TEMPLATES_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    # Create templates with different patterns
    templates = {
        "mock_template_a.png": create_feature_rich_template((80, 60), "mixed"),
        "mock_template_b.png": create_feature_rich_template((70, 70), "checkerboard"),
        "mock_template_c.png": create_feature_rich_template((60, 50), "circles"),
    }

    for filename, template in templates.items():
        output_path = TEMPLATES_DIR / filename
        cv2.imwrite(str(output_path), template)

    # Create test plane images with logos
    # Perfect alignment
    template_a = templates["mock_template_a.png"]
    plane_perfect = create_plane_with_logo(
        plane_size=(600, 400),  # 300mm x 200mm at 0.5mm/px
        logo_template=template_a,
        position_px=(300, 200),  # Center (150mm, 100mm)
        angle_deg=0.0,
        scale=1.0
    )
    cv2.imwrite(str(IMAGES_DIR / "mock_plane_perfect.jpg"), plane_perfect)

    # With offset (5mm = 10px at 0.5mm/px)
    plane_offset = create_plane_with_logo(
        plane_size=(600, 400),
        logo_template=template_a,
        position_px=(310, 210),  # Offset by 10px each direction
        angle_deg=3.0,  # Small rotation
        scale=1.0
    )
    cv2.imwrite(str(IMAGES_DIR / "mock_plane_offset.jpg"), plane_offset)

    # With rotation
    plane_rotated = create_plane_with_logo(
        plane_size=(600, 400),
        logo_template=template_a,
        position_px=(300, 200),
        angle_deg=10.0,  # 10 degree rotation
        scale=1.0
    )
    cv2.imwrite(str(IMAGES_DIR / "mock_plane_rotated.jpg"), plane_rotated)

    yield

    # No cleanup - keep files for inspection


@pytest.fixture
def feature_rich_template():
    """Provide a feature-rich template for individual tests."""
    return create_feature_rich_template((80, 60), "mixed")


@pytest.fixture
def temp_template_file(tmp_path):
    """Create a temporary template file."""
    template = create_feature_rich_template((50, 50), "checkerboard")
    template_path = tmp_path / "temp_template.png"
    cv2.imwrite(str(template_path), template)
    return template_path
