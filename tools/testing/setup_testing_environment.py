#!/usr/bin/env python3
"""
Setup testing environment for Align-Press v2.

This script prepares the directory structure and initial files needed
for complete testing workflow from calibration to evaluation.
"""

import shutil
import sys
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class TestingEnvironmentSetup:
    """Setup testing environment with proper directory structure."""

    def __init__(self, project_root: Path = None):
        """Initialize setup."""
        self.project_root = project_root or Path.cwd()
        self.required_dirs = [
            "datasets/calibration",
            "datasets/testing",
            "datasets/real_templates",
            "calibration/platen_50x60",
            "results/calibration",
            "results/evaluation",
            "results/benchmarks",
            "tools/testing"
        ]

    def create_directories(self) -> List[Path]:
        """Create required directory structure."""
        created_dirs = []

        for dir_path in self.required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(full_path)
                console.print(f"✅ Created: {dir_path}")
            else:
                console.print(f"📁 Exists: {dir_path}")

        return created_dirs

    def create_readme_files(self):
        """Create README files with instructions for each directory."""

        readme_contents = {
            "datasets/calibration/README.md": """# Calibration Images

Place your calibration images here:

## Required Images:
- `platen_with_chessboard.jpg` - Photo of platen with chessboard pattern
- `platen_with_aruco.jpg` - Photo of platen with ArUco markers (optional)

## Pattern Requirements:
- **Chessboard**: 9x6 internal corners, 25mm squares
- **ArUco**: Dictionary DICT_6X6_250, marker size 20mm

## Image Quality Guidelines:
- Resolution: Minimum 1920x1080
- Focus: Sharp pattern detection
- Lighting: Uniform, avoid shadows
- Angle: Perpendicular to platen surface
""",

            "datasets/testing/README.md": """# Testing Images

Place your test images here for evaluation:

## Directory Structure:
```
testing/
├── correct/          # Images with logo in correct position
├── incorrect/        # Images with logo in wrong position
├── no_logo/         # Images without logo (false positive test)
└── variations/      # Different conditions (lighting, angle, etc.)
```

## Image Naming Convention:
- `test_correct_001.jpg` - Logo in perfect position
- `test_incorrect_off_5mm.jpg` - Logo 5mm off target
- `test_no_logo_001.jpg` - No logo present
- `test_variation_bright_001.jpg` - Bright lighting variation

## Requirements:
- Same camera setup as calibration
- Consistent platen position
- Various logo positions for robustness testing
""",

            "datasets/real_templates/README.md": """# Real Logo Templates

Place your actual logo images here:

## Required Files:
- `main_logo.jpg` - Primary logo image for template matching
- `main_logo_clean.png` - Cleaned version (transparent background)

## Optional Variations:
- `main_logo_rotated_5deg.jpg` - Slightly rotated version
- `main_logo_scaled_90.jpg` - Slightly scaled version

## Template Quality Guidelines:
- High resolution (minimum 300x300px)
- Good contrast
- Minimal background noise
- Sharp edges and details
""",

            "calibration/platen_50x60/README.md": """# Platen 50x60 Calibration Data

This directory contains calibration data for the 50cm x 60cm platen:

## Files:
- `calibration.json` - Main calibration data
- `quality_metrics.json` - Calibration quality assessment
- `calibration_debug.jpg` - Debug image with detected pattern overlay

## Calibration Parameters:
- Platen size: 500mm x 600mm
- Expected mm_per_px: ~0.3-0.5 (depends on camera distance)
- Pattern: 9x6 chessboard, 25mm squares

## Quality Thresholds:
- Reprojection error: < 2.0 pixels
- Pattern detection rate: > 90%
- Corner detection accuracy: > 95%
""",

            "results/README.md": """# Testing Results

This directory contains all testing and evaluation results:

## Subdirectories:
- `calibration/` - Calibration quality reports
- `evaluation/` - Logo detection evaluation results
- `benchmarks/` - Performance benchmark data

## Report Types:
- HTML reports with visualizations
- JSON data for automated analysis
- CSV summaries for spreadsheet analysis
- Debug images with detection overlays
"""
        }

        for file_path, content in readme_contents.items():
            full_path = self.project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if not full_path.exists():
                with open(full_path, 'w') as f:
                    f.write(content)
                console.print(f"📝 Created: {file_path}")
            else:
                console.print(f"📝 Exists: {file_path}")

    def check_existing_files(self) -> Table:
        """Check what files already exist in the testing structure."""
        table = Table(title="Existing Testing Files")
        table.add_column("Category", style="cyan")
        table.add_column("File", style="white")
        table.add_column("Status", style="green")
        table.add_column("Size", style="yellow")

        categories = {
            "Calibration": "datasets/calibration",
            "Testing": "datasets/testing",
            "Templates": "datasets/real_templates",
            "Results": "results"
        }

        for category, dir_path in categories.items():
            full_dir = self.project_root / dir_path
            if full_dir.exists():
                files = list(full_dir.rglob("*"))
                if files:
                    for file_path in files:
                        if file_path.is_file():
                            size = file_path.stat().st_size
                            size_str = f"{size:,} bytes" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
                            table.add_row(category, file_path.name, "✅ Found", size_str)
                            category = ""  # Only show category once
                else:
                    table.add_row(category, "No files", "📁 Empty", "-")
            else:
                table.add_row(category, "Directory missing", "❌ Missing", "-")

        return table

    def generate_chessboard_pattern(self, output_path: Path = None) -> Path:
        """Generate a chessboard pattern for printing."""
        if output_path is None:
            output_path = self.project_root / "tools/testing/chessboard_9x6_25mm.pdf"

        # We'll create a simple text file with instructions since we don't have reportlab
        instructions = """# Chessboard Pattern for Calibration

## Pattern Specifications:
- **Size**: 9x6 internal corners (10x7 squares total)
- **Square size**: 25mm x 25mm
- **Total size**: 250mm x 175mm
- **Print scale**: 100% (no scaling)

## Printing Instructions:
1. Use a high-quality printer
2. Print on white paper (minimum 80gsm)
3. Ensure 100% scale (no fit-to-page)
4. Mount on rigid surface (cardboard/foam board)
5. Ensure flat surface without warping

## Online Generator:
Visit: https://calib.io/pages/camera-calibration-pattern-generator
- Select: Chessboard
- Dimensions: 10x7 squares
- Square size: 25mm
- Format: PDF

## Verification:
Measure printed squares with ruler to confirm 25mm size.
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path.with_suffix('.txt'), 'w') as f:
            f.write(instructions)

        console.print(f"📐 Created pattern instructions: {output_path.with_suffix('.txt')}")
        return output_path.with_suffix('.txt')

    def run_setup(self):
        """Run complete setup process."""
        console.print(Panel("🔧 Setting up Align-Press v2 Testing Environment", style="blue"))

        # Create directories
        console.print("\n📁 Creating directory structure...")
        created_dirs = self.create_directories()

        # Create README files
        console.print("\n📝 Creating documentation...")
        self.create_readme_files()

        # Generate pattern instructions
        console.print("\n📐 Creating calibration pattern...")
        pattern_file = self.generate_chessboard_pattern()

        # Check existing files
        console.print("\n📊 Checking existing files...")
        file_table = self.check_existing_files()
        console.print(file_table)

        # Summary
        console.print(Panel(
            f"""✅ Testing environment setup complete!

📁 Created {len(created_dirs)} new directories
📝 Documentation files created
📐 Calibration pattern instructions ready

🎯 Next Steps:
1. Print chessboard pattern (see {pattern_file})
2. Take calibration photo of your 50x60cm platen with pattern
3. Save as datasets/calibration/platen_with_chessboard.jpg
4. Extract your logo template to datasets/real_templates/main_logo.jpg
5. Run calibration: python -m alignpress.cli.main calibrate --help

📚 See README files in each directory for detailed instructions.
""",
            style="green",
            title="🎉 Setup Complete"
        ))


def main():
    """Main entry point."""
    setup = TestingEnvironmentSetup()
    setup.run_setup()
    return 0


if __name__ == "__main__":
    sys.exit(main())