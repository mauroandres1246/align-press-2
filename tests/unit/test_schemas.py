"""
Unit tests for Pydantic schemas.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from alignpress.core.schemas import (
    PlaneConfigSchema, ROIConfigSchema, LogoSpecSchema,
    ThresholdsSchema, FeatureParamsSchema, FallbackParamsSchema,
    DetectorConfigSchema, CalibrationDataSchema, LogoResultSchema,
    AppConfigSchema, FeatureType, LogLevel, ThemeType
)


class TestPlaneConfigSchema:
    """Test PlaneConfigSchema validation."""

    def test_valid_plane_config(self):
        """Test valid plane configuration."""
        config = PlaneConfigSchema(
            width_mm=300.0,
            height_mm=200.0,
            mm_per_px=0.5
        )

        assert config.width_mm == 300.0
        assert config.height_mm == 200.0
        assert config.mm_per_px == 0.5
        assert config.width_px == 600
        assert config.height_px == 400

    def test_invalid_plane_config(self):
        """Test invalid plane configuration."""
        # Negative dimensions
        with pytest.raises(ValueError):
            PlaneConfigSchema(width_mm=-100, height_mm=200, mm_per_px=0.5)

        # Zero scale
        with pytest.raises(ValueError):
            PlaneConfigSchema(width_mm=300, height_mm=200, mm_per_px=0)


class TestROIConfigSchema:
    """Test ROIConfigSchema validation."""

    def test_valid_roi_config(self):
        """Test valid ROI configuration."""
        roi = ROIConfigSchema(
            width_mm=50.0,
            height_mm=40.0,
            margin_factor=1.2
        )

        assert roi.width_mm == 50.0
        assert roi.height_mm == 40.0
        assert roi.margin_factor == 1.2

    def test_roi_config_defaults(self):
        """Test ROI configuration with defaults."""
        roi = ROIConfigSchema(width_mm=50.0, height_mm=40.0)
        assert roi.margin_factor == 1.2  # Default value

    def test_invalid_roi_config(self):
        """Test invalid ROI configuration."""
        # Negative dimensions
        with pytest.raises(ValueError):
            ROIConfigSchema(width_mm=-10, height_mm=40)

        # Invalid margin factor
        with pytest.raises(ValueError):
            ROIConfigSchema(width_mm=50, height_mm=40, margin_factor=0.5)


class TestLogoSpecSchema:
    """Test LogoSpecSchema validation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary template file
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        self.temp_file.write(b'fake png content')
        self.temp_file.close()
        self.template_path = Path(self.temp_file.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.template_path.exists():
            self.template_path.unlink()

    def test_valid_logo_spec(self):
        """Test valid logo specification."""
        logo = LogoSpecSchema(
            name="test_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
            angle_deg=0.0
        )

        assert logo.name == "test_logo"
        assert logo.template_path == self.template_path
        assert logo.position_mm == (150.0, 100.0)
        assert logo.angle_deg == 0.0

    def test_logo_spec_invalid_template(self):
        """Test logo spec with invalid template path."""
        with pytest.raises(ValueError):
            LogoSpecSchema(
                name="test",
                template_path=Path("nonexistent.png"),
                position_mm=(150.0, 100.0),
                roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
            )

    def test_logo_spec_invalid_position(self):
        """Test logo spec with invalid position."""
        with pytest.raises(ValueError):
            LogoSpecSchema(
                name="test",
                template_path=self.template_path,
                position_mm=(-10.0, 100.0),  # Negative position
                roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
            )

    def test_logo_spec_with_transparency_fields(self):
        """Test logo spec with transparency fields."""
        logo = LogoSpecSchema(
            name="transparent_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
            has_transparency=True,
            transparency_method="contour"
        )

        assert logo.has_transparency is True
        assert logo.transparency_method == "contour"

    def test_logo_spec_transparency_defaults(self):
        """Test logo spec transparency field defaults."""
        logo = LogoSpecSchema(
            name="test_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
        )

        # Defaults should be None
        assert logo.has_transparency is None
        assert logo.transparency_method is None

    def test_logo_spec_valid_transparency_methods(self):
        """Test valid transparency methods."""
        valid_methods = ["contour", "threshold", "grabcut"]

        for method in valid_methods:
            logo = LogoSpecSchema(
                name="test_logo",
                template_path=self.template_path,
                position_mm=(150.0, 100.0),
                roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
                transparency_method=method
            )
            assert logo.transparency_method == method

    def test_logo_spec_invalid_transparency_method(self):
        """Test invalid transparency method."""
        with pytest.raises(ValueError, match="transparency_method must be one of"):
            LogoSpecSchema(
                name="test_logo",
                template_path=self.template_path,
                position_mm=(150.0, 100.0),
                roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
                transparency_method="invalid_method"
            )

    def test_logo_spec_transparency_method_without_flag(self):
        """Test setting transparency method without has_transparency flag."""
        # Should be valid - transparency_method can exist without has_transparency
        logo = LogoSpecSchema(
            name="test_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
            transparency_method="threshold"
        )

        assert logo.has_transparency is None
        assert logo.transparency_method == "threshold"

    def test_logo_spec_has_transparency_without_method(self):
        """Test setting has_transparency without method."""
        # Should be valid - has_transparency can exist without method
        logo = LogoSpecSchema(
            name="test_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
            has_transparency=True
        )

        assert logo.has_transparency is True
        assert logo.transparency_method is None

    def test_logo_spec_serialization_with_transparency(self):
        """Test serialization/deserialization with transparency fields."""
        logo = LogoSpecSchema(
            name="transparent_logo",
            template_path=self.template_path,
            position_mm=(150.0, 100.0),
            roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0),
            has_transparency=True,
            transparency_method="contour"
        )

        # Serialize to dict
        logo_dict = logo.model_dump()
        assert logo_dict["has_transparency"] is True
        assert logo_dict["transparency_method"] == "contour"

        # Deserialize from dict
        logo_restored = LogoSpecSchema.model_validate(logo_dict)
        assert logo_restored.has_transparency is True
        assert logo_restored.transparency_method == "contour"

    def test_logo_spec_json_schema_includes_transparency(self):
        """Test that JSON schema includes transparency fields."""
        schema = LogoSpecSchema.model_json_schema()

        properties = schema["properties"]
        assert "has_transparency" in properties
        assert "transparency_method" in properties

        # Check that transparency_method includes proper description
        transparency_prop = properties["transparency_method"]
        assert "description" in transparency_prop
        assert "background removal" in transparency_prop["description"].lower()


