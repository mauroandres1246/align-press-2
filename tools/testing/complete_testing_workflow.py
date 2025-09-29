#!/usr/bin/env python3
"""
Complete testing workflow for Align-Press v2.

This script orchestrates the entire testing process from calibration
to final evaluation and reporting.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


class WorkflowStep:
    """Represents a single step in the testing workflow."""

    def __init__(self, name: str, description: str, required: bool = True):
        """Initialize workflow step."""
        self.name = name
        self.description = description
        self.required = required
        self.completed = False
        self.output_files: List[Path] = []
        self.error_message: Optional[str] = None

    def __str__(self):
        """String representation."""
        status = "✅" if self.completed else "❌" if self.error_message else "⏳"
        return f"{status} {self.name}: {self.description}"


class TestingWorkflow:
    """Complete testing workflow orchestrator."""

    def __init__(self, project_root: Path = None):
        """Initialize workflow."""
        self.project_root = project_root or Path.cwd()
        self.steps: List[WorkflowStep] = []
        self.workflow_results: Dict[str, any] = {}

        # Initialize workflow steps
        self._init_workflow_steps()

    def _init_workflow_steps(self):
        """Initialize all workflow steps."""
        self.steps = [
            WorkflowStep("setup", "Setup testing environment"),
            WorkflowStep("calibration", "Camera/platen calibration"),
            WorkflowStep("template_extraction", "Extract logo template"),
            WorkflowStep("config_update", "Update detector configuration"),
            WorkflowStep("dataset_preparation", "Prepare testing dataset"),
            WorkflowStep("evaluation", "Run comprehensive evaluation"),
            WorkflowStep("report_generation", "Generate final reports"),
        ]

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        console.print("🔍 Checking prerequisites...")

        issues = []

        # Check Python dependencies
        required_packages = ["cv2", "numpy", "rich", "pydantic"]
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                issues.append(f"Missing Python package: {package}")

        # Check project structure
        required_dirs = ["alignpress", "config", "tools"]
        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                issues.append(f"Missing directory: {dir_name}")

        # Check key files
        required_files = [
            "alignpress/core/detector.py",
            "config/example_detector.yaml",
            "tools/testing/setup_testing_environment.py"
        ]
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                issues.append(f"Missing file: {file_path}")

        if issues:
            console.print("❌ Prerequisites check failed:")
            for issue in issues:
                console.print(f"   • {issue}")
            return False

        console.print("✅ All prerequisites met")
        return True

    def run_step_setup(self) -> bool:
        """Setup testing environment."""
        console.print("🔧 Setting up testing environment...")

        try:
            # Run setup script
            setup_script = self.project_root / "tools/testing/setup_testing_environment.py"
            result = subprocess.run([
                sys.executable, str(setup_script)
            ], capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                self.steps[0].error_message = f"Setup script failed: {result.stderr}"
                return False

            self.steps[0].completed = True
            console.print("✅ Testing environment setup completed")
            return True

        except Exception as e:
            self.steps[0].error_message = str(e)
            return False

    def run_step_calibration(self, calibration_image: Path, pattern_size: tuple, square_size_mm: float) -> bool:
        """Run calibration step."""
        console.print("📐 Running calibration...")

        try:
            # Output paths
            calibration_output = self.project_root / "calibration/platen_50x60/calibration.json"
            debug_image_output = self.project_root / "calibration/platen_50x60/calibration_debug.jpg"

            # Run calibration script
            calibration_script = self.project_root / "tools/testing/calibrate_from_image.py"
            cmd = [
                sys.executable, str(calibration_script),
                "--image", str(calibration_image),
                "--pattern-size", str(pattern_size[0]), str(pattern_size[1]),
                "--square-size-mm", str(square_size_mm),
                "--output", str(calibration_output),
                "--debug-image", str(debug_image_output)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                self.steps[1].error_message = f"Calibration failed: {result.stderr}"
                return False

            # Store calibration results
            if calibration_output.exists():
                with open(calibration_output, 'r') as f:
                    self.workflow_results['calibration'] = json.load(f)

            self.steps[1].completed = True
            self.steps[1].output_files = [calibration_output, debug_image_output]
            console.print("✅ Calibration completed")
            return True

        except Exception as e:
            self.steps[1].error_message = str(e)
            return False

    def run_step_template_extraction(self, logo_image: Path, roi_coords: tuple = None) -> bool:
        """Extract logo template."""
        console.print("🎯 Extracting logo template...")

        try:
            # Output paths
            template_output = self.project_root / "datasets/real_templates/main_logo.png"
            variations_dir = self.project_root / "datasets/real_templates/variations"

            # Run template extraction
            extraction_script = self.project_root / "tools/testing/extract_template.py"
            cmd = [
                sys.executable, str(extraction_script),
                "--input", str(logo_image),
                "--output", str(template_output),
                "--enhance",
                "--generate-variations",
                "--variations-dir", str(variations_dir)
            ]

            # Add ROI coordinates if provided
            if roi_coords:
                cmd.extend(["--roi"] + [str(coord) for coord in roi_coords])
            else:
                cmd.append("--interactive")

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                self.steps[2].error_message = f"Template extraction failed: {result.stderr}"
                return False

            self.steps[2].completed = True
            self.steps[2].output_files = [template_output]
            console.print("✅ Template extraction completed")
            return True

        except Exception as e:
            self.steps[2].error_message = str(e)
            return False

    def run_step_config_update(self, logo_position_mm: tuple = None) -> bool:
        """Update detector configuration with calibration and template data."""
        console.print("⚙️ Updating detector configuration...")

        try:
            config_path = self.project_root / "config/platen_50x60_detector.yaml"

            # Load current configuration
            with open(config_path, 'r') as f:
                import yaml
                config = yaml.safe_load(f)

            # Update with calibration data
            if 'calibration' in self.workflow_results:
                cal_data = self.workflow_results['calibration']
                if 'mm_per_px' in cal_data:
                    config['plane']['mm_per_px'] = cal_data['mm_per_px']
                    console.print(f"📏 Updated scale factor: {cal_data['mm_per_px']:.3f} mm/px")

            # Update template path
            template_path = "datasets/real_templates/main_logo.png"
            if config.get('logos') and len(config['logos']) > 0:
                config['logos'][0]['template_path'] = template_path
                console.print(f"🎯 Updated template path: {template_path}")

                # Update logo position if provided
                if logo_position_mm:
                    config['logos'][0]['position_mm'] = list(logo_position_mm)
                    console.print(f"📍 Updated logo position: {logo_position_mm}")

            # Save updated configuration
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            self.steps[3].completed = True
            console.print("✅ Configuration updated")
            return True

        except Exception as e:
            self.steps[3].error_message = str(e)
            return False

    def run_step_dataset_preparation(self) -> bool:
        """Prepare testing dataset."""
        console.print("📁 Preparing testing dataset...")

        try:
            # Check if testing images exist
            testing_dir = self.project_root / "datasets/testing"

            # Create subdirectories if they don't exist
            subdirs = ["correct", "incorrect", "no_logo", "variations"]
            for subdir in subdirs:
                (testing_dir / subdir).mkdir(parents=True, exist_ok=True)

            # Count existing images
            image_count = 0
            for pattern in ["*.jpg", "*.jpeg", "*.png"]:
                image_count += len(list(testing_dir.rglob(pattern)))

            if image_count == 0:
                console.print("⚠️ No testing images found. Please add images to datasets/testing/")
                console.print("   - correct/: Images with logo in correct position")
                console.print("   - incorrect/: Images with logo in wrong position")
                console.print("   - no_logo/: Images without logo")
                console.print("   - variations/: Images with different conditions")

                if not Confirm.ask("Continue without testing images?", default=False):
                    self.steps[4].error_message = "No testing images available"
                    return False

            self.steps[4].completed = True
            console.print(f"✅ Dataset preparation completed ({image_count} images found)")
            return True

        except Exception as e:
            self.steps[4].error_message = str(e)
            return False

    def run_step_evaluation(self) -> bool:
        """Run comprehensive evaluation."""
        console.print("🧪 Running evaluation...")

        try:
            # Input paths
            config_path = self.project_root / "config/platen_50x60_detector.yaml"
            dataset_path = self.project_root / "datasets/testing"
            calibration_path = self.project_root / "calibration/platen_50x60/calibration.json"

            # Output paths
            results_output = self.project_root / "results/evaluation_results.json"
            html_report = self.project_root / "results/evaluation_report.html"

            # Run evaluation script
            evaluation_script = self.project_root / "tools/testing/run_full_evaluation.py"
            cmd = [
                sys.executable, str(evaluation_script),
                "--config", str(config_path),
                "--dataset", str(dataset_path),
                "--output", str(results_output),
                "--html-report", str(html_report)
            ]

            # Add calibration if available
            if calibration_path.exists():
                cmd.extend(["--calibration", str(calibration_path)])

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                self.steps[5].error_message = f"Evaluation failed: {result.stderr}"
                return False

            # Store evaluation results
            if results_output.exists():
                with open(results_output, 'r') as f:
                    self.workflow_results['evaluation'] = json.load(f)

            self.steps[5].completed = True
            self.steps[5].output_files = [results_output, html_report]
            console.print("✅ Evaluation completed")
            return True

        except Exception as e:
            self.steps[5].error_message = str(e)
            return False

    def run_step_report_generation(self) -> bool:
        """Generate final comprehensive report."""
        console.print("📊 Generating final reports...")

        try:
            # Create summary report
            summary_path = self.project_root / "results/workflow_summary.json"

            summary_data = {
                "workflow_timestamp": datetime.now().isoformat(),
                "workflow_version": "1.0",
                "steps_completed": [step.name for step in self.steps if step.completed],
                "steps_failed": [step.name for step in self.steps if step.error_message],
                "output_files": {},
                "results": self.workflow_results
            }

            # Collect output files from all steps
            for step in self.steps:
                if step.output_files:
                    summary_data["output_files"][step.name] = [str(f) for f in step.output_files]

            # Save summary
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            with open(summary_path, 'w') as f:
                json.dump(summary_data, f, indent=2)

            self.steps[6].completed = True
            self.steps[6].output_files = [summary_path]
            console.print("✅ Report generation completed")
            return True

        except Exception as e:
            self.steps[6].error_message = str(e)
            return False

    def print_workflow_status(self):
        """Print current workflow status."""
        table = Table(title="Testing Workflow Status")
        table.add_column("Step", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")

        for step in self.steps:
            if step.completed:
                status = "✅ Completed"
            elif step.error_message:
                status = f"❌ Failed: {step.error_message}"
            else:
                status = "⏳ Pending"

            table.add_row(step.name.replace("_", " ").title(), step.description, status)

        console.print(table)

    def print_final_summary(self):
        """Print final workflow summary."""
        completed_steps = [step for step in self.steps if step.completed]
        failed_steps = [step for step in self.steps if step.error_message]

        console.print(Panel(
            f"""✅ Workflow Summary

