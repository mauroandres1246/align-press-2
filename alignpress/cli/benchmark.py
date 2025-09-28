#!/usr/bin/env python3
"""
CLI tool for benchmarking detector performance.

This script runs performance benchmarks on the logo detector using datasets
of images, measuring timing, accuracy, and resource usage.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import statistics
import gc
import psutil
import os

import yaml
import cv2
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, track
from rich.panel import Panel

from ..core.detector import PlanarLogoDetector
from ..core.schemas import DetectorConfigSchema, LogoResultSchema

console = Console()


class PerformanceBenchmark:
    """
    Performance benchmark runner for the logo detector.
    """

    def __init__(self, config_path: Path):
        """
        Initialize benchmark.

        Args:
            config_path: Path to detector configuration
        """
        self.config_path = config_path
        self.detector: Optional[PlanarLogoDetector] = None
        self.results: List[Dict[str, Any]] = []
        self.system_info = self._get_system_info()

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for benchmark context."""
        return {
            "cpu_count": os.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "python_version": sys.version,
            "opencv_version": cv2.__version__ if hasattr(cv2, '__version__') else "unknown"
        }

    def load_detector(self) -> bool:
        """
        Load and initialize detector.

        Returns:
            True if detector loaded successfully
        """
        try:
            console.print(f"[bold blue]📦 Loading detector configuration: {self.config_path}[/bold blue]")

            with open(self.config_path, 'r') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    config_dict = yaml.safe_load(f)
                else:
                    config_dict = json.load(f)

            config = DetectorConfigSchema(**config_dict)
            self.detector = PlanarLogoDetector(config)

            console.print(f"[green]✓[/green] Detector loaded: {len(config.logos)} logos, "
                         f"{config.features.feature_type} with {config.features.nfeatures} features")

            return True

        except Exception as e:
            console.print(f"[red]Error loading detector: {e}[/red]")
            return False

    def load_dataset(self, dataset_path: Path) -> List[Path]:
        """
        Load dataset images.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            List of image file paths
        """
        if not dataset_path.exists():
            console.print(f"[red]Error: Dataset path does not exist: {dataset_path}[/red]")
            return []

        # Find image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        image_files = []

        if dataset_path.is_file():
            if dataset_path.suffix.lower() in image_extensions:
                image_files = [dataset_path]
        else:
            for ext in image_extensions:
                image_files.extend(dataset_path.glob(f"*{ext}"))
                image_files.extend(dataset_path.glob(f"*{ext.upper()}"))

        console.print(f"[green]✓[/green] Found {len(image_files)} images in dataset")
        return sorted(image_files)

    def benchmark_single_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Benchmark detector on a single image.

        Args:
            image_path: Path to image file

        Returns:
            Benchmark result dictionary
        """
        result = {
            "image": str(image_path),
            "success": False,
            "timing": {},
            "memory": {},
            "detection_results": [],
            "error": None
        }

        try:
            # Memory before loading
            process = psutil.Process()
            memory_before = process.memory_info().rss / (1024**2)  # MB

            # Load image
            load_start = time.time()
            image = cv2.imread(str(image_path))
            if image is None:
                result["error"] = "Could not load image"
                return result
            load_time = time.time() - load_start

            # Memory after loading
            memory_after_load = process.memory_info().rss / (1024**2)

            # Run detection
            detection_start = time.time()
            detection_results = self.detector.detect_logos(image)
            detection_time = time.time() - detection_start

            # Memory after detection
            memory_after_detection = process.memory_info().rss / (1024**2)

            # Store results
            result.update({
                "success": True,
                "timing": {
                    "load_ms": load_time * 1000,
                    "detection_ms": detection_time * 1000,
                    "total_ms": (load_time + detection_time) * 1000
                },
                "memory": {
                    "before_mb": memory_before,
                    "after_load_mb": memory_after_load,
                    "after_detection_mb": memory_after_detection,
                    "peak_usage_mb": memory_after_detection - memory_before
                },
                "detection_results": [r.dict() for r in detection_results],
                "image_size": {
                    "width": image.shape[1],
                    "height": image.shape[0],
                    "channels": image.shape[2] if len(image.shape) == 3 else 1
                }
            })

            # Force garbage collection
            del image
            gc.collect()

        except Exception as e:
            result["error"] = str(e)

        return result

    def run_benchmark(self, dataset_path: Path, samples: Optional[int] = None) -> bool:
        """
        Run full benchmark on dataset.

        Args:
            dataset_path: Path to dataset
            samples: Optional limit on number of samples to test

        Returns:
            True if benchmark completed successfully
        """
        if not self.detector:
            console.print("[red]Error: Detector not loaded[/red]")
            return False

        # Load dataset
        image_files = self.load_dataset(dataset_path)
        if not image_files:
            return False

        # Limit samples if specified
        if samples and samples < len(image_files):
            image_files = image_files[:samples]
            console.print(f"[yellow]Limiting benchmark to {samples} samples[/yellow]")

        console.print(f"\n[bold blue]🚀 Running benchmark on {len(image_files)} images[/bold blue]")

        # Run benchmark
        self.results = []
        for image_path in track(image_files, description="Benchmarking..."):
            result = self.benchmark_single_image(image_path)
            self.results.append(result)

        console.print(f"[green]✓[/green] Benchmark completed: {len(self.results)} images processed")
        return True

    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze benchmark results and generate statistics.

        Returns:
            Analysis results dictionary
        """
        if not self.results:
            return {}

        # Filter successful results
        successful_results = [r for r in self.results if r["success"]]
        failed_results = [r for r in self.results if not r["success"]]

        if not successful_results:
            return {"error": "No successful benchmark results"}

        # Timing statistics
        load_times = [r["timing"]["load_ms"] for r in successful_results]
        detection_times = [r["timing"]["detection_ms"] for r in successful_results]
        total_times = [r["timing"]["total_ms"] for r in successful_results]

        # Memory statistics
        peak_memory = [r["memory"]["peak_usage_mb"] for r in successful_results]

        # Detection statistics
        total_detections = 0
        successful_detections = 0
        detection_times_by_logo = {}

        for result in successful_results:
            for detection in result["detection_results"]:
                total_detections += 1
                if detection["found"]:
                    successful_detections += 1

                # Track timing by logo if available
                logo_name = detection["logo_name"]
                if "processing_time_ms" in detection:
                    if logo_name not in detection_times_by_logo:
                        detection_times_by_logo[logo_name] = []
                    detection_times_by_logo[logo_name].append(detection["processing_time_ms"])

        # Calculate FPS
        fps_values = [1000 / t for t in total_times if t > 0]

        analysis = {
            "summary": {
                "total_images": len(self.results),
                "successful_images": len(successful_results),
                "failed_images": len(failed_results),
                "success_rate": len(successful_results) / len(self.results) if self.results else 0
            },
            "timing": {
                "load_time_ms": {
                    "mean": statistics.mean(load_times),
                    "median": statistics.median(load_times),
                    "std": statistics.stdev(load_times) if len(load_times) > 1 else 0,
                    "min": min(load_times),
                    "max": max(load_times)
                },
                "detection_time_ms": {
                    "mean": statistics.mean(detection_times),
                    "median": statistics.median(detection_times),
                    "std": statistics.stdev(detection_times) if len(detection_times) > 1 else 0,
                    "min": min(detection_times),
                    "max": max(detection_times)
                },
                "total_time_ms": {
                    "mean": statistics.mean(total_times),
                    "median": statistics.median(total_times),
                    "std": statistics.stdev(total_times) if len(total_times) > 1 else 0,
                    "min": min(total_times),
                    "max": max(total_times)
                },
                "fps": {
                    "mean": statistics.mean(fps_values),
                    "median": statistics.median(fps_values),
                    "min": min(fps_values),
                    "max": max(fps_values)
                }
            },
            "memory": {
                "peak_usage_mb": {
                    "mean": statistics.mean(peak_memory),
                    "median": statistics.median(peak_memory),
                    "std": statistics.stdev(peak_memory) if len(peak_memory) > 1 else 0,
                    "min": min(peak_memory),
                    "max": max(peak_memory)
                }
            },
            "detection": {
                "total_detections": total_detections,
                "successful_detections": successful_detections,
                "detection_rate": successful_detections / total_detections if total_detections > 0 else 0,
                "detection_times_by_logo": {
                    logo: {
                        "mean": statistics.mean(times),
                        "count": len(times)
                    } for logo, times in detection_times_by_logo.items()
                }
            },
            "failures": [
                {"image": r["image"], "error": r["error"]}
                for r in failed_results
            ]
        }

        return analysis

    def print_analysis(self, analysis: Dict[str, Any]) -> None:
        """Print benchmark analysis in formatted tables."""
        if "error" in analysis:
            console.print(f"[red]Analysis error: {analysis['error']}[/red]")
            return

        # Summary panel
        summary = analysis["summary"]
        summary_text = (f"Images: {summary['total_images']} | "
                       f"Success: {summary['successful_images']} | "
                       f"Failed: {summary['failed_images']} | "
                       f"Rate: {summary['success_rate']:.1%}")

        console.print(Panel(summary_text, title="Benchmark Summary"))

        # Timing table
        timing_table = Table(title="Performance Metrics")
        timing_table.add_column("Metric", style="cyan")
        timing_table.add_column("Mean", justify="right")
        timing_table.add_column("Median", justify="right")
        timing_table.add_column("Min", justify="right")
        timing_table.add_column("Max", justify="right")
        timing_table.add_column("Std Dev", justify="right")

        timing = analysis["timing"]
        metrics = [
            ("Load Time (ms)", timing["load_time_ms"]),
            ("Detection Time (ms)", timing["detection_time_ms"]),
            ("Total Time (ms)", timing["total_time_ms"]),
        ]

        for name, stats in metrics:
            timing_table.add_row(
                name,
                f"{stats['mean']:.1f}",
                f"{stats['median']:.1f}",
                f"{stats['min']:.1f}",
                f"{stats['max']:.1f}",
                f"{stats['std']:.1f}"
            )

        # Add FPS row
        fps_stats = timing["fps"]
        timing_table.add_row(
            "FPS",
            f"{fps_stats['mean']:.1f}",
            f"{fps_stats['median']:.1f}",
            f"{fps_stats['min']:.1f}",
            f"{fps_stats['max']:.1f}",
            "—"
        )

        console.print(timing_table)

        # Memory table
        memory_table = Table(title="Memory Usage")
        memory_table.add_column("Metric", style="cyan")
        memory_table.add_column("Value", justify="right")

        memory = analysis["memory"]["peak_usage_mb"]
        memory_table.add_row("Peak Usage (MB)", f"{memory['mean']:.1f} ± {memory['std']:.1f}")
        memory_table.add_row("Min Usage (MB)", f"{memory['min']:.1f}")
        memory_table.add_row("Max Usage (MB)", f"{memory['max']:.1f}")

        console.print(memory_table)

        # Detection stats
        detection = analysis["detection"]
        detection_text = (f"Total Detections: {detection['total_detections']} | "
                         f"Successful: {detection['successful_detections']} | "
                         f"Rate: {detection['detection_rate']:.1%}")

        console.print(Panel(detection_text, title="Detection Statistics"))

        # Per-logo timing if available
        if detection["detection_times_by_logo"]:
            logo_table = Table(title="Per-Logo Performance")
            logo_table.add_column("Logo", style="cyan")
            logo_table.add_column("Avg Time (ms)", justify="right")
            logo_table.add_column("Detections", justify="right")

            for logo, stats in detection["detection_times_by_logo"].items():
                logo_table.add_row(
                    logo,
                    f"{stats['mean']:.1f}",
                    str(stats['count'])
                )

            console.print(logo_table)

        # Show failures if any
        if analysis["failures"]:
            console.print(f"\n[bold red]📋 Failures ({len(analysis['failures'])}):[/bold red]")
            for failure in analysis["failures"][:5]:  # Show first 5
                console.print(f"  [red]✗[/red] {Path(failure['image']).name}: {failure['error']}")
            if len(analysis["failures"]) > 5:
                console.print(f"  ... and {len(analysis['failures']) - 5} more")

    def save_results(self, output_path: Path, analysis: Dict[str, Any]) -> bool:
        """
        Save benchmark results to JSON file.

        Args:
            output_path: Path to save results
            analysis: Analysis results

        Returns:
            True if saved successfully
        """
        try:
            output_data = {
                "benchmark_info": {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "config_file": str(self.config_path),
                    "detector_config": self.detector.config.dict() if self.detector else None,
                    "system_info": self.system_info
                },
                "analysis": analysis,
                "raw_results": self.results
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)

            console.print(f"[green]✓[/green] Results saved: {output_path}")
            return True

        except Exception as e:
            console.print(f"[red]Error saving results: {e}[/red]")
            return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark Align-Press detector performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic benchmark
  python -m alignpress.cli.benchmark \\
    --config config/example_detector.yaml \\
    --dataset datasets/test_images/ \\
    --output benchmark_results.json

  # Limited sample benchmark
  python -m alignpress.cli.benchmark \\
    --config config/example_detector.yaml \\
    --dataset datasets/test_images/ \\
    --samples 50 \\
    --output benchmark_50_samples.json
        """
    )

    # Required arguments
    parser.add_argument(
        '--config', '-c',
        type=str,
        required=True,
        help='Path to detector configuration file'
    )

    parser.add_argument(
        '--dataset', '-d',
        type=str,
        required=True,
        help='Path to dataset directory or single image'
    )

    # Optional arguments
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Path to save benchmark results (JSON)'
    )

    parser.add_argument(
        '--samples', '-s',
        type=int,
        help='Limit number of samples to test'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-essential output'
    )

    args = parser.parse_args()

    if args.quiet:
        console.quiet = True

    # Initialize benchmark
    benchmark = PerformanceBenchmark(Path(args.config))

    try:
        # Load detector
        if not benchmark.load_detector():
            return 1

        # Run benchmark
        if not benchmark.run_benchmark(Path(args.dataset), args.samples):
            return 1

        # Analyze results
        console.print("\n[bold blue]📊 Analyzing results...[/bold blue]")
        analysis = benchmark.analyze_results()

        if not analysis:
            console.print("[red]Error: No analysis results generated[/red]")
            return 1

        # Print analysis
        benchmark.print_analysis(analysis)

        # Save results if requested
        if args.output:
            if not benchmark.save_results(Path(args.output), analysis):
                return 1

        # Return success/failure based on results
        if analysis.get("summary", {}).get("success_rate", 0) > 0.8:
            console.print("\n[green]🎉 Benchmark completed successfully![/green]")
            return 0
        else:
            console.print("\n[yellow]⚠ Benchmark completed with issues. Check results above.[/yellow]")
            return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


if __name__ == '__main__':
    sys.exit(main())