class TestThresholdsSchema:
    """Test ThresholdsSchema validation."""

    def test_valid_thresholds(self):
        """Test valid thresholds configuration."""
        thresholds = ThresholdsSchema(
            position_tolerance_mm=3.0,
            angle_tolerance_deg=5.0,
            min_inliers=15,
            max_reproj_error=3.0
        )

        assert thresholds.position_tolerance_mm == 3.0
        assert thresholds.angle_tolerance_deg == 5.0
        assert thresholds.min_inliers == 15
        assert thresholds.max_reproj_error == 3.0

    def test_thresholds_defaults(self):
        """Test thresholds with default values."""
        thresholds = ThresholdsSchema()
        assert thresholds.position_tolerance_mm == 3.0
        assert thresholds.angle_tolerance_deg == 5.0
        assert thresholds.min_inliers == 15
        assert thresholds.max_reproj_error == 3.0

    def test_invalid_thresholds(self):
        """Test invalid thresholds."""
        # Negative tolerance
        with pytest.raises(ValueError):
            ThresholdsSchema(position_tolerance_mm=-1.0)

        # Too many inliers requirement
        with pytest.raises(ValueError):
            ThresholdsSchema(min_inliers=2)  # Less than 4


class TestFeatureParamsSchema:
    """Test FeatureParamsSchema validation."""

    def test_valid_feature_params(self):
        """Test valid feature parameters."""
        params = FeatureParamsSchema(
            feature_type=FeatureType.ORB,
            nfeatures=1500,
            scale_factor=1.2,
            nlevels=8
        )

        assert params.feature_type == FeatureType.ORB
        assert params.nfeatures == 1500
        assert params.scale_factor == 1.2
        assert params.nlevels == 8

    def test_feature_params_defaults(self):
        """Test feature parameters with defaults."""
        params = FeatureParamsSchema()
        assert params.feature_type == FeatureType.ORB
        assert params.nfeatures == 1500

    def test_invalid_feature_params(self):
        """Test invalid feature parameters."""
        # Too few features
        with pytest.raises(ValueError):
            FeatureParamsSchema(nfeatures=50)

        # Invalid scale factor
        with pytest.raises(ValueError):
            FeatureParamsSchema(scale_factor=0.5)


