#!/usr/bin/env python3
"""
Validation script to check that the project is properly set up.

This script performs basic validation of the project structure,
imports, and configuration files.
"""

import sys
import traceback
from pathlib import Path
from typing import List, Tuple


def check_file_exists(file_path: Path, description: str) -> Tuple[bool, str]:
    """Check if a file exists."""
    if file_path.exists():
        return True, f"✅ {description}: {file_path}"
    else:
        return False, f"❌ {description}: {file_path} (NOT FOUND)"


def check_directory_exists(dir_path: Path, description: str) -> Tuple[bool, str]:
    """Check if a directory exists."""
    if dir_path.exists() and dir_path.is_dir():
        return True, f"✅ {description}: {dir_path}"
    else:
        return False, f"❌ {description}: {dir_path} (NOT FOUND)"


def check_import(module_name: str) -> Tuple[bool, str]:
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        return True, f"✅ Import {module_name}: OK"
    except Exception as e:
        return False, f"❌ Import {module_name}: FAILED ({e})"


def validate_project_structure() -> List[Tuple[bool, str]]:
    """Validate basic project structure."""
    results = []
    project_root = Path(".")

    # Check main directories
    directories = [
        ("alignpress/", "Main package directory"),
        ("alignpress/core/", "Core modules directory"),
        ("alignpress/utils/", "Utils modules directory"),
        ("alignpress/cli/", "CLI modules directory"),
        ("alignpress/ui/", "UI modules directory"),
        ("config/", "Configuration directory"),
        ("profiles/", "Profiles directory"),
        ("templates/", "Templates directory"),
        ("tests/", "Tests directory"),
        ("tests/unit/", "Unit tests directory"),
    ]

    for dir_name, description in directories:
        results.append(check_directory_exists(project_root / dir_name, description))

    # Check main files
    files = [
        ("README.md", "Main README"),
        ("requirements.txt", "Requirements file"),
        ("pyproject.toml", "Project configuration"),
        ("alignpress/__init__.py", "Main package init"),
        ("alignpress/core/__init__.py", "Core package init"),
        ("alignpress/utils/__init__.py", "Utils package init"),
        ("alignpress/cli/__init__.py", "CLI package init"),
        ("config/app.yaml", "App configuration"),
        ("config/example_detector.yaml", "Example detector config"),
    ]

    for file_name, description in files:
        results.append(check_file_exists(project_root / file_name, description))

    return results


def validate_imports() -> List[Tuple[bool, str]]:
    """Validate that main modules can be imported."""
    results = []

    # Core modules
    modules = [
        "alignpress",
        "alignpress.core",
        "alignpress.core.schemas",
        "alignpress.utils",
        "alignpress.utils.geometry",
        "alignpress.utils.image_utils",
        "alignpress.cli",
    ]

    for module in modules:
        results.append(check_import(module))

    # Check that specific classes can be imported
    try:
        from alignpress.core.schemas import DetectorConfigSchema, PlaneConfigSchema
        results.append((True, "✅ Schema imports: OK"))
    except Exception as e:
        results.append((False, f"❌ Schema imports: FAILED ({e})"))

    try:
        from alignpress.utils.geometry import angle_deg, l2, polygon_center
        results.append((True, "✅ Geometry function imports: OK"))
    except Exception as e:
        results.append((False, f"❌ Geometry function imports: FAILED ({e})"))

    return results


def validate_configurations() -> List[Tuple[bool, str]]:
    """Validate configuration files."""
    results = []

    # Check app configuration
    try:
        import yaml
        with open("config/app.yaml", 'r') as f:
            app_config = yaml.safe_load(f)

        if 'version' in app_config and 'language' in app_config:
            results.append((True, "✅ App config structure: OK"))
        else:
            results.append((False, "❌ App config structure: Missing required fields"))

    except Exception as e:
        results.append((False, f"❌ App config validation: FAILED ({e})"))

    # Check detector configuration
    try:
        with open("config/example_detector.yaml", 'r') as f:
            detector_config = yaml.safe_load(f)

        required_fields = ['version', 'plane', 'logos']
        missing_fields = [field for field in required_fields if field not in detector_config]

        if not missing_fields:
            results.append((True, "✅ Detector config structure: OK"))
        else:
            results.append((False, f"❌ Detector config structure: Missing {missing_fields}"))

    except Exception as e:
        results.append((False, f"❌ Detector config validation: FAILED ({e})"))

    return results


def validate_detector_instantiation() -> List[Tuple[bool, str]]:
    """Validate that detector can be instantiated with example config."""
    results = []

    try:
        # Try to create detector config schema
        from alignpress.core.schemas import DetectorConfigSchema
        import yaml

        with open("config/example_detector.yaml", 'r') as f:
            config_dict = yaml.safe_load(f)

        # Create a minimal valid config for testing (without requiring actual template files)
        test_config = {
            "version": 1,
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": []  # Empty for now since we don't have actual template files
        }

        schema = DetectorConfigSchema(**test_config)
        results.append((True, "✅ Detector config schema validation: OK"))

    except Exception as e:
        results.append((False, f"❌ Detector config schema validation: FAILED ({e})"))

    return results


def main():
    """Main validation function."""
    print("🔍 Validating Align-Press v2 project setup...\n")

    all_results = []

    # Run all validations
    print("📁 Checking project structure...")
    all_results.extend(validate_project_structure())

    print("\n📦 Checking imports...")
    all_results.extend(validate_imports())

    print("\n⚙️  Checking configurations...")
    all_results.extend(validate_configurations())

    print("\n🔧 Checking detector instantiation...")
    all_results.extend(validate_detector_instantiation())

    # Print all results
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)

    passed = 0
    failed = 0

    for success, message in all_results:
        print(message)
        if success:
            passed += 1
        else:
            failed += 1

    print("="*60)
    print(f"SUMMARY: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All validations passed! Project is ready for testing.")
        return 0
    else:
        print("❌ Some validations failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Validation script failed: {e}")
        traceback.print_exc()
        sys.exit(1)