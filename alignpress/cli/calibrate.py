#!/usr/bin/env python3
"""
CLI tool for camera calibration.

This script provides interactive camera calibration using chessboard patterns,
calculating homography matrices and scale factors for logo detection.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, FloatPrompt, IntPrompt
from rich.table import Table

from ..core.schemas import CalibrationDataSchema

console = Console()


class CameraCalibrator:
    """
    Interactive camera calibrator using chessboard patterns.
    """

    def __init__(self, camera_id: int, pattern_size: Tuple[int, int], square_size_mm: float):
        """
        Initialize calibrator.

        Args:
            camera_id: Camera device ID
            pattern_size: Chessboard pattern size (width, height) in corners
            square_size_mm: Size of chessboard squares in millimeters
        """
        self.camera_id = camera_id
        self.pattern_size = pattern_size
        self.square_size_mm = square_size_mm
        self.cap: Optional[cv2.VideoCapture] = None

        # Calibration data
        self.captured_frames: List[np.ndarray] = []
        self.captured_corners: List[np.ndarray] = []
        self.image_size: Optional[Tuple[int, int]] = None

        # Results
        self.homography: Optional[np.ndarray] = None
        self.mm_per_px: Optional[float] = None
        self.quality_metrics: dict = {}

    def open_camera(self) -> bool:
        """
        Open camera connection.

        Returns:
            True if camera opened successfully
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                return False

            # Set camera properties for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)

            return True

        except Exception:
            return False

    def close_camera(self) -> None:
        """Close camera connection."""
        if self.cap:
            self.cap.release()
            cv2.destroyAllWindows()

    def detect_chessboard(self, image: np.ndarray) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Detect chessboard corners in image.

        Args:
            image: Input image

        Returns:
            Tuple of (found, corners)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Find chessboard corners
        found, corners = cv2.findChessboardCorners(
            gray,
            self.pattern_size,
            cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK
        )

        if found:
            # Refine corner detection
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        return found, corners

    def preview_calibration(self, show_preview: bool = True) -> bool:
        """
        Run preview mode to capture calibration images.

        Args:
            show_preview: Whether to show camera preview window

        Returns:
            True if calibration data was captured successfully
        """
        if not self.cap:
            console.print("[red]Error: Camera not opened[/red]")
            return False

        console.print(f"\n[bold blue]📷 Calibration Preview Mode[/bold blue]")
        console.print(f"Pattern: {self.pattern_size[0]}x{self.pattern_size[1]} chessboard")
        console.print(f"Square size: {self.square_size_mm}mm")
        console.print("\n[yellow]Instructions:[/yellow]")
        console.print("• Position chessboard pattern in camera view")
        console.print("• Press SPACE to capture when pattern is detected")
        console.print("• Capture from different angles and positions")
        console.print("• Press 'q' to finish calibration")
        console.print("• Minimum 5 captures recommended\n")

        captured_count = 0
        target_captures = 10

        while True:
            ret, frame = self.cap.read()
            if not ret:
                console.print("[red]Error: Could not read frame from camera[/red]")
                return False

            # Store image size
            if self.image_size is None:
                h, w = frame.shape[:2]
                self.image_size = (w, h)

            # Detect chessboard
            found, corners = self.detect_chessboard(frame)

            # Draw visualization
            display_frame = frame.copy()

            if found:
                # Draw detected corners
                cv2.drawChessboardCorners(display_frame, self.pattern_size, corners, found)

                # Add status text
                cv2.putText(display_frame, "PATTERN DETECTED - Press SPACE to capture",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "Position chessboard pattern in view",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Add capture count
            cv2.putText(display_frame, f"Captured: {captured_count}/{target_captures}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.putText(display_frame, "Press 'q' to finish, SPACE to capture",
                       (10, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Show preview if requested
            if show_preview:
                cv2.imshow('Camera Calibration', display_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break
            elif key == ord(' ') and found:
                # Capture frame
                self.captured_frames.append(frame.copy())
                self.captured_corners.append(corners)
                captured_count += 1

                console.print(f"[green]✓[/green] Captured frame {captured_count}")

                if captured_count >= target_captures:
                    console.print(f"\n[green]🎉 Captured {captured_count} frames. Press 'q' to finish.[/green]")

        cv2.destroyAllWindows()

        if captured_count < 3:
            console.print(f"[red]Error: Need at least 3 captures, got {captured_count}[/red]")
            return False

        console.print(f"\n[green]✓[/green] Calibration capture completed: {captured_count} frames")
        return True

    def calculate_calibration(self) -> bool:
        """
        Calculate homography and scale from captured data.

        Returns:
            True if calibration was successful
        """
        if len(self.captured_frames) < 3:
            console.print("[red]Error: Need at least 3 captured frames[/red]")
            return False

        console.print("\n[bold blue]📐 Calculating calibration...[/bold blue]")

        try:
            # Prepare object points (3D points in real world space)
            objp = np.zeros((self.pattern_size[0] * self.pattern_size[1], 3), np.float32)
            objp[:, :2] = np.mgrid[0:self.pattern_size[0], 0:self.pattern_size[1]].T.reshape(-1, 2)
            objp *= self.square_size_mm

            # Prepare arrays for calibration
            object_points = [objp for _ in self.captured_frames]
            image_points = self.captured_corners

            # Camera calibration to get intrinsic parameters
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                object_points, image_points, self.image_size, None, None
            )

            if not ret:
                console.print("[red]Error: Camera calibration failed[/red]")
                return False

            # Calculate reprojection error
            total_error = 0
            for i in range(len(object_points)):
                imgpoints2, _ = cv2.projectPoints(object_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
                error = cv2.norm(image_points[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                total_error += error

            mean_error = total_error / len(object_points)

            # For planar objects, we can use the first capture to calculate homography
            # This assumes the pattern defines our "world" coordinate system
            object_points_2d = objp[:, :2].reshape(-1, 1, 2)
            image_points_2d = image_points[0]

            # Calculate homography from pattern coordinates to image coordinates
            self.homography, mask = cv2.findHomography(
                object_points_2d, image_points_2d, cv2.RANSAC, 5.0
            )

            if self.homography is None:
                console.print("[red]Error: Could not calculate homography[/red]")
                return False

            # Calculate scale factor (mm per pixel)
            # Use the distance between two adjacent corners
            corner1 = image_points_2d[0][0]
            corner2 = image_points_2d[1][0]
            pixel_distance = np.linalg.norm(corner2 - corner1)
            self.mm_per_px = self.square_size_mm / pixel_distance

            # Quality metrics
            inliers = np.sum(mask) if mask is not None else len(image_points_2d)
            self.quality_metrics = {
                "reproj_error_px": float(mean_error),
                "corners_detected": int(inliers),
                "corners_expected": int(len(image_points_2d)),
                "captures_used": len(self.captured_frames),
                "homography_condition": float(np.linalg.cond(self.homography)),
                "scale_consistency": self._check_scale_consistency()
            }

            console.print(f"[green]✓[/green] Calibration successful!")
            self._print_calibration_results()

            return True

        except Exception as e:
            console.print(f"[red]Error during calibration calculation: {e}[/red]")
            return False

    def _check_scale_consistency(self) -> float:
        """
        Check scale consistency across multiple corner pairs.

        Returns:
            Scale consistency metric (lower is better)
        """
        if len(self.captured_corners) == 0:
            return float('inf')

        scales = []
        corners = self.captured_corners[0]

        # Check scale for multiple corner pairs
        for i in range(min(10, len(corners) - 1)):
            corner1 = corners[i][0]
            corner2 = corners[i + 1][0]
            pixel_dist = np.linalg.norm(corner2 - corner1)
            if pixel_dist > 0:
                scale = self.square_size_mm / pixel_dist
                scales.append(scale)

        if len(scales) < 2:
            return 0.0

        # Return coefficient of variation
        return float(np.std(scales) / np.mean(scales))

    def _print_calibration_results(self) -> None:
        """Print calibration results in a formatted table."""
        table = Table(title="Calibration Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", justify="center")

        # Add metrics
        metrics = [
            ("Scale (mm/px)", f"{self.mm_per_px:.4f}", "✓"),
            ("Reprojection Error", f"{self.quality_metrics['reproj_error_px']:.2f} px",
             "✓" if self.quality_metrics['reproj_error_px'] < 2.0 else "⚠"),
            ("Corners Detected", f"{self.quality_metrics['corners_detected']}/{self.quality_metrics['corners_expected']}",
             "✓" if self.quality_metrics['corners_detected'] == self.quality_metrics['corners_expected'] else "⚠"),
            ("Captures Used", f"{self.quality_metrics['captures_used']}", "✓"),
            ("Scale Consistency", f"{self.quality_metrics['scale_consistency']:.4f}",
             "✓" if self.quality_metrics['scale_consistency'] < 0.05 else "⚠"),
        ]

        for metric, value, status in metrics:
            table.add_row(metric, value, status)

        console.print(table)

    def save_calibration(self, output_path: Path, camera_id: int) -> bool:
        """
        Save calibration data to JSON file.

        Args:
            output_path: Path to save calibration file
            camera_id: Camera identifier

        Returns:
            True if saved successfully
        """
        if self.homography is None or self.mm_per_px is None:
            console.print("[red]Error: No calibration data to save[/red]")
            return False

        try:
            # Create calibration schema
            calibration_data = CalibrationDataSchema(
                camera_id=camera_id,
                homography=self.homography.tolist(),
                mm_per_px=self.mm_per_px,
                pattern_info={
                    "type": "chessboard",
                    "size": list(self.pattern_size),
                    "square_size_mm": self.square_size_mm
                },
                quality_metrics=self.quality_metrics
            )

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to JSON
            with open(output_path, 'w') as f:
                json.dump(calibration_data.dict(), f, indent=2, default=str)

            console.print(f"[green]✓[/green] Calibration saved: {output_path}")
            return True

        except Exception as e:
            console.print(f"[red]Error saving calibration: {e}[/red]")
            return False

    def validate_calibration(self) -> bool:
        """
        Validate calibration quality.

        Returns:
            True if calibration meets quality standards
        """
        if not self.quality_metrics:
            return False

        # Quality thresholds
        max_reproj_error = 2.0
        min_detection_rate = 0.8
        max_scale_variation = 0.05

        issues = []

        # Check reprojection error
        if self.quality_metrics['reproj_error_px'] > max_reproj_error:
            issues.append(f"High reprojection error: {self.quality_metrics['reproj_error_px']:.2f}px > {max_reproj_error}px")

        # Check corner detection rate
        detection_rate = self.quality_metrics['corners_detected'] / self.quality_metrics['corners_expected']
        if detection_rate < min_detection_rate:
            issues.append(f"Low corner detection rate: {detection_rate:.1%} < {min_detection_rate:.1%}")

        # Check scale consistency
        if self.quality_metrics['scale_consistency'] > max_scale_variation:
            issues.append(f"Inconsistent scale: {self.quality_metrics['scale_consistency']:.4f} > {max_scale_variation}")

        if issues:
            console.print("\n[yellow]⚠ Calibration Quality Issues:[/yellow]")
            for issue in issues:
                console.print(f"  • {issue}")
            console.print("\nRecommendation: Recalibrate with better lighting and pattern positioning")
            return False
        else:
            console.print("\n[green]✓ Calibration quality is good![/green]")
            return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive camera calibration for Align-Press",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic calibration
  python -m alignpress.cli.calibrate \\
    --camera 0 \\
    --pattern-size 9 6 \\
    --square-size-mm 25.0 \\
    --output calibration/camera_0/homography.json

  # Calibration without preview (headless)
  python -m alignpress.cli.calibrate \\
    --camera 0 \\
    --pattern-size 9 6 \\
    --square-size-mm 25.0 \\
    --output calibration/camera_0/homography.json \\
    --no-preview
        """
    )

    # Required arguments
    parser.add_argument(
        '--camera', '-c',
        type=int,
        required=True,
        help='Camera device ID (usually 0)'
    )

    parser.add_argument(
        '--pattern-size',
        type=int,
        nargs=2,
        required=True,
        metavar=('WIDTH', 'HEIGHT'),
        help='Chessboard pattern size (width height) in inner corners'
    )

    parser.add_argument(
        '--square-size-mm',
        type=float,
        required=True,
        help='Size of chessboard squares in millimeters'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='Output path for calibration file (JSON)'
    )

    # Optional arguments
    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Run without showing camera preview window'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing calibration file'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.pattern_size[0] < 3 or args.pattern_size[1] < 3:
        console.print("[red]Error: Pattern size must be at least 3x3[/red]")
        return 1

    if args.square_size_mm <= 0:
        console.print("[red]Error: Square size must be positive[/red]")
        return 1

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        if not Confirm.ask(f"Calibration file exists: {output_path}. Overwrite?"):
            console.print("[yellow]Calibration cancelled[/yellow]")
            return 0

    # Initialize calibrator
    console.print("[bold blue]🎯 Align-Press Camera Calibration[/bold blue]")
    console.print(f"Camera: {args.camera}")
    console.print(f"Pattern: {args.pattern_size[0]}x{args.pattern_size[1]} chessboard")
    console.print(f"Square size: {args.square_size_mm}mm")

    calibrator = CameraCalibrator(
        camera_id=args.camera,
        pattern_size=tuple(args.pattern_size),
        square_size_mm=args.square_size_mm
    )

    try:
        # Open camera
        console.print("\n[bold blue]📷 Opening camera...[/bold blue]")
        if not calibrator.open_camera():
            console.print(f"[red]Error: Could not open camera {args.camera}[/red]")
            return 1

        console.print("[green]✓[/green] Camera opened successfully")

        # Run calibration preview
        if not calibrator.preview_calibration(show_preview=not args.no_preview):
            console.print("[red]Error: Calibration preview failed[/red]")
            return 1

        # Calculate calibration
        if not calibrator.calculate_calibration():
            console.print("[red]Error: Calibration calculation failed[/red]")
            return 1

        # Validate quality
        calibrator.validate_calibration()

        # Save calibration
        if not calibrator.save_calibration(output_path, args.camera):
            console.print("[red]Error: Failed to save calibration[/red]")
            return 1

        console.print(f"\n[green]🎉 Calibration completed successfully![/green]")
        console.print(f"Calibration file: {output_path}")

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Calibration interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1
    finally:
        calibrator.close_camera()


if __name__ == '__main__':
    sys.exit(main())