class TestFallbackParamsSchema:
    """Test FallbackParamsSchema validation."""

    def test_valid_fallback_params(self):
        """Test valid fallback parameters."""
        params = FallbackParamsSchema(
            enabled=True,
            scales=[0.8, 1.0, 1.2],
            angles=[-5, 0, 5],
            match_threshold=0.7
        )

        assert params.enabled is True
        assert params.scales == [0.8, 1.0, 1.2]
        assert params.angles == [-5, 0, 5]
        assert params.match_threshold == 0.7

    def test_invalid_fallback_params(self):
        """Test invalid fallback parameters."""
        # Invalid scales
        with pytest.raises(ValueError):
            FallbackParamsSchema(scales=[0.8, -1.0, 1.2])

        # Invalid threshold
        with pytest.raises(ValueError):
            FallbackParamsSchema(match_threshold=1.5)


class TestCalibrationDataSchema:
    """Test CalibrationDataSchema validation."""

    def test_valid_calibration_data(self):
        """Test valid calibration data."""
        homography = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]

        calibration = CalibrationDataSchema(
            camera_id=0,
            homography=homography,
            mm_per_px=0.5,
            timestamp=datetime.now()
        )

        assert calibration.camera_id == 0
        assert calibration.homography == homography
        assert calibration.mm_per_px == 0.5
        assert calibration.age_days >= 0

    def test_invalid_calibration_data(self):
        """Test invalid calibration data."""
        # Invalid homography dimensions
        with pytest.raises(ValueError):
            CalibrationDataSchema(
                camera_id=0,
                homography=[[1.0, 0.0], [0.0, 1.0]],  # 2x2 instead of 3x3
                mm_per_px=0.5
            )

        # Singular homography
        with pytest.raises(ValueError):
            CalibrationDataSchema(
                camera_id=0,
                homography=[
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0]
                ],
                mm_per_px=0.5
            )

    def test_calibration_expiry(self):
        """Test calibration expiry logic."""
        # Fresh calibration
        calibration = CalibrationDataSchema(
            camera_id=0,
            homography=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            mm_per_px=0.5,
            timestamp=datetime.now()
        )

        assert not calibration.is_expired(30)
        assert calibration.age_days == 0


class TestLogoResultSchema:
    """Test LogoResultSchema validation."""

    def test_valid_logo_result(self):
        """Test valid logo result."""
        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            position_mm=(150.0, 100.0),
            angle_deg=0.2,
            confidence=0.95,
            deviation_mm=1.4,
            angle_error_deg=0.2,
            inliers=45,
            reproj_error=1.2
        )

        assert result.logo_name == "test_logo"
        assert result.found is True
        assert result.position_mm == (150.0, 100.0)
        assert result.is_within_tolerance is True

    def test_logo_result_not_found(self):
        """Test logo result when not found."""
        result = LogoResultSchema(
            logo_name="test_logo",
            found=False
        )

        assert result.found is False
        assert result.position_mm is None
        assert result.is_within_tolerance is False

    def test_logo_result_out_of_tolerance(self):
        """Test logo result outside tolerance."""
        result = LogoResultSchema(
            logo_name="test_logo",
            found=True,
            deviation_mm=10.0,  # Outside default tolerance
            angle_error_deg=2.0
        )

        assert result.found is True
        assert result.is_within_tolerance is False


