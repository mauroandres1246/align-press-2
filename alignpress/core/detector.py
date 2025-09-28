"""
Planar logo detector using OpenCV ORB features and RANSAC.

This module implements the core detection algorithm that finds logos on textile
presses using feature matching and geometric verification.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging

import cv2
import numpy as np

from ..utils.geometry import angle_deg, l2, polygon_center, angle_diff_circular
from ..utils.image_utils import (
    mm_to_px, px_to_mm, extract_roi, warp_perspective,
    convert_color_safe, enhance_contrast
)
from .schemas import (
    DetectorConfigSchema, LogoSpecSchema, PlaneConfigSchema,
    FeatureParamsSchema, ThresholdsSchema, FallbackParamsSchema,
    LogoResultSchema, FeatureType
)

logger = logging.getLogger(__name__)


class PlanarLogoDetector:
    """
    Detector for logos on planar surfaces using feature matching.

    This detector uses ORB features as the primary method with optional
    fallback to template matching for challenging cases.
    """

    def __init__(self, config: Union[Dict[str, Any], DetectorConfigSchema]):
        """
        Initialize the detector with configuration.

        Args:
            config: Detector configuration (dict or schema)

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate and convert config
        if isinstance(config, dict):
            self.config = DetectorConfigSchema(**config)
        else:
            self.config = config

        # Initialize feature detector
        self._feature_detector = self._create_feature_detector()
        self._feature_matcher = self._create_matcher()

        # Load and process templates
        self._templates = {}
        self._template_keypoints = {}
        self._template_descriptors = {}

        self._load_templates()

        logger.info(
            f"Detector initialized: {len(self.config.logos)} logos, "
            f"{self.config.features.feature_type} with {self.config.features.nfeatures} features"
        )

    def _create_feature_detector(self) -> cv2.Feature2D:
        """Create feature detector based on configuration."""
        params = self.config.features

        if params.feature_type == FeatureType.ORB:
            return cv2.ORB_create(
                nfeatures=params.nfeatures,
                scaleFactor=params.scale_factor,
                nlevels=params.nlevels
            )
        elif params.feature_type == FeatureType.AKAZE:
            return cv2.AKAZE_create()
        elif params.feature_type == FeatureType.SIFT:
            return cv2.SIFT_create(nfeatures=params.nfeatures)
        else:
            raise ValueError(f"Unsupported feature type: {params.feature_type}")

    def _create_matcher(self) -> cv2.BFMatcher:
        """Create feature matcher based on detector type."""
        if self.config.features.feature_type == FeatureType.SIFT:
            # SIFT uses float descriptors
            return cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        else:
            # ORB and AKAZE use binary descriptors
            return cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def _load_templates(self) -> None:
        """Load and process all template images."""
        for logo_spec in self.config.logos:
            try:
                self._load_single_template(logo_spec)
            except Exception as e:
                logger.error(f"Failed to load template for {logo_spec.name}: {e}")
                raise

    def _load_single_template(self, logo_spec: LogoSpecSchema) -> None:
        """Load and process a single template image."""
        template_path = Path(logo_spec.template_path)

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Load template image
        template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
        if template is None:
            raise ValueError(f"Could not load template image: {template_path}")

        # Convert to grayscale and enhance
        template_gray = convert_color_safe(template, cv2.COLOR_BGR2GRAY)
        template_enhanced = enhance_contrast(template_gray)

        # Detect features
        keypoints, descriptors = self._feature_detector.detectAndCompute(template_enhanced, None)

        if descriptors is None or len(keypoints) < 10:
            logger.warning(
                f"Template {logo_spec.name} has insufficient features "
                f"({len(keypoints) if keypoints else 0}). Consider using a different template."
            )

        # Store template data
        self._templates[logo_spec.name] = template_enhanced
        self._template_keypoints[logo_spec.name] = keypoints
        self._template_descriptors[logo_spec.name] = descriptors

        logger.debug(f"Loaded template {logo_spec.name}: {len(keypoints)} features")

    def detect_logos(
        self,
        image: np.ndarray,
        homography: Optional[np.ndarray] = None
    ) -> List[LogoResultSchema]:
        """
        Detect all configured logos in the input image.

        Args:
            image: Input image (BGR format)
            homography: Optional homography for perspective correction

        Returns:
            List of detection results for each logo

        Raises:
            ValueError: If image is invalid
        """
        if image is None or image.size == 0:
            raise ValueError("Input image is invalid")

        start_time = time.time()

        # Apply homography if provided
        if homography is not None:
            plane_size = (self.config.plane.width_px, self.config.plane.height_px)
            image = warp_perspective(image, homography, plane_size)

        # Convert to grayscale and enhance
        image_gray = convert_color_safe(image, cv2.COLOR_BGR2GRAY)
        image_enhanced = enhance_contrast(image_gray)

        results = []
        for logo_spec in self.config.logos:
            logo_start = time.time()
            result = self._detect_single_logo(image_enhanced, logo_spec)
            result.processing_time_ms = (time.time() - logo_start) * 1000
            results.append(result)

        total_time = (time.time() - start_time) * 1000
        logger.debug(f"Detection completed in {total_time:.1f}ms for {len(results)} logos")

        return results

    def _detect_single_logo(
        self,
        image: np.ndarray,
        logo_spec: LogoSpecSchema
    ) -> LogoResultSchema:
        """
        Detect a single logo in the image.

        Args:
            image: Preprocessed grayscale image
            logo_spec: Logo specification

        Returns:
            Detection result for the logo
        """
        # Initialize result
        result = LogoResultSchema(
            logo_name=logo_spec.name,
            found=False
        )

        try:
            # Extract ROI around expected position
            roi, roi_offset = self._extract_logo_roi(image, logo_spec)
            if roi is None:
                logger.warning(f"Could not extract ROI for logo {logo_spec.name}")
                return result

            # Try feature-based detection first
            feature_result = self._detect_with_features(roi, logo_spec, roi_offset)
            if feature_result.found and self._is_detection_valid(feature_result):
                feature_result.method_used = f"{self.config.features.feature_type}+RANSAC"
                return feature_result

            # Try fallback template matching if enabled
            if self.config.fallback.enabled:
                logger.debug(f"Trying fallback template matching for {logo_spec.name}")
                fallback_result = self._detect_with_template_matching(roi, logo_spec, roi_offset)
                if fallback_result.found:
                    fallback_result.method_used = "Template Matching"
                    return fallback_result

            return result

        except Exception as e:
            logger.error(f"Error detecting logo {logo_spec.name}: {e}")
            return result

    def _extract_logo_roi(
        self,
        image: np.ndarray,
        logo_spec: LogoSpecSchema
    ) -> Tuple[Optional[np.ndarray], Tuple[int, int]]:
        """
        Extract Region of Interest around expected logo position.

        Args:
            image: Input grayscale image
            logo_spec: Logo specification

        Returns:
            Tuple of (ROI image, ROI offset in original image)
        """
        # Convert expected position to pixels
        expected_px = mm_to_px(
            logo_spec.position_mm[0],
            logo_spec.position_mm[1],
            1.0 / self.config.plane.mm_per_px
        )

        # Calculate ROI size with margin
        roi_size_mm = (
            logo_spec.roi.width_mm * logo_spec.roi.margin_factor,
            logo_spec.roi.height_mm * logo_spec.roi.margin_factor
        )
        roi_size_px = mm_to_px(
            roi_size_mm[0],
            roi_size_mm[1],
            1.0 / self.config.plane.mm_per_px
        )

        try:
            roi = extract_roi(image, expected_px, roi_size_px)
            roi_offset = (
                expected_px[0] - roi_size_px[0] // 2,
                expected_px[1] - roi_size_px[1] // 2
            )
            return roi, roi_offset
        except Exception as e:
            logger.error(f"Failed to extract ROI for {logo_spec.name}: {e}")
            return None, (0, 0)

    def _detect_with_features(
        self,
        roi: np.ndarray,
        logo_spec: LogoSpecSchema,
        roi_offset: Tuple[int, int]
    ) -> LogoResultSchema:
        """
        Detect logo using feature matching and RANSAC.

        Args:
            roi: Region of interest image
            logo_spec: Logo specification
            roi_offset: ROI offset in original image

        Returns:
            Detection result
        """
        result = LogoResultSchema(logo_name=logo_spec.name, found=False)

        # Get template data
        template_kp = self._template_keypoints.get(logo_spec.name)
        template_desc = self._template_descriptors.get(logo_spec.name)

        if template_desc is None or len(template_kp) < 4:
            logger.warning(f"Insufficient template data for {logo_spec.name}")
            return result

        # Detect features in ROI
        roi_kp, roi_desc = self._feature_detector.detectAndCompute(roi, None)
        if roi_desc is None or len(roi_kp) < 4:
            logger.debug(f"Insufficient features in ROI for {logo_spec.name}")
            return result

        # Match features
        matches = self._feature_matcher.match(template_desc, roi_desc)
        if len(matches) < 4:
            logger.debug(f"Insufficient matches for {logo_spec.name}: {len(matches)}")
            return result

        # Sort matches by distance
        matches = sorted(matches, key=lambda x: x.distance)

        # Extract matching points
        template_pts = np.float32([template_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        roi_pts = np.float32([roi_kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        # Find homography with RANSAC
        try:
            H, mask = cv2.findHomography(
                template_pts, roi_pts,
                cv2.RANSAC,
                self.config.thresholds.max_reproj_error
            )

            if H is None:
                return result

            # Count inliers
            inliers = np.sum(mask)
            if inliers < self.config.thresholds.min_inliers:
                logger.debug(f"Insufficient inliers for {logo_spec.name}: {inliers}")
                return result

            # Calculate detection center
            template_center = self._get_template_center(logo_spec.name)
            roi_center = cv2.perspectiveTransform(
                np.array([[template_center]], dtype=np.float32), H
            )[0][0]

            # Convert to global coordinates
            global_center = (
                roi_center[0] + roi_offset[0],
                roi_center[1] + roi_offset[1]
            )

            # Convert to millimeters
            center_mm = px_to_mm(
                int(global_center[0]),
                int(global_center[1]),
                1.0 / self.config.plane.mm_per_px
            )

            # Calculate angle from homography
            detected_angle = self._extract_angle_from_homography(H)

            # Calculate deviations
            expected_mm = logo_spec.position_mm
            deviation_mm = l2(center_mm, expected_mm)
            angle_error = angle_diff_circular(logo_spec.angle_deg, detected_angle)

            # Calculate reprojection error
            reproj_error = self._calculate_reprojection_error(
                template_pts, roi_pts, H, mask
            )

            # Update result
            result.found = True
            result.position_mm = center_mm
            result.angle_deg = detected_angle
            result.deviation_mm = deviation_mm
            result.angle_error_deg = angle_error
            result.inliers = int(inliers)
            result.reproj_error = reproj_error
            result.confidence = min(1.0, inliers / len(matches))

            logger.debug(
                f"Logo {logo_spec.name} detected: "
                f"pos={center_mm}, dev={deviation_mm:.1f}mm, "
                f"angle={detected_angle:.1f}°, inliers={inliers}"
            )

        except cv2.error as e:
            logger.error(f"OpenCV error in feature detection for {logo_spec.name}: {e}")

        return result

    def _detect_with_template_matching(
        self,
        roi: np.ndarray,
        logo_spec: LogoSpecSchema,
        roi_offset: Tuple[int, int]
    ) -> LogoResultSchema:
        """
        Detect logo using template matching as fallback.

        Args:
            roi: Region of interest image
            logo_spec: Logo specification
            roi_offset: ROI offset in original image

        Returns:
            Detection result
        """
        result = LogoResultSchema(logo_name=logo_spec.name, found=False)

        template = self._templates.get(logo_spec.name)
        if template is None:
            return result

        best_match_val = 0
        best_match_loc = None
        best_scale = 1.0
        best_angle = 0.0

        # Try different scales and angles
        for scale in self.config.fallback.scales:
            for angle in self.config.fallback.angles:
                # Rotate and scale template
                transformed_template = self._transform_template(template, scale, angle)
                if transformed_template is None:
                    continue

                # Skip if template is larger than ROI
                if (transformed_template.shape[0] > roi.shape[0] or
                    transformed_template.shape[1] > roi.shape[1]):
                    continue

                # Template matching
                result_tm = cv2.matchTemplate(
                    roi, transformed_template, cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, max_loc = cv2.minMaxLoc(result_tm)

                if max_val > best_match_val:
                    best_match_val = max_val
                    best_match_loc = max_loc
                    best_scale = scale
                    best_angle = angle

        # Check if match is good enough
        if best_match_val < self.config.fallback.match_threshold:
            return result

        # Calculate detection center
        template_h, template_w = template.shape[:2]
        scaled_w = int(template_w * best_scale)
        scaled_h = int(template_h * best_scale)

        roi_center = (
            best_match_loc[0] + scaled_w // 2,
            best_match_loc[1] + scaled_h // 2
        )

        # Convert to global coordinates
        global_center = (
            roi_center[0] + roi_offset[0],
            roi_center[1] + roi_offset[1]
        )

        # Convert to millimeters
        center_mm = px_to_mm(
            int(global_center[0]),
            int(global_center[1]),
            1.0 / self.config.plane.mm_per_px
        )

        # Calculate deviations
        expected_mm = logo_spec.position_mm
        deviation_mm = l2(center_mm, expected_mm)
        detected_angle = logo_spec.angle_deg + best_angle
        angle_error = angle_diff_circular(logo_spec.angle_deg, detected_angle)

        # Update result
        result.found = True
        result.position_mm = center_mm
        result.angle_deg = detected_angle
        result.deviation_mm = deviation_mm
        result.angle_error_deg = angle_error
        result.confidence = best_match_val

        logger.debug(
            f"Logo {logo_spec.name} detected via template matching: "
            f"pos={center_mm}, dev={deviation_mm:.1f}mm, "
            f"confidence={best_match_val:.3f}"
        )

        return result

    def _get_template_center(self, logo_name: str) -> Tuple[float, float]:
        """Get the center point of a template image."""
        template = self._templates[logo_name]
        h, w = template.shape[:2]
        return (w / 2.0, h / 2.0)

    def _extract_angle_from_homography(self, H: np.ndarray) -> float:
        """Extract rotation angle from homography matrix."""
        # Extract rotation component (approximate for small rotations)
        return float(np.degrees(np.arctan2(H[1, 0], H[0, 0])))

    def _calculate_reprojection_error(
        self,
        template_pts: np.ndarray,
        roi_pts: np.ndarray,
        H: np.ndarray,
        mask: np.ndarray
    ) -> float:
        """Calculate average reprojection error for inliers."""
        if mask is None or np.sum(mask) == 0:
            return float('inf')

        # Transform template points using homography
        projected_pts = cv2.perspectiveTransform(template_pts, H)

        # Calculate errors for inliers only
        errors = []
        for i, is_inlier in enumerate(mask.ravel()):
            if is_inlier:
                error = np.linalg.norm(projected_pts[i][0] - roi_pts[i][0])
                errors.append(error)

        return float(np.mean(errors)) if errors else float('inf')

    def _transform_template(
        self,
        template: np.ndarray,
        scale: float,
        angle: float
    ) -> Optional[np.ndarray]:
        """Transform template with scale and rotation."""
        try:
            h, w = template.shape[:2]
            center = (w // 2, h // 2)

            # Create transformation matrix
            M = cv2.getRotationMatrix2D(center, angle, scale)

            # Calculate new dimensions
            cos_a = abs(M[0, 0])
            sin_a = abs(M[0, 1])
            new_w = int(h * sin_a + w * cos_a)
            new_h = int(h * cos_a + w * sin_a)

            # Adjust transformation matrix for new center
            M[0, 2] += (new_w / 2) - center[0]
            M[1, 2] += (new_h / 2) - center[1]

            # Apply transformation
            transformed = cv2.warpAffine(template, M, (new_w, new_h))
            return transformed

        except Exception as e:
            logger.error(f"Error transforming template: {e}")
            return None

    def _is_detection_valid(self, result: LogoResultSchema) -> bool:
        """Check if detection result meets quality thresholds."""
        if not result.found:
            return False

        # Check position tolerance
        if (result.deviation_mm is not None and
            result.deviation_mm > self.config.thresholds.position_tolerance_mm):
            return False

        # Check angle tolerance
        if (result.angle_error_deg is not None and
            abs(result.angle_error_deg) > self.config.thresholds.angle_tolerance_deg):
            return False

        # Check minimum inliers (for feature-based detection)
        if (result.inliers is not None and
            result.inliers < self.config.thresholds.min_inliers):
            return False

        # Check reprojection error
        if (result.reproj_error is not None and
            result.reproj_error > self.config.thresholds.max_reproj_error):
            return False

        return True

    def get_expected_positions_px(self) -> Dict[str, Tuple[int, int]]:
        """
        Get expected positions of all logos in pixels.

        Returns:
            Dictionary mapping logo names to pixel positions
        """
        positions = {}
        scale = 1.0 / self.config.plane.mm_per_px

        for logo_spec in self.config.logos:
            pos_px = mm_to_px(logo_spec.position_mm[0], logo_spec.position_mm[1], scale)
            positions[logo_spec.name] = pos_px

        return positions

    def get_roi_bounds_px(self, logo_name: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Get ROI bounds for a logo in pixels.

        Args:
            logo_name: Name of the logo

        Returns:
            ROI bounds as (x1, y1, x2, y2) or None if logo not found
        """
        logo_spec = None
        for spec in self.config.logos:
            if spec.name == logo_name:
                logo_spec = spec
                break

        if logo_spec is None:
            return None

        scale = 1.0 / self.config.plane.mm_per_px
        center_px = mm_to_px(logo_spec.position_mm[0], logo_spec.position_mm[1], scale)

        roi_size_mm = (
            logo_spec.roi.width_mm * logo_spec.roi.margin_factor,
            logo_spec.roi.height_mm * logo_spec.roi.margin_factor
        )
        roi_size_px = mm_to_px(roi_size_mm[0], roi_size_mm[1], scale)

        x1 = center_px[0] - roi_size_px[0] // 2
        y1 = center_px[1] - roi_size_px[1] // 2
        x2 = x1 + roi_size_px[0]
        y2 = y1 + roi_size_px[1]

        return (x1, y1, x2, y2)