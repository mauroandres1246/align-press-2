"""
Pydantic schemas for configuration validation and data models.

This module defines all the data structures used throughout the application
with proper validation, type hints, and sensible defaults.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class FeatureType(str, Enum):
    """Supported feature detection algorithms."""
    ORB = "ORB"
    AKAZE = "AKAZE"
    SIFT = "SIFT"  # May require opencv-contrib-python


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ThemeType(str, Enum):
    """UI theme options."""
    LIGHT = "light"
    DARK = "dark"


class PlaneConfigSchema(BaseModel):
    """Configuration for the physical platen/plane."""

    width_mm: float = Field(..., gt=0, description="Platen width in millimeters")
    height_mm: float = Field(..., gt=0, description="Platen height in millimeters")
    mm_per_px: float = Field(..., gt=0, description="Scale factor: millimeters per pixel")

    model_config = {
        "json_schema_extra": {
            "example": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            }
        }
    }

    @property
    def width_px(self) -> int:
        """Calculate width in pixels."""
        return int(round(self.width_mm / self.mm_per_px))

    @property
    def height_px(self) -> int:
        """Calculate height in pixels."""
        return int(round(self.height_mm / self.mm_per_px))


class ROIConfigSchema(BaseModel):
    """Region of Interest configuration for logo detection."""

    width_mm: float = Field(..., gt=0, description="ROI width in millimeters")
    height_mm: float = Field(..., gt=0, description="ROI height in millimeters")
    margin_factor: float = Field(
        default=1.2,
        ge=1.0,
        le=3.0,
        description="Margin factor for ROI expansion"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "width_mm": 50.0,
                "height_mm": 40.0,
                "margin_factor": 1.2
            }
        }
    }


class LogoSpecSchema(BaseModel):
    """Specification for a logo to be detected."""

    name: str = Field(..., min_length=1, description="Logo identifier")
    template_path: Path = Field(..., description="Path to template image")
    position_mm: Tuple[float, float] = Field(..., description="Expected position (x, y) in mm")
    roi: ROIConfigSchema = Field(..., description="Region of interest configuration")
    angle_deg: float = Field(default=0.0, description="Expected angle in degrees")
    has_transparency: Optional[bool] = Field(default=None, description="Whether template has transparency channel")
    transparency_method: Optional[str] = Field(default=None, description="Method used for background removal")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "pecho",
                "template_path": "templates/logo_pecho.png",
                "position_mm": [150.0, 100.0],
                "roi": {
                    "width_mm": 50.0,
                    "height_mm": 40.0,
                    "margin_factor": 1.2
                },
                "angle_deg": 0.0,
                "has_transparency": True,
                "transparency_method": "contour"
            }
        }
    }

    @field_validator('transparency_method')
    @classmethod
    def validate_transparency_method(cls, v: Optional[str]) -> Optional[str]:
        """Validate transparency method."""
        if v is not None:
            valid_methods = {'contour', 'threshold', 'grabcut'}
            if v not in valid_methods:
                raise ValueError(f"transparency_method must be one of {valid_methods}")
        return v

    @field_validator('template_path')
    @classmethod
    def template_must_exist(cls, v):
        """Validate that template file exists."""
        if not v.exists():
            raise ValueError(f"Template file not found: {v}")
        if not v.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            raise ValueError(f"Invalid template format: {v.suffix}")
        return v

    @field_validator('position_mm')
    @classmethod
    def position_must_be_positive(cls, v):
        """Validate that position coordinates are non-negative."""
        x, y = v
        if x < 0 or y < 0:
            raise ValueError(f"Position coordinates must be non-negative: ({x}, {y})")
        return v


class ThresholdsSchema(BaseModel):
    """Detection thresholds and tolerances."""

    position_tolerance_mm: float = Field(
        default=3.0,
        gt=0,
        le=20.0,
        description="Position tolerance in millimeters"
    )
    angle_tolerance_deg: float = Field(
        default=5.0,
        gt=0,
        le=45.0,
        description="Angle tolerance in degrees"
    )
    min_inliers: int = Field(
        default=15,
        ge=4,
        description="Minimum RANSAC inliers required"
    )
    max_reproj_error: float = Field(
        default=3.0,
        gt=0,
        le=10.0,
        description="Maximum reprojection error in pixels"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "position_tolerance_mm": 3.0,
                "angle_tolerance_deg": 5.0,
                "min_inliers": 15,
                "max_reproj_error": 3.0
            }
        }
    }


class FeatureParamsSchema(BaseModel):
    """Feature detection parameters."""

    feature_type: FeatureType = Field(default=FeatureType.ORB, description="Feature detection algorithm")
    nfeatures: int = Field(
        default=1500,
        ge=100,
        le=10000,
        description="Maximum number of features to detect"
    )
    scale_factor: float = Field(
        default=1.2,
        gt=1.0,
        le=2.0,
        description="Pyramid decimation ratio for ORB"
    )
    nlevels: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Number of pyramid levels for ORB"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "feature_type": "ORB",
                "nfeatures": 1500,
                "scale_factor": 1.2,
                "nlevels": 8
            }
        }
    }


class FallbackParamsSchema(BaseModel):
    """Parameters for fallback template matching."""

    enabled: bool = Field(default=True, description="Enable fallback template matching")
    scales: List[float] = Field(
        default=[0.8, 0.9, 1.0, 1.1, 1.2],
        description="Scale factors to try"
    )
    angles: List[float] = Field(
        default=[-10, -5, 0, 5, 10],
        description="Angles in degrees to try"
    )
    match_threshold: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Template matching threshold"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled": True,
                "scales": [0.8, 0.9, 1.0, 1.1, 1.2],
                "angles": [-10, -5, 0, 5, 10],
                "match_threshold": 0.7
            }
        }
    }

    @field_validator('scales')
    @classmethod
    def scales_must_be_positive(cls, v):
        """Validate that all scales are positive."""
        if any(s <= 0 for s in v):
            raise ValueError("All scales must be positive")
        return v


class DetectorConfigSchema(BaseModel):
    """Complete detector configuration."""

    version: int = Field(default=1, description="Configuration version")
    plane: PlaneConfigSchema = Field(..., description="Platen configuration")
    logos: List[LogoSpecSchema] = Field(..., min_length=1, description="Logo specifications")
    thresholds: ThresholdsSchema = Field(default_factory=ThresholdsSchema)
    features: FeatureParamsSchema = Field(default_factory=FeatureParamsSchema)
    fallback: FallbackParamsSchema = Field(default_factory=FallbackParamsSchema)

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": 1,
                "plane": {
                    "width_mm": 300.0,
                    "height_mm": 200.0,
                    "mm_per_px": 0.5
                },
                "logos": [
                    {
                        "name": "pecho",
                        "template_path": "templates/logo_pecho.png",
                        "position_mm": [150.0, 100.0],
                        "roi": {
                            "width_mm": 50.0,
                            "height_mm": 40.0,
                            "margin_factor": 1.2
                        },
                        "angle_deg": 0.0
                    }
                ]
            }
        }
    }

    @model_validator(mode='after')
    @classmethod
    def validate_logos_in_plane(cls, model):
        """Validate that all logos fit within the platen."""
        plane = model.plane
        logos = model.logos

        if not plane or not logos:
            return model

        for logo in logos:
            x, y = logo.position_mm
            roi_w = logo.roi.width_mm * logo.roi.margin_factor
            roi_h = logo.roi.height_mm * logo.roi.margin_factor

            # Check if ROI fits within platen
            if (x - roi_w/2 < 0 or x + roi_w/2 > plane.width_mm or
                y - roi_h/2 < 0 or y + roi_h/2 > plane.height_mm):
                raise ValueError(
                    f"Logo '{logo.name}' ROI extends outside platen bounds. "
                    f"Position: ({x}, {y}), ROI: {roi_w}x{roi_h}, "
                    f"Platen: {plane.width_mm}x{plane.height_mm}"
                )

        return model

    @field_validator('logos')
    @classmethod
    def logo_names_must_be_unique(cls, v):
        """Validate that logo names are unique."""
        names = [logo.name for logo in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate logo names found: {set(duplicates)}")
        return v


class CalibrationDataSchema(BaseModel):
    """Camera calibration data."""

    version: int = Field(default=1, description="Calibration version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Calibration timestamp")
    camera_id: Union[int, str] = Field(..., description="Camera identifier")
    homography: List[List[float]] = Field(..., description="3x3 homography matrix as nested list")
    mm_per_px: float = Field(..., gt=0, description="Scale factor")
    pattern_info: Dict[str, Any] = Field(default_factory=dict, description="Calibration pattern metadata")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Quality metrics")

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": 1,
                "timestamp": "2025-09-28T14:30:00Z",
                "camera_id": 0,
                "homography": [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0]
                ],
                "mm_per_px": 0.5,
                "pattern_info": {
                    "type": "chessboard",
                    "size": [9, 6],
                    "square_size_mm": 25.0
                },
                "quality_metrics": {
                    "reproj_error_px": 0.8,
                    "corners_detected": 54,
                    "corners_expected": 54
                }
            }
        }
    }

    @field_validator('homography')
    @classmethod
    def homography_must_be_3x3(cls, v):
        """Validate homography matrix dimensions."""
        if len(v) != 3 or any(len(row) != 3 for row in v):
            raise ValueError("Homography must be a 3x3 matrix")

        # Check if matrix is invertible (non-zero determinant)
        H = np.array(v)
        if abs(np.linalg.det(H)) < 1e-10:
            raise ValueError("Homography matrix is singular (determinant ≈ 0)")

        return v

    @property
    def age_days(self) -> int:
        """Calculate age of calibration in days."""
        return (datetime.now() - self.timestamp).days

    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if calibration is expired."""
        return self.age_days > max_age_days