class TestDetectorConfigSchema:
    """Test DetectorConfigSchema validation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary template files
        self.temp_files = []
        for i in range(2):
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.write(b'fake png content')
            temp_file.close()
            self.temp_files.append(Path(temp_file.name))

    def teardown_method(self):
        """Clean up test fixtures."""
        for temp_file in self.temp_files:
            if temp_file.exists():
                temp_file.unlink()

    def test_valid_detector_config(self):
        """Test valid detector configuration."""
        config = DetectorConfigSchema(
            plane=PlaneConfigSchema(
                width_mm=300.0,
                height_mm=200.0,
                mm_per_px=0.5
            ),
            logos=[
                LogoSpecSchema(
                    name="logo1",
                    template_path=self.temp_files[0],
                    position_mm=(150.0, 100.0),
                    roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
                )
            ]
        )

        assert config.version == 1
        assert len(config.logos) == 1
        assert config.logos[0].name == "logo1"

    def test_detector_config_logos_outside_plane(self):
        """Test detector config with logos outside plane bounds."""
        with pytest.raises(ValueError):
            DetectorConfigSchema(
                plane=PlaneConfigSchema(
                    width_mm=100.0,  # Small plane
                    height_mm=100.0,
                    mm_per_px=0.5
                ),
                logos=[
                    LogoSpecSchema(
                        name="logo1",
                        template_path=self.temp_files[0],
                        position_mm=(200.0, 100.0),  # Outside plane
                        roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
                    )
                ]
            )

    def test_detector_config_duplicate_logo_names(self):
        """Test detector config with duplicate logo names."""
        with pytest.raises(ValueError):
            DetectorConfigSchema(
                plane=PlaneConfigSchema(
                    width_mm=300.0,
                    height_mm=200.0,
                    mm_per_px=0.5
                ),
                logos=[
                    LogoSpecSchema(
                        name="logo1",
                        template_path=self.temp_files[0],
                        position_mm=(100.0, 100.0),
                        roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
                    ),
                    LogoSpecSchema(
                        name="logo1",  # Duplicate name
                        template_path=self.temp_files[1],
                        position_mm=(200.0, 100.0),
                        roi=ROIConfigSchema(width_mm=50.0, height_mm=40.0)
                    )
                ]
            )


class TestAppConfigSchema:
    """Test AppConfigSchema validation."""

    def test_valid_app_config(self):
        """Test valid application configuration."""
        config = AppConfigSchema(
            language="es",
            ui_theme=ThemeType.LIGHT,
            technical_pin="1234",
            fps_target=30,
            log_level=LogLevel.INFO
        )

        assert config.language == "es"
        assert config.ui_theme == ThemeType.LIGHT
        assert config.technical_pin == "1234"
        assert config.fps_target == 30
        assert config.log_level == LogLevel.INFO

    def test_app_config_defaults(self):
        """Test application configuration with defaults."""
        config = AppConfigSchema()

        assert config.version == 1
        assert config.language == "es"
        assert config.ui_theme == ThemeType.LIGHT
        assert config.technical_pin == "2468"
        assert config.fullscreen is False
        assert config.fps_target == 30

    def test_app_config_validation(self):
        """Test application configuration validation."""
        # Invalid PIN (too short)
        with pytest.raises(ValueError):
            AppConfigSchema(technical_pin="123")

        # Invalid FPS
        with pytest.raises(ValueError):
            AppConfigSchema(fps_target=0)

        # Invalid warning days
        with pytest.raises(ValueError):
            AppConfigSchema(
                calibration_max_age_days=10,
                calibration_warning_days=15  # Warning > max age
            )