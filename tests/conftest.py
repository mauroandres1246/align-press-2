"""
Pytest configuration and shared fixtures.
"""

import pytest
import tempfile
import numpy as np
from pathlib import Path
from typing import Generator

from alignpress.core.schemas import (
    PlaneConfigSchema, LogoSpecSchema, ROIConfigSchema,
    DetectorConfigSchema, CalibrationDataSchema
)


@pytest.fixture
def temp_template_file() -> Generator[Path, None, None]:
    """Create a temporary template file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        f.write(b'fake png content')
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_plane_config() -> PlaneConfigSchema:
    """Create a sample plane configuration for testing."""
    return PlaneConfigSchema(
        width_mm=300.0,
        height_mm=200.0,
        mm_per_px=0.5
    )


@pytest.fixture
def sample_roi_config() -> ROIConfigSchema:
    """Create a sample ROI configuration for testing."""
    return ROIConfigSchema(
        width_mm=50.0,
        height_mm=40.0,
        margin_factor=1.2
    )


@pytest.fixture
def sample_logo_spec(temp_template_file: Path, sample_roi_config: ROIConfigSchema) -> LogoSpecSchema:
    """Create a sample logo specification for testing."""
    return LogoSpecSchema(
        name="test_logo",
        template_path=temp_template_file,
        position_mm=(150.0, 100.0),
        roi=sample_roi_config,
        angle_deg=0.0
    )


@pytest.fixture
def sample_detector_config(
    sample_plane_config: PlaneConfigSchema,
    sample_logo_spec: LogoSpecSchema
) -> DetectorConfigSchema:
    """Create a sample detector configuration for testing."""
    return DetectorConfigSchema(
        plane=sample_plane_config,
        logos=[sample_logo_spec]
    )


@pytest.fixture
def sample_calibration_data() -> CalibrationDataSchema:
    """Create sample calibration data for testing."""
    return CalibrationDataSchema(
        camera_id=0,
        homography=[
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ],
        mm_per_px=0.5,
        pattern_info={
            "type": "chessboard",
            "size": [9, 6],
            "square_size_mm": 25.0
        },
        quality_metrics={
            "reproj_error_px": 0.8,
            "corners_detected": 54,
            "corners_expected": 54
        }
    )


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a sample test image."""
    # Create a simple test image with some features
    img = np.zeros((200, 300, 3), dtype=np.uint8)

    # Add some patterns for feature detection
    # White rectangle in center
    img[75:125, 125:175] = [255, 255, 255]

    # Add some noise for texture
    noise = np.random.randint(-10, 10, img.shape, dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img


@pytest.fixture
def sample_template() -> np.ndarray:
    """Create a sample template image."""
    # Create a simple template with distinctive features
    template = np.zeros((80, 100, 3), dtype=np.uint8)

    # Add a white circle
    center = (50, 40)
    radius = 20
    import cv2
    cv2.circle(template, center, radius, (255, 255, 255), -1)

    # Add some internal structure
    cv2.circle(template, center, radius // 2, (128, 128, 128), -1)

    return template


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Skip tests that require OpenCV if not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle missing dependencies."""
    try:
        import cv2
    except ImportError:
        skip_opencv = pytest.mark.skip(reason="OpenCV not available")
        for item in items:
            if "test_image_utils" in str(item.fspath) or "detector" in str(item.fspath):
                item.add_marker(skip_opencv)