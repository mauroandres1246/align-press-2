#!/usr/bin/env python3
"""
CLI tool for testing the logo detector.

This script allows testing the detector with static images or live camera feed,
providing detailed output and debug visualizations.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

import cv2
import yaml
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.detector import PlanarLogoDetector
from ..core.schemas import DetectorConfigSchema, LogoResultSchema
from ..utils.image_utils import draw_detection_overlay


console = Console()


def load_config(config_path: Path) -> DetectorConfigSchema:
    """
    Load detector configuration from file.

    Args:
        config_path: Path to configuration file (YAML or JSON)

    Returns:
        Validated detector configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_dict = yaml.safe_load(f)
            else:
                config_dict = json.load(f)

        return DetectorConfigSchema(**config_dict)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON configuration: {e}")
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def load_image(image_path: Path) -> np.ndarray:
    """
    Load image from file.

    Args:
        image_path: Path to image file

    Returns:
        Loaded image in BGR format

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    return image


def load_homography(homography_path: Optional[Path]) -> Optional[np.ndarray]:
    """
    Load homography matrix from file.

    Args:
        homography_path: Path to homography file (JSON)

    Returns:
        Homography matrix or None if not provided

    Raises:
        FileNotFoundError: If homography file doesn't exist
        ValueError: If homography is invalid
    """
    if homography_path is None:
        return None

    if not homography_path.exists():
        raise FileNotFoundError(f"Homography file not found: {homography_path}")

    try:
        with open(homography_path, 'r') as f:
            data = json.load(f)

        if 'homography' not in data:
            raise ValueError("Homography matrix not found in file")

        H = np.array(data['homography'], dtype=np.float32)
        if H.shape != (3, 3):
            raise ValueError(f"Invalid homography shape: {H.shape}")

        return H

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in homography file: {e}")


def create_debug_image(
    image: np.ndarray,
    results: list[LogoResultSchema],
    detector: PlanarLogoDetector
) -> np.ndarray:
    """
    Create debug image with detection overlays.

    Args:
        image: Original input image
        results: Detection results
        detector: Detector instance for expected positions

    Returns:
        Image with debug overlays
    """
    debug_img = image.copy()
    expected_positions = detector.get_expected_positions_px()

    for result in results:
        if result.logo_name not in expected_positions:
            continue

        expected_pos = expected_positions[result.logo_name]

        if result.found and result.position_mm is not None:
            # Convert detected position to pixels
            detected_px = (
                int(result.position_mm[0] / detector.config.plane.mm_per_px),
                int(result.position_mm[1] / detector.config.plane.mm_per_px)
            )

            # Draw overlay
            debug_img = draw_detection_overlay(
                debug_img,
                detected_px,
                expected_pos,
                result.deviation_mm or 0.0,
                result.angle_deg or 0.0,
                detector.config.thresholds.position_tolerance_mm,
                detector.config.thresholds.angle_tolerance_deg
            )
        else:
            # Draw expected position only (red X)
            cv2.drawMarker(debug_img, expected_pos, (0, 0, 255),
                          cv2.MARKER_TILTED_CROSS, 20, 3)

        # Draw ROI bounds
        roi_bounds = detector.get_roi_bounds_px(result.logo_name)
        if roi_bounds:
            x1, y1, x2, y2 = roi_bounds
            cv2.rectangle(debug_img, (x1, y1), (x2, y2), (255, 255, 0), 2)

    return debug_img


def print_results_table(results: list[LogoResultSchema], verbose: bool = False) -> None:
    """
    Print detection results in a formatted table.

    Args:
        results: Detection results
        verbose: Whether to show detailed information
    """
    table = Table(title="Detection Results")

    # Add columns
    table.add_column("Logo", style="cyan", no_wrap=True)
    table.add_column("Found", justify="center")
    table.add_column("Position (mm)", justify="center")
    table.add_column("Deviation (mm)", justify="center")
    table.add_column("Angle (°)", justify="center")
    table.add_column("Status", justify="center")

    if verbose:
        table.add_column("Confidence", justify="center")
        table.add_column("Inliers", justify="center")
        table.add_column("Method", justify="center")

    # Add rows
    for result in results:
        # Status styling
        if result.found:
            if result.is_within_tolerance:
                status = "[green]✓ OK[/green]"
                found_text = "[green]✓[/green]"
            else:
                status = "[yellow]⚠ ADJUST[/yellow]"
                found_text = "[yellow]✓[/yellow]"
        else:
            status = "[red]✗ NOT FOUND[/red]"
            found_text = "[red]✗[/red]"

        # Format position
        if result.position_mm:
            pos_text = f"({result.position_mm[0]:.1f}, {result.position_mm[1]:.1f})"
        else:
            pos_text = "—"

        # Format deviation
        dev_text = f"{result.deviation_mm:.1f}" if result.deviation_mm is not None else "—"

        # Format angle
        angle_text = f"{result.angle_deg:.1f}" if result.angle_deg is not None else "—"

        row = [
            result.logo_name,
            found_text,
            pos_text,
            dev_text,
            angle_text,
            status
        ]

        if verbose:
            conf_text = f"{result.confidence:.3f}" if result.confidence is not None else "—"
            inliers_text = str(result.inliers) if result.inliers is not None else "—"
            method_text = result.method_used or "—"

            row.extend([conf_text, inliers_text, method_text])

        table.add_row(*row)

    console.print(table)


def print_summary(results: list[LogoResultSchema]) -> None:
    """
    Print detection summary.

    Args:
        results: Detection results
    """
    total = len(results)
    found = sum(1 for r in results if r.found)
    ok = sum(1 for r in results if r.found and r.is_within_tolerance)
    adjust = sum(1 for r in results if r.found and not r.is_within_tolerance)

    console.print(f"\n[bold]SUMMARY[/bold]: {found}/{total} logos detected, "
                 f"{ok}/{total} OK, {adjust}/{total} require adjustment")


def test_single_image(args) -> int:
    """
    Test detector on a single image.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        console.print("[bold blue]Loading configuration...[/bold blue]")
        config = load_config(Path(args.config))

        console.print("[bold blue]Initializing detector...[/bold blue]")
        detector = PlanarLogoDetector(config)

        console.print(f"[green]✓[/green] Detector initialized: {len(config.logos)} logos, "
                     f"{config.features.feature_type} with {config.features.nfeatures} features")

        console.print(f"[bold blue]Loading image: {args.image}[/bold blue]")
        image = load_image(Path(args.image))

        # Load homography if provided
        homography = None
        if args.homography:
            console.print(f"[bold blue]Loading homography: {args.homography}[/bold blue]")
            homography = load_homography(Path(args.homography))

        # Run detection
        console.print("[bold blue]Running detection...[/bold blue]")
        start_time = time.time()
        results = detector.detect_logos(image, homography)
        detection_time = (time.time() - start_time) * 1000

        # Print results
        if args.verbose:
            console.print(f"\n[dim]Detection completed in {detection_time:.1f}ms[/dim]")

        print_results_table(results, args.verbose)
        print_summary(results)

        # Save debug image if requested
        if args.save_debug:
            console.print(f"\n[bold blue]Creating debug image...[/bold blue]")
            debug_img = create_debug_image(image, results, detector)

            debug_path = Path(args.save_debug)
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_path), debug_img)
            console.print(f"[green]✓[/green] Debug image saved: {debug_path}")

        # Save JSON results if requested
        if args.save_json:
            json_data = {
                "detection_time_ms": detection_time,
                "results": [result.dict() for result in results]
            }

            json_path = Path(args.save_json)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            console.print(f"[green]✓[/green] JSON results saved: {json_path}")

        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def test_camera_live(args) -> int:
    """
    Test detector with live camera feed.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    try:
        console.print("[bold blue]Loading configuration...[/bold blue]")
        config = load_config(Path(args.config))

        console.print("[bold blue]Initializing detector...[/bold blue]")
        detector = PlanarLogoDetector(config)

        console.print(f"[bold blue]Opening camera {args.camera}...[/bold blue]")
        cap = cv2.VideoCapture(args.camera)

        if not cap.isOpened():
            console.print(f"[red]Error: Could not open camera {args.camera}[/red]")
            return 1

        # Set FPS if specified
        if args.fps:
            cap.set(cv2.CAP_PROP_FPS, args.fps)

        console.print("[green]✓[/green] Camera opened. Press 'q' to quit, 's' to save snapshot")

        frame_count = 0
        fps_timer = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                console.print("[red]Error: Could not read frame from camera[/red]")
                break

            # Run detection
            start_time = time.time()
            results = detector.detect_logos(frame)
            detection_time = (time.time() - start_time) * 1000

            # Create display image
            display_img = create_debug_image(frame, results, detector)

            # Add FPS and timing info
            frame_count += 1
            if frame_count % 30 == 0:
                current_fps = 30 / (time.time() - fps_timer)
                fps_timer = time.time()
            else:
                current_fps = 0

            if current_fps > 0:
                cv2.putText(display_img, f"FPS: {current_fps:.1f}",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.putText(display_img, f"Detection: {detection_time:.1f}ms",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Show results in console (periodically)
            if args.verbose and frame_count % 30 == 0:
                console.clear()
                print_results_table(results, verbose=False)

            # Display image
            if args.show:
                cv2.imshow('Align-Press Live Detection', display_img)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s') and args.save_debug:
                    # Save snapshot
                    timestamp = int(time.time())
                    snapshot_path = Path(args.save_debug).parent / f"snapshot_{timestamp}.jpg"
                    cv2.imwrite(str(snapshot_path), display_img)
                    console.print(f"[green]✓[/green] Snapshot saved: {snapshot_path}")

        cap.release()
        if args.show:
            cv2.destroyAllWindows()

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the Align-Press logo detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with static image
  python -m alignpress.cli.test_detector \\
    --config config/example_detector.yaml \\
    --image datasets/test_001.jpg \\
    --save-debug output/debug_001.jpg \\
    --verbose

  # Test with live camera
  python -m alignpress.cli.test_detector \\
    --config config/example_detector.yaml \\
    --camera 0 \\
    --show \\
    --fps 30
        """
    )

    # Configuration
    parser.add_argument(
        '--config', '-c',
        type=str,
        required=True,
        help='Path to detector configuration file (YAML or JSON)'
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--image', '-i',
        type=str,
        help='Path to input image file'
    )
    input_group.add_argument(
        '--camera',
        type=int,
        help='Camera device ID (usually 0)'
    )

    # Optional inputs
    parser.add_argument(
        '--homography',
        type=str,
        help='Path to homography calibration file (JSON)'
    )

    # Output options
    parser.add_argument(
        '--save-debug',
        type=str,
        help='Path to save debug image with overlays'
    )
    parser.add_argument(
        '--save-json',
        type=str,
        help='Path to save results as JSON'
    )

    # Camera options
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show live video window (camera mode only)'
    )
    parser.add_argument(
        '--fps',
        type=int,
        help='Target FPS for camera capture'
    )

    # Output options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output with detailed metrics'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )

    args = parser.parse_args()

    # Handle quiet mode
    if args.quiet:
        console.quiet = True

    # Validate arguments
    if args.camera is not None and not args.show and not args.verbose:
        console.print("[yellow]Warning: Camera mode without --show or --verbose may not display results[/yellow]")

    # Run appropriate test mode
    if args.image:
        return test_single_image(args)
    else:
        return test_camera_live(args)


if __name__ == '__main__':
    sys.exit(main())