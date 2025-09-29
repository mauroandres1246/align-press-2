#!/usr/bin/env python3
"""
Complete evaluation system for Align-Press v2.

This script runs comprehensive testing on a dataset of images,
evaluating detection accuracy, positioning precision, and performance.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import cv2
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.layout import Layout
from rich.live import Live

# Import detector components
sys.path.append(str(Path(__file__).parent.parent.parent))
from alignpress.core.detector import PlanarLogoDetector
from alignpress.core.schemas import DetectorConfigSchema, LogoResultSchema
from alignpress.utils.config_loader import ConfigLoader

console = Console()


class EvaluationResult:
    """Results from evaluating a single image."""

    def __init__(self, image_path: Path, expected_results: Dict[str, Any] = None):
        """Initialize evaluation result."""
        self.image_path = image_path
        self.expected_results = expected_results or {}
        self.detection_results: List[LogoResultSchema] = []
        self.processing_time_ms: float = 0.0
        self.success: bool = False
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "image_path": str(self.image_path),
            "expected_results": self.expected_results,
            "detection_results": [result.dict() for result in self.detection_results],
            "processing_time_ms": self.processing_time_ms,
            "success": self.success,
            "error_message": self.error_message
        }


class DatasetEvaluator:
    """Comprehensive dataset evaluation system."""

    def __init__(self, config_path: Path, calibration_path: Path = None):
        """Initialize evaluator."""
        self.config_path = config_path
        self.calibration_path = calibration_path

        # Load configuration
        self.config_loader = ConfigLoader()
        self.detector_config = self.config_loader.load_detector_config(config_path)

        # Initialize detector
        self.detector = PlanarLogoDetector(self.detector_config)

        # Load calibration if provided
        if calibration_path and calibration_path.exists():
            self.load_calibration(calibration_path)

        # Results storage
        self.evaluation_results: List[EvaluationResult] = []
        self.summary_metrics: Dict[str, Any] = {}

    def load_calibration(self, calibration_path: Path):
        """Load calibration data and update detector."""
        try:
            with open(calibration_path, 'r') as f:
                calibration_data = json.load(f)

            # Update detector config with calibration data
            if 'mm_per_px' in calibration_data:
                self.detector_config.plane.mm_per_px = calibration_data['mm_per_px']
                console.print(f"📏 Updated scale factor: {calibration_data['mm_per_px']:.3f} mm/px")

            # Store homography for potential use
            if 'homography' in calibration_data:
                self.homography = np.array(calibration_data['homography'])
                console.print("🔧 Loaded homography matrix")

        except Exception as e:
            console.print(f"⚠️ Warning: Could not load calibration: {e}")

    def discover_dataset(self, dataset_path: Path) -> List[Tuple[Path, Dict[str, Any]]]:
        """Discover images in dataset and parse expected results."""
        if not dataset_path.exists():
            console.print(f"❌ Dataset path not found: {dataset_path}")
            return []

        image_files = []

        # Supported image extensions
        extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

        if dataset_path.is_file():
            # Single image
            if dataset_path.suffix.lower() in extensions:
                image_files.append((dataset_path, {}))
        else:
            # Directory - scan for images
            for image_path in dataset_path.rglob("*"):
                if image_path.suffix.lower() in extensions:
                    # Parse expected results from filename or metadata
                    expected = self.parse_expected_results(image_path)
                    image_files.append((image_path, expected))

        console.print(f"📁 Discovered {len(image_files)} images for evaluation")
        return image_files

    def parse_expected_results(self, image_path: Path) -> Dict[str, Any]:
        """Parse expected results from filename or metadata file."""
        expected = {
            "has_logo": True,  # Default assumption
            "position_correct": True,  # Default assumption
            "category": "unknown"
        }

        # Parse from filename patterns
        filename = image_path.stem.lower()

        if "correct" in filename:
            expected["category"] = "correct"
            expected["has_logo"] = True
            expected["position_correct"] = True
        elif "incorrect" in filename or "wrong" in filename:
            expected["category"] = "incorrect"
            expected["has_logo"] = True
            expected["position_correct"] = False
        elif "no_logo" in filename or "empty" in filename:
            expected["category"] = "no_logo"
            expected["has_logo"] = False
            expected["position_correct"] = False
        elif "variation" in filename:
            expected["category"] = "variation"
            expected["has_logo"] = True
            expected["position_correct"] = True

        # Look for associated metadata file
        metadata_file = image_path.with_suffix('.json')
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    expected.update(metadata.get('expected', {}))
            except Exception:
                pass

        return expected

    def evaluate_image(self, image_path: Path, expected: Dict[str, Any]) -> EvaluationResult:
        """Evaluate detection on a single image."""
        result = EvaluationResult(image_path, expected)

        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                result.error_message = "Failed to load image"
                return result

            # Run detection with timing
            start_time = time.time()
            detection_results = self.detector.detect_logos(image)
            end_time = time.time()

            result.processing_time_ms = (end_time - start_time) * 1000
            result.detection_results = detection_results
            result.success = True

        except Exception as e:
            result.error_message = str(e)
            result.success = False

        return result

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive evaluation metrics."""
        if not self.evaluation_results:
            return {}

        # Basic statistics
        total_images = len(self.evaluation_results)
        successful_processing = sum(1 for r in self.evaluation_results if r.success)
        failed_processing = total_images - successful_processing

        # Processing time statistics
        processing_times = [r.processing_time_ms for r in self.evaluation_results if r.success]

        # Detection accuracy by category
        categories = ["correct", "incorrect", "no_logo", "variation", "unknown"]
        category_stats = {}

        for category in categories:
            category_results = [r for r in self.evaluation_results
                              if r.expected_results.get("category") == category]
            if category_results:
                category_stats[category] = {
                    "total": len(category_results),
                    "successful_detection": 0,
                    "false_positives": 0,
                    "false_negatives": 0,
                    "position_accuracy": 0
                }

        # Detailed analysis
        for result in self.evaluation_results:
            if not result.success:
                continue

            category = result.expected_results.get("category", "unknown")
            expected_has_logo = result.expected_results.get("has_logo", True)
            expected_correct_position = result.expected_results.get("position_correct", True)

            # Count detections
            logos_detected = sum(1 for det in result.detection_results if det.found)

            if category in category_stats:
                stats = category_stats[category]

                # Detection accuracy
                if expected_has_logo and logos_detected > 0:
                    stats["successful_detection"] += 1
                elif not expected_has_logo and logos_detected == 0:
                    stats["successful_detection"] += 1
                elif not expected_has_logo and logos_detected > 0:
                    stats["false_positives"] += 1
                elif expected_has_logo and logos_detected == 0:
                    stats["false_negatives"] += 1

                # Position accuracy (for detected logos)
                if logos_detected > 0:
                    position_ok = all(det.is_within_tolerance for det in result.detection_results if det.found)
                    if expected_correct_position and position_ok:
                        stats["position_accuracy"] += 1
                    elif not expected_correct_position and not position_ok:
                        stats["position_accuracy"] += 1

        # Overall metrics
        total_detections = sum(len(r.detection_results) for r in self.evaluation_results if r.success)
        successful_detections = sum(
            sum(1 for det in r.detection_results if det.found)
            for r in self.evaluation_results if r.success
        )

        metrics = {
            "summary": {
                "total_images": total_images,
                "successful_processing": successful_processing,
                "failed_processing": failed_processing,
                "processing_success_rate": successful_processing / total_images if total_images > 0 else 0,
                "total_detections": total_detections,
                "successful_detections": successful_detections,
                "detection_rate": successful_detections / total_detections if total_detections > 0 else 0
            },
            "performance": {
                "mean_processing_time_ms": np.mean(processing_times) if processing_times else 0,
                "median_processing_time_ms": np.median(processing_times) if processing_times else 0,
                "min_processing_time_ms": np.min(processing_times) if processing_times else 0,
                "max_processing_time_ms": np.max(processing_times) if processing_times else 0,
                "std_processing_time_ms": np.std(processing_times) if processing_times else 0,
                "fps_estimate": 1000 / np.mean(processing_times) if processing_times else 0
            },
            "accuracy_by_category": category_stats,
            "timestamp": datetime.now().isoformat(),
            "config_file": str(self.config_path),
            "calibration_file": str(self.calibration_path) if self.calibration_path else None
        }

        return metrics

    def run_evaluation(self, dataset_path: Path) -> bool:
        """Run complete evaluation on dataset."""
        # Discover images
        image_files = self.discover_dataset(dataset_path)
        if not image_files:
            console.print("❌ No images found in dataset")
            return False

        # Run evaluation with progress bar
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            task = progress.add_task("Evaluating images...", total=len(image_files))

            for image_path, expected in image_files:
                result = self.evaluate_image(image_path, expected)
                self.evaluation_results.append(result)

                # Update progress
                progress.update(task, advance=1)
                progress.update(task, description=f"Processed {image_path.name}")

        # Calculate metrics
        self.summary_metrics = self.calculate_metrics()

        console.print("✅ Evaluation completed")
        return True

    def save_results(self, output_path: Path):
        """Save detailed results to JSON file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            results_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "config_file": str(self.config_path),
                    "calibration_file": str(self.calibration_path) if self.calibration_path else None,
                    "total_images": len(self.evaluation_results)
                },
                "summary_metrics": self.summary_metrics,
                "detailed_results": [result.to_dict() for result in self.evaluation_results]
            }

            with open(output_path, 'w') as f:
                json.dump(results_data, f, indent=2)

            console.print(f"💾 Results saved to: {output_path}")

        except Exception as e:
            console.print(f"❌ Error saving results: {e}")

    def generate_html_report(self, output_path: Path):
        """Generate HTML report with visualizations."""
        if not self.summary_metrics:
            return

        html_content = self._create_html_report()

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            console.print(f"📊 HTML report saved to: {output_path}")

        except Exception as e:
            console.print(f"❌ Error generating HTML report: {e}")

    def _create_html_report(self) -> str:
        """Create HTML report content."""
        metrics = self.summary_metrics

        # Basic HTML template with embedded CSS and JS
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Align-Press v2 - Evaluation Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metric-card {{ display: inline-block; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px; margin: 10px; min-width: 200px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .metric-label {{ color: #6c757d; font-size: 14px; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .category-section {{ margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Align-Press v2 - Evaluation Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <h2>📊 Summary Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{metrics['summary']['total_images']}</div>
                <div class="metric-label">Total Images</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if metrics['summary']['processing_success_rate'] > 0.95 else 'warning'}">{metrics['summary']['processing_success_rate']:.1%}</div>
                <div class="metric-label">Processing Success Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if metrics['summary']['detection_rate'] > 0.8 else 'warning'}">{metrics['summary']['detection_rate']:.1%}</div>
                <div class="metric-label">Detection Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['performance']['mean_processing_time_ms']:.1f}ms</div>
                <div class="metric-label">Avg Processing Time</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['performance']['fps_estimate']:.1f}</div>
                <div class="metric-label">Estimated FPS</div>
            </div>
        </div>

        <h2>⚡ Performance Analysis</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Mean Processing Time</td><td>{metrics['performance']['mean_processing_time_ms']:.2f} ms</td></tr>
            <tr><td>Median Processing Time</td><td>{metrics['performance']['median_processing_time_ms']:.2f} ms</td></tr>
            <tr><td>Min Processing Time</td><td>{metrics['performance']['min_processing_time_ms']:.2f} ms</td></tr>
            <tr><td>Max Processing Time</td><td>{metrics['performance']['max_processing_time_ms']:.2f} ms</td></tr>
            <tr><td>Standard Deviation</td><td>{metrics['performance']['std_processing_time_ms']:.2f} ms</td></tr>
            <tr><td>Estimated FPS</td><td>{metrics['performance']['fps_estimate']:.1f} fps</td></tr>
        </table>

        <h2>🎯 Accuracy by Category</h2>
"""

        # Add category analysis
        for category, stats in metrics.get('accuracy_by_category', {}).items():
            if stats['total'] > 0:
                detection_accuracy = stats['successful_detection'] / stats['total']
                position_accuracy = stats['position_accuracy'] / stats['total'] if stats['total'] > 0 else 0

                html += f"""
        <div class="category-section">
            <h3>📁 {category.title()} Images</h3>
            <table>
                <tr><th>Metric</th><th>Value</th><th>Percentage</th></tr>
                <tr><td>Total Images</td><td>{stats['total']}</td><td>-</td></tr>
                <tr><td>Successful Detection</td><td>{stats['successful_detection']}</td><td>{detection_accuracy:.1%}</td></tr>
                <tr><td>False Positives</td><td>{stats['false_positives']}</td><td>{stats['false_positives']/stats['total']:.1%}</td></tr>
                <tr><td>False Negatives</td><td>{stats['false_negatives']}</td><td>{stats['false_negatives']/stats['total']:.1%}</td></tr>
                <tr><td>Position Accuracy</td><td>{stats['position_accuracy']}</td><td>{position_accuracy:.1%}</td></tr>
            </table>
        </div>
"""

        html += """
        <h2>🔧 Configuration</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
"""

        # Add configuration details
        html += f"""
            <tr><td>Config File</td><td>{metrics.get('config_file', 'N/A')}</td></tr>
            <tr><td>Calibration File</td><td>{metrics.get('calibration_file', 'N/A')}</td></tr>
            <tr><td>Evaluation Timestamp</td><td>{metrics.get('timestamp', 'N/A')}</td></tr>
        </table>

    </div>
</body>
</html>
"""

        return html

    def print_summary(self):
        """Print evaluation summary to console."""
        if not self.summary_metrics:
            return

        metrics = self.summary_metrics

        # Main summary table
        table = Table(title="Evaluation Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Assessment", style="green")

        # Overall metrics
        success_rate = metrics['summary']['processing_success_rate']
        detection_rate = metrics['summary']['detection_rate']
        avg_time = metrics['performance']['mean_processing_time_ms']
        fps = metrics['performance']['fps_estimate']

        table.add_row("Total Images", str(metrics['summary']['total_images']), "✅")

        success_assessment = "Excellent" if success_rate > 0.95 else "Good" if success_rate > 0.8 else "Poor"
        table.add_row("Processing Success", f"{success_rate:.1%}", success_assessment)

        detection_assessment = "Excellent" if detection_rate > 0.9 else "Good" if detection_rate > 0.7 else "Poor"
        table.add_row("Detection Rate", f"{detection_rate:.1%}", detection_assessment)

        speed_assessment = "Fast" if avg_time < 50 else "Moderate" if avg_time < 100 else "Slow"
        table.add_row("Avg Processing Time", f"{avg_time:.1f}ms", speed_assessment)

        fps_assessment = "Excellent" if fps > 20 else "Good" if fps > 10 else "Slow"
        table.add_row("Estimated FPS", f"{fps:.1f}", fps_assessment)

        console.print(table)

        # Category breakdown
        if metrics.get('accuracy_by_category'):
            console.print("\n📁 Category Breakdown:")
            for category, stats in metrics['accuracy_by_category'].items():
                if stats['total'] > 0:
                    accuracy = stats['successful_detection'] / stats['total']
                    console.print(f"   {category.title()}: {accuracy:.1%} ({stats['successful_detection']}/{stats['total']})")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive evaluation on image dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic evaluation
  python run_full_evaluation.py \\
    --config config/platen_50x60_detector.yaml \\
    --dataset datasets/testing/ \\
    --output results/evaluation.json

  # With calibration and HTML report
  python run_full_evaluation.py \\
    --config config/platen_50x60_detector.yaml \\
    --dataset datasets/testing/ \\
    --calibration calibration/platen_50x60/calibration.json \\
    --output results/evaluation.json \\
    --html-report results/evaluation_report.html
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=Path,
        required=True,
        help='Path to detector configuration file'
    )

    parser.add_argument(
        '--dataset', '-d',
        type=Path,
        required=True,
        help='Path to dataset directory or single image'
    )

    parser.add_argument(
        '--calibration',
        type=Path,
        help='Path to calibration file (optional)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path("results/evaluation_results.json"),
        help='Output path for results JSON file'
    )

    parser.add_argument(
        '--html-report',
        type=Path,
        help='Generate HTML report at specified path'
    )

    args = parser.parse_args()

    # Welcome message
    console.print(Panel(
        "🎯 Align-Press v2 - Dataset Evaluation",
        subtitle=f"Config: {args.config.name} | Dataset: {args.dataset.name}"
    ))

    try:
        # Create evaluator
        evaluator = DatasetEvaluator(args.config, args.calibration)

        # Run evaluation
        if not evaluator.run_evaluation(args.dataset):
            return 1

        # Print summary
        evaluator.print_summary()

        # Save results
        evaluator.save_results(args.output)

        # Generate HTML report if requested
        if args.html_report:
            evaluator.generate_html_report(args.html_report)

        console.print(Panel(
            "✅ Evaluation completed successfully!",
            style="green"
        ))

        return 0

    except Exception as e:
        console.print(Panel(
            f"❌ Evaluation failed: {e}",
            style="red"
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())