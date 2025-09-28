#!/usr/bin/env python3
"""
CLI tool for validating profile files.

This script validates profile files (planchas, estilos, variantes) against
their schemas and performs semantic validation checks.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, track
from rich.panel import Panel

from ..core.schemas import DetectorConfigSchema
from ..utils.image_utils import calculate_image_sharpness

console = Console()


class ProfileValidator:
    """
    Validator for profile files with semantic checks.
    """

    def __init__(self, fix_common: bool = False):
        """
        Initialize validator.

        Args:
            fix_common: Whether to attempt automatic fixes for common issues
        """
        self.fix_common = fix_common
        self.validation_results: List[Dict[str, Any]] = []
        self.fixed_files: List[Path] = []

    def validate_file(self, file_path: Path, schema_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate a single profile file.

        Args:
            file_path: Path to profile file
            schema_path: Optional path to JSON schema

        Returns:
            Validation result dictionary
        """
        result = {
            "file": str(file_path),
            "valid": False,
            "errors": [],
            "warnings": [],
            "fixed": False
        }

        try:
            # Check if file exists
            if not file_path.exists():
                result["errors"].append("File does not exist")
                return result

            # Load file content
            content = self._load_file(file_path)
            if content is None:
                result["errors"].append("Could not parse file content")
                return result

            # Schema validation if provided
            if schema_path:
                schema_errors = self._validate_against_schema(content, schema_path)
                result["errors"].extend(schema_errors)

            # Semantic validation based on file type
            semantic_errors, warnings = self._validate_semantics(content, file_path)
            result["errors"].extend(semantic_errors)
            result["warnings"].extend(warnings)

            # Attempt fixes if enabled and there are fixable issues
            if self.fix_common and result["errors"]:
                fixed_content, fixed = self._apply_fixes(content, result["errors"])
                if fixed:
                    self._save_file(file_path, fixed_content)
                    result["fixed"] = True
                    self.fixed_files.append(file_path)
                    # Re-validate after fixes
                    result["errors"] = []
                    result["warnings"] = []
                    semantic_errors, warnings = self._validate_semantics(fixed_content, file_path)
                    result["errors"].extend(semantic_errors)
                    result["warnings"].extend(warnings)

            result["valid"] = len(result["errors"]) == 0

        except Exception as e:
            result["errors"].append(f"Validation exception: {e}")

        return result

    def _load_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load and parse file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception:
            return None

    def _save_file(self, file_path: Path, content: Dict[str, Any]) -> None:
        """Save fixed content back to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
                else:
                    json.dump(content, f, indent=2, ensure_ascii=False)
        except Exception as e:
            console.print(f"[red]Warning: Could not save fixed file {file_path}: {e}[/red]")

    def _validate_against_schema(self, content: Dict[str, Any], schema_path: Path) -> List[str]:
        """Validate content against JSON schema."""
        try:
            import jsonschema

            with open(schema_path, 'r') as f:
                schema = json.load(f)

            jsonschema.validate(content, schema)
            return []
        except ImportError:
            return ["JSON schema validation skipped (jsonschema package not installed)"]
        except jsonschema.ValidationError as e:
            return [f"Schema validation error: {e.message}"]
        except Exception as e:
            return [f"Schema validation failed: {e}"]

    def _validate_semantics(self, content: Dict[str, Any], file_path: Path) -> Tuple[List[str], List[str]]:
        """Perform semantic validation based on file type."""
        errors = []
        warnings = []

        # Determine file type from path or content
        file_type = self._determine_file_type(content, file_path)

        if file_type == "detector_config":
            e, w = self._validate_detector_config(content)
            errors.extend(e)
            warnings.extend(w)
        elif file_type == "platen":
            e, w = self._validate_platen_profile(content)
            errors.extend(e)
            warnings.extend(w)
        elif file_type == "style":
            e, w = self._validate_style_profile(content)
            errors.extend(e)
            warnings.extend(w)
        elif file_type == "size_variant":
            e, w = self._validate_size_variant(content)
            errors.extend(e)
            warnings.extend(w)
        else:
            warnings.append(f"Unknown file type: {file_type}")

        return errors, warnings

    def _determine_file_type(self, content: Dict[str, Any], file_path: Path) -> str:
        """Determine the type of profile file."""
        # Check explicit type field
        if "type" in content:
            return content["type"]

        # Infer from path
        path_str = str(file_path).lower()
        if "planchas" in path_str or "platen" in path_str:
            return "platen"
        elif "estilos" in path_str or "style" in path_str:
            return "style"
        elif "variantes" in path_str or "variant" in path_str:
            return "size_variant"
        elif "detector" in path_str or ("logos" in content and "plane" in content):
            return "detector_config"

        return "unknown"

    def _validate_detector_config(self, content: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate detector configuration."""
        errors = []
        warnings = []

        try:
            # Try to create schema (this validates structure)
            DetectorConfigSchema(**content)
        except Exception as e:
            errors.append(f"Detector config validation failed: {e}")
            return errors, warnings

        # Additional semantic checks
        if "logos" in content:
            for logo in content["logos"]:
                # Check template file exists
                if "template_path" in logo:
                    template_path = Path(logo["template_path"])
                    if not template_path.is_absolute():
                        # Try relative to config file
                        template_path = Path.cwd() / template_path

                    if not template_path.exists():
                        errors.append(f"Template file not found: {logo['template_path']}")
                    else:
                        # Check template quality
                        quality_warnings = self._check_template_quality(template_path)
                        warnings.extend(quality_warnings)

        return errors, warnings

    def _validate_platen_profile(self, content: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate platen profile."""
        errors = []
        warnings = []

        required_fields = ["name", "dimensions_mm"]
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        # Validate dimensions
        if "dimensions_mm" in content:
            dims = content["dimensions_mm"]
            if isinstance(dims, dict):
                if "width" not in dims or "height" not in dims:
                    errors.append("Missing width or height in dimensions_mm")
                elif dims["width"] <= 0 or dims["height"] <= 0:
                    errors.append("Dimensions must be positive")
            else:
                errors.append("dimensions_mm should be an object with width and height")

        # Check calibration
        if "calibration" in content:
            cal = content["calibration"]
            if "homography_path" in cal:
                homography_path = Path(cal["homography_path"])
                if not homography_path.is_absolute():
                    homography_path = Path.cwd() / homography_path

                if not homography_path.exists():
                    errors.append(f"Homography file not found: {cal['homography_path']}")

        return errors, warnings

    def _validate_style_profile(self, content: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate style profile."""
        errors = []
        warnings = []

        required_fields = ["name", "logos"]
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        # Validate logos
        if "logos" in content:
            if not isinstance(content["logos"], list) or len(content["logos"]) == 0:
                errors.append("logos must be a non-empty list")
            else:
                logo_names = set()
                for i, logo in enumerate(content["logos"]):
                    if "name" not in logo:
                        errors.append(f"Logo {i} missing name field")
                    else:
                        if logo["name"] in logo_names:
                            errors.append(f"Duplicate logo name: {logo['name']}")
                        logo_names.add(logo["name"])

                    # Check template path
                    if "template_path" in logo:
                        template_path = Path(logo["template_path"])
                        if not template_path.is_absolute():
                            template_path = Path.cwd() / template_path

                        if not template_path.exists():
                            errors.append(f"Template file not found for logo {logo.get('name', i)}: {logo['template_path']}")

        return errors, warnings

    def _validate_size_variant(self, content: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate size variant profile."""
        errors = []
        warnings = []

        required_fields = ["name"]
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")

        # Validate position offsets
        if "position_offsets" in content:
            offsets = content["position_offsets"]
            if not isinstance(offsets, dict):
                errors.append("position_offsets must be an object")
            else:
                for logo_name, offset in offsets.items():
                    if not isinstance(offset, dict):
                        errors.append(f"Offset for {logo_name} must be an object")
                    else:
                        for coord in ["dx_mm", "dy_mm"]:
                            if coord in offset and not isinstance(offset[coord], (int, float)):
                                errors.append(f"Offset {coord} for {logo_name} must be a number")

        return errors, warnings

    def _check_template_quality(self, template_path: Path) -> List[str]:
        """Check template image quality."""
        warnings = []

        try:
            import cv2
            img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if img is None:
                warnings.append(f"Could not load template image: {template_path}")
                return warnings

            # Check image size
            h, w = img.shape[:2]
            if w < 50 or h < 50:
                warnings.append(f"Template {template_path.name} is very small ({w}x{h}px)")
            elif w > 500 or h > 500:
                warnings.append(f"Template {template_path.name} is very large ({w}x{h}px)")

            # Check sharpness
            sharpness = calculate_image_sharpness(img)
            if sharpness < 100:
                warnings.append(f"Template {template_path.name} may be blurry (sharpness: {sharpness:.1f})")

            # Check if image is too uniform
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if gray.std() < 30:
                warnings.append(f"Template {template_path.name} has low contrast (std: {gray.std():.1f})")

        except ImportError:
            warnings.append("OpenCV not available - skipping template quality checks")
        except Exception as e:
            warnings.append(f"Could not check template quality for {template_path.name}: {e}")

        return warnings

    def _apply_fixes(self, content: Dict[str, Any], errors: List[str]) -> Tuple[Dict[str, Any], bool]:
        """Apply automatic fixes for common issues."""
        fixed_content = content.copy()
        fixed = False

        # Add version field if missing
        if "version" not in fixed_content and any("version" in error for error in errors):
            fixed_content["version"] = 1
            fixed = True

        # Convert relative paths to absolute (if templates directory exists)
        if "logos" in fixed_content:
            for logo in fixed_content["logos"]:
                if "template_path" in logo:
                    template_path = Path(logo["template_path"])
                    if not template_path.is_absolute():
                        # Try to find in templates directory
                        templates_dir = Path("templates")
                        if templates_dir.exists():
                            abs_path = templates_dir / template_path.name
                            if abs_path.exists():
                                logo["template_path"] = str(abs_path)
                                fixed = True

        return fixed_content, fixed

    def validate_directory(self, directory: Path, recursive: bool = False) -> None:
        """Validate all profile files in a directory."""
        if not directory.exists():
            console.print(f"[red]Error: Directory does not exist: {directory}[/red]")
            return

        # Find profile files
        pattern = "**/*" if recursive else "*"
        file_extensions = [".yaml", ".yml", ".json"]

        files = []
        for ext in file_extensions:
            files.extend(directory.glob(f"{pattern}{ext}"))

        if not files:
            console.print(f"[yellow]No profile files found in {directory}[/yellow]")
            return

        console.print(f"\n[bold blue]📋 Validating {len(files)} files in {directory}[/bold blue]")

        for file_path in track(files, description="Validating..."):
            result = self.validate_file(file_path)
            self.validation_results.append(result)

    def print_results(self) -> None:
        """Print validation results in a formatted table."""
        if not self.validation_results:
            console.print("[yellow]No validation results to display[/yellow]")
            return

        # Summary statistics
        total = len(self.validation_results)
        valid = sum(1 for r in self.validation_results if r["valid"])
        invalid = total - valid
        fixed = sum(1 for r in self.validation_results if r["fixed"])

        # Summary panel
        summary_text = f"Total: {total} | Valid: {valid} | Invalid: {invalid}"
        if fixed > 0:
            summary_text += f" | Fixed: {fixed}"

        console.print(Panel(summary_text, title="Validation Summary"))

        # Detailed results table
        table = Table(title="Validation Results")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Errors", style="red")
        table.add_column("Warnings", style="yellow")
        table.add_column("Fixed", justify="center")

        for result in self.validation_results:
            # Status styling
            if result["valid"]:
                status = "[green]✓ VALID[/green]"
            else:
                status = "[red]✗ INVALID[/red]"

            # Format errors and warnings
            errors_text = f"{len(result['errors'])}" if result['errors'] else "—"
            warnings_text = f"{len(result['warnings'])}" if result['warnings'] else "—"
            fixed_text = "[green]✓[/green]" if result['fixed'] else "—"

            table.add_row(
                Path(result["file"]).name,
                status,
                errors_text,
                warnings_text,
                fixed_text
            )

        console.print(table)

        # Show detailed errors for invalid files
        invalid_results = [r for r in self.validation_results if not r["valid"]]
        if invalid_results:
            console.print("\n[bold red]📋 Detailed Errors:[/bold red]")
            for result in invalid_results:
                console.print(f"\n[bold]{Path(result['file']).name}:[/bold]")
                for error in result["errors"]:
                    console.print(f"  [red]✗[/red] {error}")
                for warning in result["warnings"]:
                    console.print(f"  [yellow]⚠[/yellow] {warning}")

        # Show fixes applied
        if self.fixed_files:
            console.print("\n[bold green]🔧 Files automatically fixed:[/bold green]")
            for file_path in self.fixed_files:
                console.print(f"  [green]✓[/green] {file_path}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Align-Press profile files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate single file
  python -m alignpress.cli.validate_profile \\
    profiles/estilos/polo_basico.yaml

  # Validate all files in directory
  python -m alignpress.cli.validate_profile \\
    profiles/estilos/ \\
    --recursive

  # Validate with automatic fixes
  python -m alignpress.cli.validate_profile \\
    profiles/ \\
    --recursive \\
    --fix-common
        """
    )

    # Required argument
    parser.add_argument(
        'path',
        type=str,
        help='Path to profile file or directory'
    )

    # Optional arguments
    parser.add_argument(
        '--schema',
        type=str,
        help='Path to JSON schema file for validation'
    )

    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Validate files recursively in subdirectories'
    )

    parser.add_argument(
        '--fix-common',
        action='store_true',
        help='Attempt to automatically fix common issues'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )

    args = parser.parse_args()

    if args.quiet:
        console.quiet = True

    # Initialize validator
    validator = ProfileValidator(fix_common=args.fix_common)

    path = Path(args.path)
    schema_path = Path(args.schema) if args.schema else None

    try:
        if path.is_file():
            # Validate single file
            result = validator.validate_file(path, schema_path)
            validator.validation_results.append(result)
        elif path.is_dir():
            # Validate directory
            validator.validate_directory(path, args.recursive)
        else:
            console.print(f"[red]Error: Path does not exist: {path}[/red]")
            return 1

        # Print results
        validator.print_results()

        # Return appropriate exit code
        invalid_count = sum(1 for r in validator.validation_results if not r["valid"])
        return 1 if invalid_count > 0 else 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Validation interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


if __name__ == '__main__':
    sys.exit(main())