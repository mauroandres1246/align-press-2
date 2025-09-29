#!/usr/bin/env python3
"""
Template extraction tool for logo detection.

This script helps extract logo templates from images and prepare them
for use in the detection system.
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple, Optional, List

import cv2
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, FloatPrompt
from rich.table import Table

# Import transparency utilities
sys.path.append(str(Path(__file__).parents[2]))
from alignpress.utils.image_utils import (
    load_image_with_alpha, save_image_with_alpha,
    remove_background_auto, has_transparency
)

console = Console()


class TemplateExtractor:
    """Extract and process logo templates from images."""

    def __init__(self):
        """Initialize extractor."""
        self.original_image: Optional[np.ndarray] = None
        self.original_alpha: Optional[np.ndarray] = None
        self.template: Optional[np.ndarray] = None
        self.template_alpha: Optional[np.ndarray] = None
        self.roi_coords: Optional[Tuple[int, int, int, int]] = None

    def load_image(self, image_path: Path) -> bool:
        """Load source image with transparency support."""
        try:
            if not image_path.exists():
                console.print(f"❌ Image not found: {image_path}")
                return False

            self.original_image, self.original_alpha = load_image_with_alpha(str(image_path))
            if self.original_image is None:
                console.print(f"❌ Failed to load image: {image_path}")
                return False

            height, width = self.original_image.shape[:2]
            has_alpha = self.original_alpha is not None
            alpha_info = " (with transparency)" if has_alpha else ""
            console.print(f"📷 Loaded image: {width}x{height} pixels{alpha_info}")
            return True

        except Exception as e:
            console.print(f"❌ Error loading image: {e}")
            return False

    def interactive_roi_selection(self) -> bool:
        """Interactive ROI selection using mouse."""
        if self.original_image is None:
            return False

        console.print("🖱️ Select logo region with mouse:")
        console.print("   - Drag to select rectangle")
        console.print("   - Press ENTER to confirm")
        console.print("   - Press ESC to cancel")

        # Clone image for display
        display_image = self.original_image.copy()

        # ROI selection
        roi = cv2.selectROI("Select Logo Template", display_image, False, False)
        cv2.destroyAllWindows()

        if roi[2] > 0 and roi[3] > 0:  # Width and height > 0
            self.roi_coords = roi
            x, y, w, h = roi
            self.template = self.original_image[y:y+h, x:x+w]
            if self.original_alpha is not None:
                self.template_alpha = self.original_alpha[y:y+h, x:x+w]
            console.print(f"✅ Selected ROI: {w}x{h} pixels at ({x}, {y})")
            return True
        else:
            console.print("❌ No ROI selected")
            return False

    def manual_roi_selection(self, x: int, y: int, width: int, height: int) -> bool:
        """Manual ROI selection with coordinates."""
        if self.original_image is None:
            return False

        h, w = self.original_image.shape[:2]

        # Validate coordinates
        if x < 0 or y < 0 or x + width > w or y + height > h:
            console.print(f"❌ Invalid ROI coordinates: {x},{y},{width},{height}")
            console.print(f"   Image size: {w}x{h}")
            return False

        self.roi_coords = (x, y, width, height)
        self.template = self.original_image[y:y+height, x:x+width]
        if self.original_alpha is not None:
            self.template_alpha = self.original_alpha[y:y+height, x:x+width]
        console.print(f"✅ Extracted ROI: {width}x{height} pixels at ({x}, {y})")
        return True

    def enhance_template(self) -> bool:
        """Apply enhancement to improve template quality."""
        if self.template is None:
            return False

        original_template = self.template.copy()

        # Convert to grayscale for analysis
        gray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)

        # Calculate image quality metrics
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        mean_intensity = np.mean(gray)

        console.print(f"📊 Template Quality Metrics:")
        console.print(f"   Sharpness (Laplacian): {laplacian_var:.2f}")
        console.print(f"   Mean intensity: {mean_intensity:.1f}")

        # Apply enhancements based on image analysis
        enhanced = self.template.copy()

        # Enhance contrast if image is too flat
        if laplacian_var < 50:
            console.print("🔧 Applying contrast enhancement...")
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        # Sharpen if image is blurry
        if laplacian_var < 100:
            console.print("🔧 Applying sharpening...")
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)

        # Ask user if they want to keep enhancements
        console.print("\n📋 Enhancement Results:")

        # Show before/after comparison (in console description)
        enhanced_gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        enhanced_sharpness = cv2.Laplacian(enhanced_gray, cv2.CV_64F).var()
        console.print(f"   Original sharpness: {laplacian_var:.2f}")
        console.print(f"   Enhanced sharpness: {enhanced_sharpness:.2f}")

        if Confirm.ask("Keep enhancements?", default=True):
            self.template = enhanced
            console.print("✅ Enhancements applied")
        else:
            self.template = original_template
            console.print("📸 Keeping original template")

        return True

    def generate_variations(self, output_dir: Path) -> List[Path]:
        """Generate template variations for robust detection."""
        if self.template is None:
            return []

        variations = []
        output_dir.mkdir(parents=True, exist_ok=True)

        # Original template
        original_path = output_dir / "template_original.png"
        cv2.imwrite(str(original_path), self.template)
        variations.append(original_path)

        # Rotation variations
        angles = [-5, -2, 2, 5]
        for angle in angles:
            h, w = self.template.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(self.template, M, (w, h), borderValue=(255, 255, 255))

            path = output_dir / f"template_rot_{angle:+d}deg.png"
            cv2.imwrite(str(path), rotated)
            variations.append(path)

        # Scale variations
        scales = [0.9, 0.95, 1.05, 1.1]
        for scale in scales:
            h, w = self.template.shape[:2]
            new_w, new_h = int(w * scale), int(h * scale)
            scaled = cv2.resize(self.template, (new_w, new_h))

            # Pad or crop to original size
            if scale < 1.0:
                # Pad smaller image
                pad_w = (w - new_w) // 2
                pad_h = (h - new_h) // 2
                result = np.full((h, w, 3), 255, dtype=np.uint8)
                result[pad_h:pad_h+new_h, pad_w:pad_w+new_w] = scaled
            else:
                # Crop larger image
                crop_w = (new_w - w) // 2
                crop_h = (new_h - h) // 2
                result = scaled[crop_h:crop_h+h, crop_w:crop_w+w]

            path = output_dir / f"template_scale_{scale:.2f}.png"
            cv2.imwrite(str(path), result)
            variations.append(path)

        console.print(f"✅ Generated {len(variations)} template variations")
        return variations

    def save_template(self, output_path: Path) -> bool:
        """Save the main template with transparency support."""
        if self.template is None:
            return False

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_image_with_alpha(self.template, str(output_path), self.template_alpha)
            alpha_info = " (with transparency)" if self.template_alpha is not None else ""
            console.print(f"💾 Template saved to: {output_path}{alpha_info}")
            return True

        except Exception as e:
            console.print(f"❌ Error saving template: {e}")
            return False

    def add_transparency(self, method: str = "contour") -> bool:
        """Add transparency to logo by removing background."""
        if self.template is None:
            return False

        try:
            if self.template_alpha is not None:
                console.print("🎭 Template already has transparency")
                return True

            console.print(f"🎭 Removing background using {method} method...")
            processed_image, mask = remove_background_auto(self.template, method=method)

            if processed_image is not None:
                self.template = processed_image
                self.template_alpha = mask
                console.print("✅ Background removed successfully")
                return True
            else:
                console.print("❌ Failed to remove background")
                return False

        except Exception as e:
            console.print(f"❌ Error removing background: {e}")
            return False

    def analyze_template_quality(self) -> dict:
        """Analyze template quality for detection."""
        if self.template is None:
            return {}

        gray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Feature detection analysis
        orb = cv2.ORB_create(nfeatures=500)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        # Sharpness analysis
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Contrast analysis
        contrast = gray.std()

        # Edge density
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (h * w)

        # Size analysis
        size_category = "Small" if min(h, w) < 50 else "Medium" if min(h, w) < 100 else "Large"

        metrics = {
            "size": (w, h),
            "size_category": size_category,
            "features_detected": len(keypoints) if keypoints else 0,
            "sharpness": laplacian_var,
            "contrast": contrast,
            "edge_density": edge_density,
            "has_descriptors": descriptors is not None and len(descriptors) > 0
        }

        return metrics

    def print_quality_report(self):
        """Print template quality analysis."""
        metrics = self.analyze_template_quality()
        if not metrics:
            return

        table = Table(title="Template Quality Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Assessment", style="green")

        # Size
        w, h = metrics["size"]
        size_quality = "Good" if min(w, h) >= 50 else "Small (may cause issues)"
        table.add_row("Size", f"{w}x{h} pixels", size_quality)

        # Features
        features = metrics["features_detected"]
        feature_quality = "Excellent" if features > 50 else "Good" if features > 20 else "Poor"
        table.add_row("ORB Features", str(features), feature_quality)

        # Sharpness
        sharpness = metrics["sharpness"]
        sharp_quality = "Excellent" if sharpness > 100 else "Good" if sharpness > 50 else "Blurry"
        table.add_row("Sharpness", f"{sharpness:.1f}", sharp_quality)

        # Contrast
        contrast = metrics["contrast"]
        contrast_quality = "Excellent" if contrast > 50 else "Good" if contrast > 30 else "Low"
        table.add_row("Contrast", f"{contrast:.1f}", contrast_quality)

        # Edge density
        edge_density = metrics["edge_density"]
        edge_quality = "Rich" if edge_density > 0.1 else "Moderate" if edge_density > 0.05 else "Sparse"
        table.add_row("Edge Density", f"{edge_density:.3f}", edge_quality)

        console.print(table)

        # Overall assessment
        issues = []
        if features < 20:
            issues.append("Low feature count - consider higher contrast template")
        if sharpness < 50:
            issues.append("Template appears blurry - use sharper source image")
        if contrast < 30:
            issues.append("Low contrast - template may be hard to detect")
        if min(w, h) < 50:
            issues.append("Template is small - may reduce detection accuracy")

        if issues:
            console.print("\n⚠️ Potential Issues:")
            for issue in issues:
                console.print(f"   • {issue}")
        else:
            console.print("\n✅ Template quality looks good for detection!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract logo template from image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive ROI selection
  python extract_template.py \\
    --input datasets/real_templates/logo_source.jpg \\
    --output datasets/real_templates/main_logo.png \\
    --interactive

  # Manual ROI coordinates
  python extract_template.py \\
    --input datasets/real_templates/logo_source.jpg \\
    --output datasets/real_templates/main_logo.png \\
    --roi 100 50 200 150

  # Generate variations
  python extract_template.py \\
    --input datasets/real_templates/logo_source.jpg \\
    --output datasets/real_templates/main_logo.png \\
    --roi 100 50 200 150 \\
    --generate-variations
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=Path,
        required=True,
        help='Input image containing the logo'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        required=True,
        help='Output path for extracted template'
    )

    parser.add_argument(
        '--roi',
        type=int,
        nargs=4,
        metavar=('X', 'Y', 'WIDTH', 'HEIGHT'),
        help='Manual ROI coordinates (x, y, width, height)'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Use interactive ROI selection'
    )

    parser.add_argument(
        '--enhance',
        action='store_true',
        default=True,
        help='Apply automatic enhancements (default: True)'
    )

    parser.add_argument(
        '--generate-variations',
        action='store_true',
        help='Generate template variations for robust detection'
    )

    parser.add_argument(
        '--variations-dir',
        type=Path,
        help='Directory for template variations (default: output parent dir)'
    )

    parser.add_argument(
        '--add-transparency',
        choices=['contour', 'threshold', 'grabcut'],
        help='Automatically remove background to add transparency'
    )

    args = parser.parse_args()

    # Welcome message
    console.print(Panel(
        "🎯 Align-Press v2 - Template Extraction Tool",
        subtitle=f"Input: {args.input.name}"
    ))

    # Create extractor
    extractor = TemplateExtractor()

    # Load image
    if not extractor.load_image(args.input):
        return 1

    # Select ROI
    if args.roi:
        # Manual coordinates
        x, y, w, h = args.roi
        if not extractor.manual_roi_selection(x, y, w, h):
            return 1
    elif args.interactive:
        # Interactive selection
        if not extractor.interactive_roi_selection():
            return 1
    else:
        console.print("❌ Must specify either --roi coordinates or --interactive mode")
        return 1

    # Enhance template
    if args.enhance:
        extractor.enhance_template()

    # Add transparency if requested
    if args.add_transparency:
        extractor.add_transparency(method=args.add_transparency)

    # Analyze quality
    extractor.print_quality_report()

    # Save main template
    if not extractor.save_template(args.output):
        return 1

    # Generate variations if requested
    if args.generate_variations:
        variations_dir = args.variations_dir or args.output.parent / "variations"
        variations = extractor.generate_variations(variations_dir)
        console.print(f"📁 Variations saved to: {variations_dir}")

    console.print(Panel(
        "✅ Template extraction completed successfully!",
        style="green"
    ))

    return 0


if __name__ == "__main__":
    sys.exit(main())