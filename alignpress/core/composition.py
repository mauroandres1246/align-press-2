"""
Composition module for combining platen, style, and variant profiles.

This module creates detector configurations by combining:
- Platen dimensions and calibration
- Style logo definitions
- Optional size variant offsets
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

from .profile import PlatenProfile, StyleProfile, SizeVariant, LogoDefinition

logger = logging.getLogger(__name__)


class Composition:
    """
    Combines platen, style, and variant into a detector configuration.

    This class validates that all logos fit within the platen boundaries
    and generates a complete configuration for PlanarLogoDetector.
    """

    def __init__(
        self,
        platen: PlatenProfile,
        style: StyleProfile,
        variant: Optional[SizeVariant] = None
    ):
        """
        Initialize composition.

        Args:
            platen: Platen profile with dimensions and calibration
            style: Style profile with logo definitions
            variant: Optional size variant with position offsets

        Raises:
            ValueError: If composition is invalid
        """
        self.platen = platen
        self.style = style
        self.variant = variant

        # Validate composition
        self._validate()

        logger.info(
            f"Created composition: {platen.name} + {style.name}" +
            (f" + {variant.name}" if variant else "")
        )

    def _validate(self) -> None:
        """Validate that all logos fit within platen boundaries."""
        errors = []

        for logo in self.style.logos:
            # Get final position (with variant offset if applicable)
            final_pos = self._get_final_position(logo)

            # Check if logo center is within platen
            if final_pos[0] < 0 or final_pos[0] > self.platen.width_mm:
                errors.append(
                    f"Logo '{logo.name}' X position {final_pos[0]:.1f}mm "
                    f"outside platen width {self.platen.width_mm:.1f}mm"
                )

            if final_pos[1] < 0 or final_pos[1] > self.platen.height_mm:
                errors.append(
                    f"Logo '{logo.name}' Y position {final_pos[1]:.1f}mm "
                    f"outside platen height {self.platen.height_mm:.1f}mm"
                )

            # Check ROI boundaries
            roi_half_width = logo.roi["width_mm"] * logo.roi.get("margin_factor", 1.0) / 2
            roi_half_height = logo.roi["height_mm"] * logo.roi.get("margin_factor", 1.0) / 2

            if (final_pos[0] - roi_half_width < 0 or
                final_pos[0] + roi_half_width > self.platen.width_mm):
                errors.append(
                    f"Logo '{logo.name}' ROI extends outside platen width"
                )

            if (final_pos[1] - roi_half_height < 0 or
                final_pos[1] + roi_half_height > self.platen.height_mm):
                errors.append(
                    f"Logo '{logo.name}' ROI extends outside platen height"
                )

        if errors:
            error_msg = "Composition validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_final_position(self, logo: LogoDefinition) -> Tuple[float, float]:
        """Get final logo position including variant offset."""
        base_x, base_y = logo.position_mm[0], logo.position_mm[1]

        if self.variant:
            offset_x, offset_y = self.variant.get_offset(logo.name)
            return (base_x + offset_x, base_y + offset_y)

        return (base_x, base_y)

    def get_expected_positions(self) -> Dict[str, Tuple[float, float]]:
        """
        Get expected positions for all logos.

        Returns:
            Dictionary mapping logo name to (x, y) position in mm
        """
        positions = {}
        for logo in self.style.logos:
            positions[logo.name] = self._get_final_position(logo)
        return positions

    def to_detector_config(self) -> Dict[str, Any]:
        """
        Generate detector configuration dictionary.

        Returns:
            Configuration dictionary compatible with PlanarLogoDetector
        """
        # Build logos configuration
        logos_config = []
        for logo in self.style.logos:
            final_pos = self._get_final_position(logo)

            logo_config = {
                "name": logo.name,
                "template_path": logo.template_path,
                "position_mm": list(final_pos),
                "angle_deg": logo.angle_deg,
                "roi": {
                    "width_mm": logo.roi["width_mm"],
                    "height_mm": logo.roi["height_mm"],
                    "margin_factor": logo.roi.get("margin_factor", 1.5)
                }
            }
            logos_config.append(logo_config)

        # Build complete configuration
        config = {
            "plane": {
                "width_mm": self.platen.width_mm,
                "height_mm": self.platen.height_mm,
                "mm_per_px": self.platen.calibration.mm_per_px,
                "homography": None  # Will be loaded separately if needed
            },
            "logos": logos_config,
            "thresholds": {
                "max_deviation_mm": 5.0,
                "max_angle_error_deg": 10.0,
                "min_inliers": 15,
                "max_reproj_error_px": 3.0
            },
            "features": {
                "feature_type": "ORB",
                "nfeatures": 1500,
                "scale_factor": 1.2,
                "nlevels": 8
            },
            "fallback": {
                "enabled": True,
                "scales": [0.8, 0.9, 1.0, 1.1, 1.2],
                "angles_deg": [-10, -5, 0, 5, 10],
                "match_threshold": 0.7
            }
        }

        logger.debug(f"Generated detector config with {len(logos_config)} logos")
        return config

    def get_calibration_path(self) -> str:
        """Get path to calibration file."""
        return self.platen.calibration.homography_path

    def is_calibration_valid(self, max_age_days: int = 30) -> bool:
        """Check if platen calibration is still valid."""
        return self.platen.is_calibration_valid(max_age_days)

    def get_calibration_warning(self) -> Optional[str]:
        """Get calibration warning message if needed."""
        age = self.platen.calibration.age_days

        if age > 30:
            return f"⚠️  Calibration expired ({age} days old). Recalibration required."
        elif age > 21:
            return f"⚠️  Calibration expiring soon ({age} days old)."

        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize composition to dictionary.

        Returns:
            Dictionary representation of composition
        """
        return {
            "platen": self.platen.name,
            "style": self.style.name,
            "variant": self.variant.name if self.variant else None,
            "logos": list(self.get_expected_positions().keys()),
            "calibration_age_days": self.platen.calibration.age_days,
            "calibration_valid": self.is_calibration_valid()
        }

    def __repr__(self) -> str:
        variant_str = f" + {self.variant.name}" if self.variant else ""
        return f"<Composition: {self.platen.name} + {self.style.name}{variant_str}>"
