#!/usr/bin/env python3
"""
Calibration tool for static images.

This script performs camera calibration using a single static image
with a chessboard pattern, specifically designed for platen calibration.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import cv2
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class StaticImageCalibrator:
    """Calibrate using a single static image with chessboard pattern."""

    def __init__(self, image_path: Path, pattern_size: Tuple[int, int], square_size_mm: float):
        """
        Initialize calibrator.

        Args:
            image_path: Path to calibration image
            pattern_size: Chessboard pattern size (width, height) in corners
            square_size_mm: Size of chessboard squares in millimeters
        """
        self.image_path = image_path
        self.pattern_size = pattern_size
        self.square_size_mm = square_size_mm

        # Results
        self.homography: Optional[np.ndarray] = None
        self.mm_per_px: Optional[float] = None
        self.quality_metrics: Dict[str, Any] = {}
        self.image: Optional[np.ndarray] = None
        self.corners: Optional[np.ndarray] = None

    def load_image(self) -> bool:
        """Load and validate calibration image."""
        try:
            if not self.image_path.exists():
                console.print(f"❌ Image not found: {self.image_path}")
                return False

            self.image = cv2.imread(str(self.image_path))
            if self.image is None:
                console.print(f"❌ Failed to load image: {self.image_path}")
                return False

            height, width = self.image.shape[:2]
            console.print(f"📷 Loaded image: {width}x{height} pixels")
            return True

        except Exception as e:
            console.print(f"❌ Error loading image: {e}")
            return False

    def detect_chessboard(self) -> bool:
        """Detect chessboard pattern in the image."""
        if self.image is None:
            return False

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)

        console.print(f"🔍 Detecting chessboard pattern {self.pattern_size[0]}x{self.pattern_size[1]}...")

        # Enhanced chessboard detection
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # Try different flags for robustness
        flags = [
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK,
            cv2.CALIB_CB_ADAPTIVE_THRESH,
            cv2.CALIB_CB_NORMALIZE_IMAGE
        ]

        found = False
        corners = None

        for flag in flags:
            found, corners = cv2.findChessboardCorners(gray, self.pattern_size, flag)
            if found:
                console.print(f"✅ Pattern detected with flag {flag}")
                break

        if not found:
            console.print("❌ Chessboard pattern not detected")
            console.print("💡 Troubleshooting tips:")
            console.print("   - Ensure pattern is clearly visible")
            console.print("   - Check pattern size matches configuration")
            console.print("   - Improve lighting and focus")
            console.print("   - Ensure pattern is not distorted")
            return False

        # Refine corner positions
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        self.corners = corners

        console.print(f"✅ Detected {len(corners)} corners")
        return True

    def calculate_homography(self) -> bool:
        """Calculate homography matrix from detected corners."""
        if self.corners is None:
            return False

        # Create object points (real world coordinates in mm)
        # Pattern is on a plane, so Z=0 for all points
        objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
        objp *= self.square_size_mm

        # Convert corners to appropriate format
        image_points = self.corners.reshape(-1, 2)
        object_points = objp[:, :2]  # Only X,Y coordinates for homography

        try:
            # Calculate homography
            self.homography, mask = cv2.findHomography(
                image_points,
                object_points,
                cv2.RANSAC,
                5.0  # RANSAC threshold
            )

            if self.homography is None:
                console.print("❌ Failed to calculate homography")
                return False

            # Calculate scale factor (mm per pixel)
            # Use the average distance between adjacent corners
            distances_px = []
            distances_mm = []

            for i in range(len(image_points) - 1):
                for j in range(i + 1, len(image_points)):
                    # Distance in pixels
                    dist_px = np.linalg.norm(image_points[i] - image_points[j])
                    # Corresponding distance in mm
                    dist_mm = np.linalg.norm(object_points[i] - object_points[j])

                    if dist_px > 10:  # Avoid very close points
                        distances_px.append(dist_px)
                        distances_mm.append(dist_mm)

            if distances_px:
                mm_per_px_values = np.array(distances_mm) / np.array(distances_px)
                self.mm_per_px = float(np.median(mm_per_px_values))
            else:
                # Fallback calculation
                self.mm_per_px = self.square_size_mm / np.mean([
                    np.linalg.norm(image_points[1] - image_points[0]),
                    np.linalg.norm(image_points[self.pattern_size[0]] - image_points[0])
                ])

            console.print(f"✅ Homography calculated")
            console.print(f"📏 Scale factor: {self.mm_per_px:.3f} mm/pixel")

            return True

        except Exception as e:
            console.print(f"❌ Error calculating homography: {e}")
            return False

    def calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate calibration quality metrics."""
        if self.homography is None or self.corners is None:
            return {}

        # Reprojection error
        objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
        objp *= self.square_size_mm

        # Project object points back to image
        object_points_2d = objp[:, :2].reshape(-1, 1, 2).astype(np.float32)
        projected_points = cv2.perspectiveTransform(
            object_points_2d,
            np.linalg.inv(self.homography)
        )

        # Calculate reprojection error
        image_points = self.corners.reshape(-1, 2)
        projected_points = projected_points.reshape(-1, 2)

        errors = np.linalg.norm(image_points - projected_points, axis=1)
        mean_error = float(np.mean(errors))
        max_error = float(np.max(errors))

        # Additional metrics
        corners_detected = len(self.corners)
        corners_expected = self.pattern_size[0] * self.pattern_size[1]
        detection_rate = corners_detected / corners_expected

        metrics = {
            "reproj_error_px": mean_error,
            "max_reproj_error_px": max_error,
            "corners_detected": corners_detected,
            "corners_expected": corners_expected,
            "detection_rate": detection_rate,
            "pattern_size": self.pattern_size,
            "square_size_mm": self.square_size_mm,
            "mm_per_px": self.mm_per_px
        }

        self.quality_metrics = metrics
        return metrics

    def save_calibration(self, output_path: Path) -> bool:
        """Save calibration data to JSON file."""
        if self.homography is None:
            return False

        try:
            calibration_data = {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "source_image": str(self.image_path),
                "homography": self.homography.tolist(),
                "mm_per_px": self.mm_per_px,
                "pattern_info": {
                    "type": "chessboard",
                    "size": self.pattern_size,
                    "square_size_mm": self.square_size_mm
                },
                "quality_metrics": self.quality_metrics
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(calibration_data, f, indent=2)

            console.print(f"💾 Calibration saved to: {output_path}")
            return True

        except Exception as e:
            console.print(f"❌ Error saving calibration: {e}")
            return False

    def save_debug_image(self, output_path: Path) -> bool:
        """Save debug image with detected corners."""
        if self.image is None or self.corners is None:
            return False

        try:
            debug_image = self.image.copy()

            # Draw detected corners
            cv2.drawChessboardCorners(
                debug_image,
                self.pattern_size,
                self.corners,
                True
            )

            # Add text information
            height, width = debug_image.shape[:2]
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            color = (0, 255, 0)
            thickness = 2

            info_text = [
                f"Pattern: {self.pattern_size[0]}x{self.pattern_size[1]}",
                f"Square size: {self.square_size_mm}mm",
                f"Scale: {self.mm_per_px:.3f} mm/px",
                f"Reproj error: {self.quality_metrics.get('reproj_error_px', 0):.2f}px"
            ]

            for i, text in enumerate(info_text):
                y = 30 + i * 30
                cv2.putText(debug_image, text, (10, y), font, font_scale, color, thickness)

            cv2.imwrite(str(output_path), debug_image)
            console.print(f"🖼️ Debug image saved to: {output_path}")
            return True

        except Exception as e:
            console.print(f"❌ Error saving debug image: {e}")
            return False

    def run_calibration(self, output_path: Path, debug_image_path: Path = None) -> bool:
        """Run complete calibration process."""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Load image
            task = progress.add_task("Loading image...", total=None)
            if not self.load_image():
                return False
            progress.update(task, description="✅ Image loaded")

            # Detect pattern
            progress.update(task, description="Detecting chessboard pattern...")
            if not self.detect_chessboard():
                return False
            progress.update(task, description="✅ Pattern detected")

            # Calculate homography
            progress.update(task, description="Calculating homography...")
            if not self.calculate_homography():
                return False
            progress.update(task, description="✅ Homography calculated")

            # Calculate quality metrics
            progress.update(task, description="Calculating quality metrics...")
            self.calculate_quality_metrics()
            progress.update(task, description="✅ Quality metrics calculated")

            # Save results
            progress.update(task, description="Saving calibration data...")
            if not self.save_calibration(output_path):
                return False

            if debug_image_path:
                self.save_debug_image(debug_image_path)

            progress.update(task, description="✅ Calibration complete")

        return True

    def print_results(self):
        """Print calibration results in a formatted table."""
        if not self.quality_metrics:
            return

        # Main results table
        table = Table(title="Calibration Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Quality", style="green")

        # Scale factor
        mm_per_px = self.quality_metrics.get('mm_per_px', 0)
        scale_quality = "Good" if 0.2 <= mm_per_px <= 0.8 else "Check"
        table.add_row("Scale Factor", f"{mm_per_px:.3f} mm/pixel", scale_quality)

        # Reprojection error
        reproj_error = self.quality_metrics.get('reproj_error_px', 0)
        error_quality = "Excellent" if reproj_error < 1.0 else "Good" if reproj_error < 2.0 else "Poor"
        table.add_row("Reprojection Error", f"{reproj_error:.2f} pixels", error_quality)

        # Detection rate
        detection_rate = self.quality_metrics.get('detection_rate', 0)
        detection_quality = "Perfect" if detection_rate == 1.0 else "Good" if detection_rate > 0.9 else "Poor"
        table.add_row("Pattern Detection", f"{detection_rate*100:.1f}%", detection_quality)

        # Corner count
        corners_detected = self.quality_metrics.get('corners_detected', 0)
        corners_expected = self.quality_metrics.get('corners_expected', 0)
        table.add_row("Corners Found", f"{corners_detected}/{corners_expected}", "✅")

        console.print(table)

        # Overall quality assessment
        overall_quality = "Good"
        if reproj_error > 2.0 or detection_rate < 0.9:
            overall_quality = "Poor - Consider retaking calibration image"
        elif reproj_error < 1.0 and detection_rate == 1.0:
            overall_quality = "Excellent"

        console.print(f"\n📊 Overall Quality: {overall_quality}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Calibrate using static image with chessboard pattern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic calibration
  python calibrate_from_image.py \\
    --image datasets/calibration/platen_with_chessboard.jpg \\
    --pattern-size 9 6 \\
    --square-size-mm 25.0 \\
    --output calibration/platen_50x60/calibration.json

  # With debug image
  python calibrate_from_image.py \\
    --image datasets/calibration/platen_with_chessboard.jpg \\
    --pattern-size 9 6 \\
    --square-size-mm 25.0 \\
    --output calibration/platen_50x60/calibration.json \\
    --debug-image calibration/platen_50x60/calibration_debug.jpg
        """
    )

    parser.add_argument(
        '--image', '-i',
        type=Path,
        required=True,
        help='Path to calibration image with chessboard pattern'
    )

    parser.add_argument(
        '--pattern-size',
        type=int,
        nargs=2,
        required=True,
        metavar=('WIDTH', 'HEIGHT'),
        help='Chessboard pattern size in internal corners (e.g., 9 6)'
    )

    parser.add_argument(
        '--square-size-mm',
        type=float,
        required=True,
        help='Size of chessboard squares in millimeters'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        required=True,
        help='Output path for calibration JSON file'
    )

    parser.add_argument(
        '--debug-image',
        type=Path,
        help='Optional: Save debug image with detected corners'
    )

    args = parser.parse_args()

    # Welcome message
    console.print(Panel(
        "🎯 Align-Press v2 - Static Image Calibration",
        subtitle=f"Pattern: {args.pattern_size[0]}x{args.pattern_size[1]}, Square: {args.square_size_mm}mm"
    ))

    # Create calibrator
    calibrator = StaticImageCalibrator(
        args.image,
        tuple(args.pattern_size),
        args.square_size_mm
    )

    # Run calibration
    success = calibrator.run_calibration(args.output, args.debug_image)

    if success:
        calibrator.print_results()
        console.print(Panel(
            "✅ Calibration completed successfully!",
            style="green"
        ))
        return 0
    else:
        console.print(Panel(
            "❌ Calibration failed. Check image and pattern parameters.",
            style="red"
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())