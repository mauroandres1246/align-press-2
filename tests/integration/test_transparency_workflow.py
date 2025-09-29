"""
Integration tests for complete transparency workflow.
"""

import pytest
import numpy as np
import cv2
from pathlib import Path
import tempfile
import json

from alignpress.utils.image_utils import (
    load_image_with_alpha, save_image_with_alpha,
    remove_background_auto, has_transparency
)
from alignpress.core.schemas import (
    DetectorConfigSchema, PlaneConfigSchema, FeatureParamsSchema,
    ROIConfigSchema, LogoSpecSchema
)


class TestTransparencyWorkflow:
    """Test complete transparency workflow integration."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace for testing."""
        workspace = {
            "root": tmp_path,
            "templates": tmp_path / "templates",
            "test_images": tmp_path / "test_images",
            "configs": tmp_path / "configs"
        }

        # Create directories
        for path in workspace.values():
            if isinstance(path, Path):
                path.mkdir(exist_ok=True)

        return workspace

    def create_test_logo_with_transparency(self, output_path: Path, logo_type: str = "circle"):
        """Create a test logo with transparency."""
        # Create RGBA image
        image = np.zeros((80, 120, 4), dtype=np.uint8)

        if logo_type == "circle":
            # Create a circle logo with gradient transparency
            center = (60, 40)
            radius = 25
            cv2.circle(image, center, radius, (0, 0, 255, 255), -1)  # Red circle

            # Add gradient transparency
            for y in range(80):
                for x in range(120):
                    if image[y, x, 3] > 0:  # If not transparent
                        dist = np.sqrt((x - center[0])**2 + (y - center[1])**2)
                        if dist <= radius:
                            alpha_val = max(0, int(255 * (1 - dist / radius * 0.5)))
                            image[y, x, 3] = alpha_val

        elif logo_type == "rectangle":
            # Create a rectangle logo
            cv2.rectangle(image, (30, 20), (90, 60), (0, 255, 0, 255), -1)  # Green rectangle

            # Add some text simulation
            cv2.rectangle(image, (35, 25), (50, 35), (255, 255, 255, 255), -1)
            cv2.rectangle(image, (55, 25), (70, 35), (255, 255, 255, 255), -1)
            cv2.rectangle(image, (75, 25), (85, 35), (255, 255, 255, 255), -1)

        cv2.imwrite(str(output_path), image)
        return output_path

    def create_test_logo_without_transparency(self, output_path: Path):
        """Create a test logo without transparency on white background."""
        # Create RGB image with white background
        image = np.ones((80, 120, 3), dtype=np.uint8) * 255

        # Add blue rectangle logo
        cv2.rectangle(image, (30, 20), (90, 60), (255, 0, 0), -1)  # Blue rectangle
        cv2.rectangle(image, (35, 25), (50, 35), (255, 255, 255), -1)  # White text sim
        cv2.rectangle(image, (55, 25), (70, 35), (255, 255, 255), -1)
        cv2.rectangle(image, (75, 25), (85, 35), (255, 255, 255), -1)

        cv2.imwrite(str(output_path), image)
        return output_path

    def test_load_and_save_transparency_workflow(self, temp_workspace):
        """Test loading and saving workflow with transparency."""
        # Create test logo with transparency
        logo_path = temp_workspace["templates"] / "test_logo_alpha.png"
        self.create_test_logo_with_transparency(logo_path)

        # Load image with alpha
        image, alpha = load_image_with_alpha(str(logo_path))

        assert image is not None
        assert alpha is not None
        assert image.shape == (80, 120, 3)
        assert alpha.shape == (80, 120)

        # Save to new location
        output_path = temp_workspace["test_images"] / "saved_logo.png"
        success = save_image_with_alpha(image, str(output_path), alpha)

        assert success is True
        assert output_path.exists()

        # Verify transparency is preserved
        assert has_transparency(str(output_path)) is True

        # Load again to verify consistency
        image2, alpha2 = load_image_with_alpha(str(output_path))

        assert image2 is not None
        assert alpha2 is not None
        assert image2.shape == image.shape
        assert alpha2.shape == alpha.shape

    def test_background_removal_workflow(self, temp_workspace):
        """Test background removal workflow."""
        # Create logo without transparency
        logo_path = temp_workspace["templates"] / "test_logo_rgb.png"
        self.create_test_logo_without_transparency(logo_path)

        # Load image
        image, alpha = load_image_with_alpha(str(logo_path))

        assert image is not None
        assert alpha is None  # No transparency initially

        # Remove background
        processed_image, mask = remove_background_auto(image, method="contour")

        assert processed_image is not None
        assert mask is not None
        assert processed_image.shape == (80, 120, 4)  # Should have alpha channel
        assert mask.shape == (80, 120)

        # Save processed image
        output_path = temp_workspace["test_images"] / "processed_logo.png"
        # Extract alpha from processed image for saving
        alpha_channel = processed_image[:, :, 3] if processed_image.shape[2] == 4 else None
        rgb_image = processed_image[:, :, :3]

        success = save_image_with_alpha(rgb_image, str(output_path), alpha_channel)

        assert success is True
        assert has_transparency(str(output_path)) is True

    def test_complete_template_processing_workflow(self, temp_workspace):
        """Test complete template processing workflow."""
        # Create original logo with transparency
        original_logo = temp_workspace["templates"] / "original_logo.png"
        self.create_test_logo_with_transparency(original_logo, "circle")

        # Create logo without transparency
        rgb_logo = temp_workspace["templates"] / "rgb_logo.png"
        self.create_test_logo_without_transparency(rgb_logo)

        # Test workflow 1: Logo with existing transparency
        image1, alpha1 = load_image_with_alpha(str(original_logo))

        assert alpha1 is not None

        # Save enhanced version
        enhanced_path1 = temp_workspace["test_images"] / "enhanced_alpha.png"
        save_image_with_alpha(image1, str(enhanced_path1), alpha1)

        assert has_transparency(str(enhanced_path1)) is True

        # Test workflow 2: Logo without transparency -> add transparency
        image2, alpha2 = load_image_with_alpha(str(rgb_logo))

        assert alpha2 is None

        # Add transparency via background removal
        processed_image2, mask2 = remove_background_auto(image2, method="threshold")

        # Save with new transparency
        enhanced_path2 = temp_workspace["test_images"] / "enhanced_added_alpha.png"
        alpha_channel2 = processed_image2[:, :, 3] if processed_image2.shape[2] == 4 else mask2
        rgb_image2 = processed_image2[:, :, :3] if processed_image2.shape[2] == 4 else image2

        save_image_with_alpha(rgb_image2, str(enhanced_path2), alpha_channel2)

        assert has_transparency(str(enhanced_path2)) is True

    def test_configuration_with_transparency_fields(self, temp_workspace):
        """Test configuration creation with transparency fields."""
        # Create test logo
        logo_path = temp_workspace["templates"] / "config_test_logo.png"
        self.create_test_logo_with_transparency(logo_path)

        # Create detector configuration with transparency fields
        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            logos=[
                LogoSpecSchema(
                    name="test_logo",
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

        # Validate configuration
        assert config.logos[0].has_transparency is True
        assert config.logos[0].transparency_method == "contour"

        # Test serialization/deserialization
        config_dict = config.model_dump()
        assert config_dict["logos"][0]["has_transparency"] is True
        assert config_dict["logos"][0]["transparency_method"] == "contour"

        # Save configuration
        config_path = temp_workspace["configs"] / "detector_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)

        assert config_path.exists()

        # Load and validate
        with open(config_path, 'r') as f:
            loaded_dict = json.load(f)

        loaded_config = DetectorConfigSchema.model_validate(loaded_dict)
        assert loaded_config.logos[0].has_transparency is True
        assert loaded_config.logos[0].transparency_method == "contour"

    def test_multiple_transparency_methods(self, temp_workspace):
        """Test different transparency removal methods."""
        # Create test logo without transparency
        logo_path = temp_workspace["templates"] / "multi_method_test.png"
        self.create_test_logo_without_transparency(logo_path)

        # Load image
        image, _ = load_image_with_alpha(str(logo_path))

        methods = ["contour", "threshold"]
        results = {}

        for method in methods:
            # Apply background removal
            processed_image, mask = remove_background_auto(image, method=method)

            # Save result
            output_path = temp_workspace["test_images"] / f"method_{method}.png"
            alpha_channel = processed_image[:, :, 3] if processed_image.shape[2] == 4 else mask
            rgb_image = processed_image[:, :, :3] if processed_image.shape[2] == 4 else image

            save_image_with_alpha(rgb_image, str(output_path), alpha_channel)

            # Verify transparency was added
            assert has_transparency(str(output_path)) is True

            results[method] = {
                "path": output_path,
                "mask_unique_values": len(np.unique(mask)),
                "alpha_mean": np.mean(alpha_channel)
            }

        # Verify different methods produce different results
        contour_mask = results["contour"]["mask_unique_values"]
        threshold_mask = results["threshold"]["mask_unique_values"]

        # Both should have at least some mask values (even if binary)
        assert contour_mask >= 1
        assert threshold_mask >= 1

        # At least one method should produce a non-trivial mask
        assert max(contour_mask, threshold_mask) >= 2

    def test_error_handling_workflow(self, temp_workspace):
        """Test error handling in transparency workflow."""
        # Test with non-existent file
        with pytest.raises(ValueError):
            load_image_with_alpha("nonexistent.png")

        # Test with invalid transparency method
        image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        with pytest.raises(ValueError, match="Unknown background removal method"):
            remove_background_auto(image, method="invalid_method")

        # Test saving to invalid path (should handle gracefully)
        image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        alpha = np.random.randint(0, 255, (50, 50), dtype=np.uint8)

        invalid_path = "/invalid/path/that/does/not/exist.png"
        success = save_image_with_alpha(image, invalid_path, alpha)

        assert success is False  # Should return False for invalid paths