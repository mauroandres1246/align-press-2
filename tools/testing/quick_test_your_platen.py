#!/usr/bin/env python3
"""
Quick testing script for your specific 50x60cm platen setup.

This script provides a simplified interface for testing your platen
with the images you provided.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


def main():
    """Main entry point for quick testing."""
    console.print(Panel(
        "🎯 Align-Press v2 - Quick Platen Testing",
        subtitle="Simplified setup for 50cm x 60cm platen"
    ))

    # Welcome message with your specific setup
    console.print("""
🎛️ **Your Setup Configuration**:
   • Platen size: 50cm x 60cm
   • Pattern: Chessboard 9x6 (25mm squares)
   • Logo position: Center of platen (250mm, 300mm)

📋 **Required Images**:
   1. Calibration image: Your platen with chessboard pattern
   2. Logo template: Clean image of your logo
   3. Test images: Photos with logo in various positions

🚀 **Quick Start Steps**:
""")

    steps = [
        "1. Place your images in the correct directories",
        "2. Run calibration with your chessboard image",
        "3. Extract your logo template",
        "4. Test with your sample images",
        "5. View results and reports"
    ]

    for step in steps:
        console.print(f"   {step}")

    console.print("\n" + "="*60)

    # Check if user wants to proceed
    if not Confirm.ask("\n🚀 Ready to start testing?", default=True):
        console.print("👋 Goodbye! Run this script again when you're ready.")
        return 0

    # File path collection
    console.print("\n📁 **Step 1: Locate Your Images**")

    # Calibration image
    console.print("\n📐 First, we need your calibration image...")
    console.print("   This should be a photo of your 50x60cm platen with the chessboard pattern on it.")

    cal_image_path = None
    while not cal_image_path:
        path_input = Prompt.ask("Enter path to calibration image", default="datasets/calibration/platen_with_chessboard.jpg")
        cal_path = Path(path_input)

        if cal_path.exists():
            cal_image_path = cal_path
            console.print(f"✅ Found calibration image: {cal_image_path}")
        else:
            console.print(f"❌ File not found: {cal_path}")
            if not Confirm.ask("Try a different path?", default=True):
                break

    # Logo image
    console.print("\n🎯 Next, we need your logo image...")
    console.print("   This should be a clear image of the logo you want to detect.")

    logo_image_path = None
    while not logo_image_path:
        path_input = Prompt.ask("Enter path to logo image", default="datasets/real_templates/logo_source.jpg")
        logo_path = Path(path_input)

        if logo_path.exists():
            logo_image_path = logo_path
            console.print(f"✅ Found logo image: {logo_image_path}")
        else:
            console.print(f"❌ File not found: {logo_path}")
            if not Confirm.ask("Try a different path?", default=True):
                break

    # Check if we have the required images
    if not cal_image_path or not logo_image_path:
        console.print(Panel(
            "❌ Missing required images. Please ensure you have:\n"
            "1. Calibration image with chessboard pattern\n"
            "2. Logo image for template extraction\n\n"
            "Place them in the suggested directories and run this script again.",
            style="red",
            title="Setup Incomplete"
        ))
        return 1

    # Run the workflow
    console.print("\n🔧 **Step 2: Running Automated Workflow**")

    # Import and run the complete workflow
    sys.path.append(str(Path(__file__).parent))
    from complete_testing_workflow import TestingWorkflow

    workflow = TestingWorkflow()

    # Workflow parameters for your specific setup
    kwargs = {
        'calibration_image': cal_image_path,
        'logo_image': logo_image_path,
        'pattern_size': (9, 6),
        'square_size_mm': 25.0,
        'logo_position_mm': (250.0, 300.0),  # Center of your 50x60cm platen
        'roi_coords': None  # Will use interactive selection
    }

    console.print("🚀 Starting automated workflow...")
    success = workflow.run_complete_workflow(**kwargs)

    # Results summary
    console.print("\n" + "="*60)
    workflow.print_workflow_status()

    if success:
        console.print(Panel(
            """✅ **Testing Complete!**

📊 **Check Your Results**:
   • HTML Report: results/evaluation_report.html
   • Detailed Data: results/evaluation_results.json
   • Calibration Debug: calibration/platen_50x60/calibration_debug.jpg

🎯 **Next Steps**:
   1. Open the HTML report in your browser
   2. Check if calibration looks correct in the debug image
   3. Add more test images to datasets/testing/ for better evaluation
   4. Adjust detection parameters in config/platen_50x60_detector.yaml if needed

💡 **Tips for Better Results**:
   • Ensure consistent lighting between calibration and test images
   • Keep the platen in the same position relative to camera
   • Use high-quality, focused images
   • Test with various logo positions and conditions
""",
            style="green",
            title="🎉 Success!"
        ))
    else:
        console.print(Panel(
            """❌ **Testing Failed**

🔍 **Common Issues & Solutions**:
   • Chessboard not detected: Ensure pattern is clearly visible and focused
   • Logo extraction failed: Check if logo image has good contrast
   • Configuration errors: Verify YAML syntax in config files

🛠️ **Troubleshooting**:
   1. Check the error messages in the workflow status above
   2. Verify your images are high quality and properly focused
   3. Ensure the chessboard pattern matches the 9x6 specification
   4. Try adjusting the ROI coordinates for logo extraction

📞 **Need Help?**:
   Run individual tools for more detailed error information:
   • python tools/testing/calibrate_from_image.py --help
   • python tools/testing/extract_template.py --help
   • python tools/testing/run_full_evaluation.py --help
""",
            style="red",
            title="❌ Workflow Failed"
        ))

    workflow.print_final_summary()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())