📊 Steps Completed: {len(completed_steps)}/{len(self.steps)}
❌ Steps Failed: {len(failed_steps)}

📁 Output Files Generated:
""" + "\n".join([f"   • {file}" for step in self.steps for file in step.output_files]) + f"""

📈 Key Results:
""" + (f"""   • Calibration: {self.workflow_results.get('calibration', {}).get('mm_per_px', 'N/A')} mm/px
   • Detection Rate: {self.workflow_results.get('evaluation', {}).get('summary_metrics', {}).get('summary', {}).get('detection_rate', 'N/A')}
   • Processing Speed: {self.workflow_results.get('evaluation', {}).get('summary_metrics', {}).get('performance', {}).get('mean_processing_time_ms', 'N/A')} ms
""" if 'evaluation' in self.workflow_results else "   • No evaluation results available") + f"""

🎯 Next Steps:
   1. Review HTML report: results/evaluation_report.html
   2. Check detailed results: results/evaluation_results.json
   3. Analyze calibration debug image: calibration/platen_50x60/calibration_debug.jpg
""",
            title="🎉 Testing Workflow Complete",
            style="green" if len(failed_steps) == 0 else "yellow"
        ))

    def run_complete_workflow(self, **kwargs) -> bool:
        """Run the complete testing workflow."""
        console.print(Panel(
            "🎯 Align-Press v2 - Complete Testing Workflow",
            subtitle="Automated calibration, template extraction, and evaluation"
        ))

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Run workflow steps
        success = True

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            task = progress.add_task("Running workflow...", total=None)

            # Step 1: Setup
            progress.update(task, description="Setting up testing environment...")
            if not self.run_step_setup():
                success = False

            # Step 2: Calibration
            if success and kwargs.get('calibration_image'):
                progress.update(task, description="Running calibration...")
                success = self.run_step_calibration(
                    kwargs['calibration_image'],
                    kwargs.get('pattern_size', (9, 6)),
                    kwargs.get('square_size_mm', 25.0)
                )

            # Step 3: Template extraction
            if success and kwargs.get('logo_image'):
                progress.update(task, description="Extracting template...")
                success = self.run_step_template_extraction(
                    kwargs['logo_image'],
                    kwargs.get('roi_coords')
                )

            # Step 4: Config update
            if success:
                progress.update(task, description="Updating configuration...")
                success = self.run_step_config_update(kwargs.get('logo_position_mm'))

            # Step 5: Dataset preparation
            if success:
                progress.update(task, description="Preparing dataset...")
                success = self.run_step_dataset_preparation()

            # Step 6: Evaluation
            if success:
                progress.update(task, description="Running evaluation...")
                success = self.run_step_evaluation()

            # Step 7: Report generation
            if success:
                progress.update(task, description="Generating reports...")
                success = self.run_step_report_generation()

        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Complete testing workflow for Align-Press v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive workflow
  python complete_testing_workflow.py --interactive

  # Automated workflow with images
  python complete_testing_workflow.py \\
    --calibration-image datasets/calibration/platen_with_chessboard.jpg \\
    --logo-image datasets/real_templates/logo_source.jpg \\
    --pattern-size 9 6 \\
    --square-size-mm 25.0 \\
    --logo-position-mm 250 300

  # Skip interactive steps
  python complete_testing_workflow.py \\
    --calibration-image datasets/calibration/platen_with_chessboard.jpg \\
    --logo-image datasets/real_templates/logo_source.jpg \\
    --roi 100 50 200 150 \\
    --auto-confirm
        """
    )

    parser.add_argument(
        '--calibration-image',
        type=Path,
        help='Path to calibration image with chessboard pattern'
    )

    parser.add_argument(
        '--logo-image',
        type=Path,
        help='Path to image containing logo for template extraction'
    )

    parser.add_argument(
        '--pattern-size',
        type=int,
        nargs=2,
        default=[9, 6],
        metavar=('WIDTH', 'HEIGHT'),
        help='Chessboard pattern size (default: 9 6)'
    )

    parser.add_argument(
        '--square-size-mm',
        type=float,
        default=25.0,
        help='Chessboard square size in mm (default: 25.0)'
    )

    parser.add_argument(
        '--roi',
        type=int,
        nargs=4,
        metavar=('X', 'Y', 'WIDTH', 'HEIGHT'),
        help='Logo ROI coordinates for template extraction'
    )

    parser.add_argument(
        '--logo-position-mm',
        type=float,
        nargs=2,
        metavar=('X', 'Y'),
        help='Expected logo position in mm (default: platen center)'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode with prompts'
    )

    parser.add_argument(
        '--auto-confirm',
        action='store_true',
        help='Auto-confirm all prompts (non-interactive mode)'
    )

    args = parser.parse_args()

    # Create workflow
    workflow = TestingWorkflow()

    # Interactive mode
    if args.interactive:
        console.print("🤖 Interactive Testing Workflow")

        # Get calibration image
        if not args.calibration_image:
            cal_path = Prompt.ask("Path to calibration image")
            args.calibration_image = Path(cal_path) if cal_path else None

        # Get logo image
        if not args.logo_image:
            logo_path = Prompt.ask("Path to logo image")
            args.logo_image = Path(logo_path) if logo_path else None

        # Get logo position
        if not args.logo_position_mm:
            x = Prompt.ask("Logo X position (mm)", default="250")
            y = Prompt.ask("Logo Y position (mm)", default="300")
            args.logo_position_mm = [float(x), float(y)]

    # Run workflow
    kwargs = {
        'calibration_image': args.calibration_image,
        'logo_image': args.logo_image,
        'pattern_size': tuple(args.pattern_size),
        'square_size_mm': args.square_size_mm,
        'roi_coords': tuple(args.roi) if args.roi else None,
        'logo_position_mm': tuple(args.logo_position_mm) if args.logo_position_mm else (250.0, 300.0)
    }

    success = workflow.run_complete_workflow(**kwargs)

    # Print results
    workflow.print_workflow_status()
    workflow.print_final_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())