class LogoResultSchema(BaseModel):
    """Result of logo detection."""

    logo_name: str = Field(..., description="Logo identifier")
    found: bool = Field(..., description="Whether logo was detected")
    position_mm: Optional[Tuple[float, float]] = Field(None, description="Detected position (x, y) in mm")
    angle_deg: Optional[float] = Field(None, description="Detected angle in degrees")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Detection confidence")
    deviation_mm: Optional[float] = Field(None, ge=0, description="Position deviation in mm")
    angle_error_deg: Optional[float] = Field(None, description="Angle error in degrees")
    inliers: Optional[int] = Field(None, ge=0, description="Number of RANSAC inliers")
    reproj_error: Optional[float] = Field(None, ge=0, description="Reprojection error in pixels")
    method_used: Optional[str] = Field(None, description="Detection method used")
    processing_time_ms: Optional[float] = Field(None, ge=0, description="Processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "logo_name": "pecho",
                "found": True,
                "position_mm": [148.7, 100.3],
                "angle_deg": 0.2,
                "confidence": 0.95,
                "deviation_mm": 1.4,
                "angle_error_deg": 0.2,
                "inliers": 45,
                "reproj_error": 1.2,
                "method_used": "ORB+RANSAC",
                "processing_time_ms": 15.6
            }
        }
    }

    @property
    def is_within_tolerance(self) -> bool:
        """Check if detection is within acceptable tolerances."""
        if not self.found:
            return False

        # These would typically come from the detector config
        # For now, use reasonable defaults
        pos_ok = self.deviation_mm is None or self.deviation_mm <= 3.0
        angle_ok = self.angle_error_deg is None or abs(self.angle_error_deg) <= 5.0

        return pos_ok and angle_ok


