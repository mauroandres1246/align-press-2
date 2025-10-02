"""
Profile management for platen, style, and size variants.

This module handles loading and validation of configuration profiles
that define platen dimensions, logo styles, and size-specific offsets.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class CalibrationInfo(BaseModel):
    """Calibration information for a platen."""
    camera_id: int
    last_calibrated: datetime
    homography_path: str
    mm_per_px: float

    @property
    def age_days(self) -> int:
        """Calculate age of calibration in days."""
        # Handle both timezone-aware and naive datetimes
        now = datetime.now()
        if self.last_calibrated.tzinfo is not None:
            # If stored time is timezone-aware, make now aware too
            from datetime import timezone
            now = datetime.now(timezone.utc)
        return (now - self.last_calibrated).days

    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if calibration is expired."""
        return self.age_days > max_age_days


class PlatenProfile(BaseModel):
    """Profile for a platen (press plate)."""
    version: int
    name: str
    type: str = Field(default="platen")
    dimensions_mm: Dict[str, float]  # width, height
    calibration: CalibrationInfo
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "platen":
            raise ValueError(f"Type must be 'platen', got '{v}'")
        return v

    @property
    def width_mm(self) -> float:
        """Get platen width in mm."""
        return self.dimensions_mm["width"]

    @property
    def height_mm(self) -> float:
        """Get platen height in mm."""
        return self.dimensions_mm["height"]

    @classmethod
    def from_file(cls, path: Path) -> "PlatenProfile":
        """Load platen profile from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Platen profile not found: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded platen profile: {data.get('name')}")
        return cls(**data)

    def is_calibration_valid(self, max_age_days: int = 30) -> bool:
        """Check if calibration is still valid."""
        return not self.calibration.is_expired(max_age_days)


class LogoDefinition(BaseModel):
    """Definition of a logo in a style."""
    name: str
    template_path: str
    position_mm: List[float]  # [x, y]
    roi: Dict[str, float]  # width_mm, height_mm, margin_factor
    angle_deg: float = 0.0
    priority: int = 1

    @field_validator('position_mm')
    @classmethod
    def validate_position(cls, v: List[float]) -> List[float]:
        if len(v) != 2:
            raise ValueError(f"position_mm must have 2 values, got {len(v)}")
        return v


class StyleProfile(BaseModel):
    """Profile for a style (e.g., polo, t-shirt)."""
    version: int
    name: str
    type: str = Field(default="style")
    description: Optional[str] = None
    logos: List[LogoDefinition]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "style":
            raise ValueError(f"Type must be 'style', got '{v}'")
        return v

    @field_validator('logos')
    @classmethod
    def validate_logos_not_empty(cls, v: List[LogoDefinition]) -> List[LogoDefinition]:
        if not v:
            raise ValueError("Style must have at least one logo")
        return v

    @classmethod
    def from_file(cls, path: Path) -> "StyleProfile":
        """Load style profile from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Style profile not found: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded style profile: {data.get('name')}")
        return cls(**data)


class SizeVariant(BaseModel):
    """Size variant with position offsets."""
    version: int
    name: str
    type: str = Field(default="variant")
    size: str  # S, M, L, XL, etc.
    offsets: Dict[str, List[float]]  # logo_name -> [x_offset, y_offset]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "variant":
            raise ValueError(f"Type must be 'variant', got '{v}'")
        return v

    @classmethod
    def from_file(cls, path: Path) -> "SizeVariant":
        """Load size variant from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Size variant not found: {path}")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded size variant: {data.get('name')}")
        return cls(**data)

    def get_offset(self, logo_name: str) -> Tuple[float, float]:
        """Get offset for a specific logo."""
        offset = self.offsets.get(logo_name, [0.0, 0.0])
        return (offset[0], offset[1])


class ProfileLoader:
    """Loads and caches profiles."""

    def __init__(self, base_dir: Path = Path("profiles")):
        self.base_dir = base_dir
        self._platen_cache: Dict[str, PlatenProfile] = {}
        self._style_cache: Dict[str, StyleProfile] = {}
        self._variant_cache: Dict[str, SizeVariant] = {}

    def load_platen(self, name_or_path: str) -> PlatenProfile:
        """Load platen profile by name or path."""
        # Check cache first
        if name_or_path in self._platen_cache:
            logger.debug(f"Using cached platen: {name_or_path}")
            return self._platen_cache[name_or_path]

        # Determine path
        path = Path(name_or_path)
        if not path.is_absolute():
            path = self.base_dir / "planchas" / f"{name_or_path}.yaml"
            if not path.exists():
                path = self.base_dir / "planchas" / name_or_path

        # Load and cache
        profile = PlatenProfile.from_file(path)
        self._platen_cache[name_or_path] = profile
        return profile

    def load_style(self, name_or_path: str) -> StyleProfile:
        """Load style profile by name or path."""
        # Check cache first
        if name_or_path in self._style_cache:
            logger.debug(f"Using cached style: {name_or_path}")
            return self._style_cache[name_or_path]

        # Determine path
        path = Path(name_or_path)
        if not path.is_absolute():
            path = self.base_dir / "estilos" / f"{name_or_path}.yaml"
            if not path.exists():
                path = self.base_dir / "estilos" / name_or_path

        # Load and cache
        profile = StyleProfile.from_file(path)
        self._style_cache[name_or_path] = profile
        return profile

    def load_variant(self, name_or_path: str) -> SizeVariant:
        """Load size variant by name or path."""
        # Check cache first
        if name_or_path in self._variant_cache:
            logger.debug(f"Using cached variant: {name_or_path}")
            return self._variant_cache[name_or_path]

        # Determine path
        path = Path(name_or_path)
        if not path.is_absolute():
            path = self.base_dir / "variantes" / f"{name_or_path}.yaml"
            if not path.exists():
                path = self.base_dir / "variantes" / name_or_path

        # Load and cache
        profile = SizeVariant.from_file(path)
        self._variant_cache[name_or_path] = profile
        return profile

    def clear_cache(self) -> None:
        """Clear all cached profiles."""
        self._platen_cache.clear()
        self._style_cache.clear()
        self._variant_cache.clear()
        logger.info("Profile cache cleared")