class AppConfigSchema(BaseModel):
    """Application-wide configuration."""

    version: int = Field(default=1, description="Configuration version")
    language: str = Field(default="es", description="Application language")

    # Paths configuration
    profiles_path: Path = Field(default=Path("profiles"), description="Profiles directory")
    templates_path: Path = Field(default=Path("templates"), description="Templates directory")
    calibration_path: Path = Field(default=Path("calibration"), description="Calibration directory")
    datasets_path: Path = Field(default=Path("datasets"), description="Datasets directory")
    logs_path: Path = Field(default=Path("logs"), description="Logs directory")

    # UI configuration
    ui_theme: ThemeType = Field(default=ThemeType.LIGHT, description="UI theme")
    technical_pin: str = Field(default="2468", min_length=4, description="Technical mode PIN")
    fullscreen: bool = Field(default=False, description="Start in fullscreen mode")
    fps_target: int = Field(default=30, ge=1, le=60, description="Target FPS for camera")

    # Detector defaults
    detector_feature_type: FeatureType = Field(default=FeatureType.ORB)
    detector_nfeatures: int = Field(default=1500, ge=100, le=10000)
    detector_fallback_enabled: bool = Field(default=True)

    # Calibration settings
    calibration_max_age_days: int = Field(default=30, ge=1, description="Max calibration age")
    calibration_warning_days: int = Field(default=7, ge=1, description="Warning threshold")

    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    log_format: str = Field(default="json", description="Log format")
    log_output_path: Path = Field(default=Path("logs/sessions"), description="Log output directory")

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": 1,
                "language": "es",
                "ui_theme": "light",
                "technical_pin": "2468",
                "fullscreen": False,
                "fps_target": 30,
                "calibration_max_age_days": 30,
                "log_level": "INFO"
            }
        }
    }

    @model_validator(mode='after')
    @classmethod
    def warning_days_less_than_max_age(cls, model):
        """Validate that warning comes before expiration."""
        if model.calibration_warning_days >= model.calibration_max_age_days:
            raise ValueError("Warning days must be less than max age days")
        return model