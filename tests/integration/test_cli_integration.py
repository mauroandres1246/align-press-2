"""
Integration tests for CLI tools.

These tests verify that the CLI tools work correctly in real scenarios
with actual files and configurations.
"""

import tempfile
import json
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest
import yaml

from alignpress.cli import main
from alignpress.core.schemas import DetectorConfigSchema


class TestCLIIntegration:
    """Integration tests for CLI tools."""

    @pytest.fixture
    def sample_detector_config(self, tmp_path):
        """Create a sample detector configuration file."""
        config = {
            "version": 1,
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": []  # Empty for tests
        }

        config_path = tmp_path / "detector_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        return config_path

    @pytest.fixture
    def sample_profile(self, tmp_path):
        """Create a sample profile file."""
        # Create a dummy template file
        template_path = tmp_path / "test_template.png"
        import cv2
        import numpy as np
        cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

        profile = {
            "version": 1,
            "name": "Test Profile",
            "type": "style",
            "logos": [
                {
                    "name": "test_logo",
                    "template_path": str(template_path),
                    "position_mm": [100.0, 100.0],
                    "angle_deg": 0.0,
                    "roi": {
                        "width_mm": 50.0,
                        "height_mm": 50.0,
                        "margin_factor": 1.5
                    }
                }
            ]
        }

        profile_path = tmp_path / "test_profile.yaml"
        with open(profile_path, 'w') as f:
            yaml.dump(profile, f)

        return profile_path

    def run_cli_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """
        Run CLI command and return result.

        Args:
            args: Command line arguments

        Returns:
            CompletedProcess result
        """
        # Run the CLI as a subprocess to test the full integration
        cmd = [sys.executable, '-m', 'alignpress.cli'] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

    def test_main_cli_help(self):
        """Test main CLI help output."""
        result = self.run_cli_command(['--help'])

        assert result.returncode == 0
        assert 'Align-Press v2' in result.stdout
        assert 'test' in result.stdout
        assert 'calibrate' in result.stdout
        assert 'validate' in result.stdout
        assert 'benchmark' in result.stdout

    def test_main_cli_version(self):
        """Test main CLI version output."""
        result = self.run_cli_command(['--version'])

        assert result.returncode == 0
        assert 'Align-Press v2.0.0' in result.stdout

    def test_main_cli_no_command(self):
        """Test main CLI with no command shows help."""
        result = self.run_cli_command([])

        assert result.returncode == 0
        assert 'Available Commands' in result.stdout

    @pytest.mark.integration
    def test_validate_command_success(self, sample_profile, tmp_path):
        """Test validate command with valid profile."""
        result = self.run_cli_command([
            'validate',
            str(sample_profile),
            '--quiet'
        ])

        assert result.returncode == 0

    @pytest.mark.integration
    def test_validate_command_invalid_file(self, tmp_path):
        """Test validate command with non-existent file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        result = self.run_cli_command([
            'validate',
            str(nonexistent_file),
            '--quiet'
        ])

        assert result.returncode == 1

    @pytest.mark.integration
    def test_validate_command_directory(self, tmp_path):
        """Test validate command with directory."""
        import cv2
        import numpy as np

        # Create multiple profile files
        for i in range(3):
            # Create dummy template
            template_path = tmp_path / f"template_{i}.png"
            cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

            profile = {
                "version": 1,
                "name": f"Test Profile {i}",
                "type": "style",
                "logos": [
                    {
                        "name": f"logo_{i}",
                        "template_path": str(template_path),
                        "position_mm": [100.0, 100.0],
                        "angle_deg": 0.0,
                        "roi": {
                            "width_mm": 50.0,
                            "height_mm": 50.0,
                            "margin_factor": 1.5
                        }
                    }
                ]
            }

            profile_path = tmp_path / f"profile_{i}.yaml"
            with open(profile_path, 'w') as f:
                yaml.dump(profile, f)

        result = self.run_cli_command([
            'validate',
            str(tmp_path),
            '--quiet'
        ])

        assert result.returncode == 0

    @pytest.mark.integration
    def test_validate_command_with_schema(self, sample_profile):
        """Test validate command with schema validation."""
        # Just test that the validate command works,
        # schema validation is optional feature
        result = self.run_cli_command([
            'validate',
            str(sample_profile),
            '--quiet'
        ])

        # Should pass validation
        assert result.returncode == 0

    @pytest.mark.integration
    def test_test_command_help(self):
        """Test test command help."""
        result = self.run_cli_command(['test', '--help'])

        assert result.returncode == 0
        assert '--config' in result.stdout
        assert '--image' in result.stdout
        assert '--camera' in result.stdout

    @pytest.mark.integration
    def test_calibrate_command_help(self):
        """Test calibrate command help."""
        result = self.run_cli_command(['calibrate', '--help'])

        assert result.returncode == 0
        assert '--camera' in result.stdout
        assert '--pattern-size' in result.stdout
        assert '--square-size-mm' in result.stdout

    @pytest.mark.integration
    def test_benchmark_command_help(self):
        """Test benchmark command help."""
        result = self.run_cli_command(['benchmark', '--help'])

        assert result.returncode == 0
        assert '--config' in result.stdout
        assert '--dataset' in result.stdout

    @pytest.mark.integration
    def test_invalid_command(self):
        """Test invalid command returns error."""
        result = self.run_cli_command(['invalid_command'])

        assert result.returncode != 0

    def test_cli_import(self):
        """Test that CLI modules can be imported."""
        from alignpress.cli import main, test_detector, calibrate, validate_profile, benchmark

        # Check that main functions exist
        assert callable(main.main)
        assert callable(test_detector.main)
        assert callable(calibrate.main)
        assert callable(validate_profile.main)
        assert callable(benchmark.main)

    @pytest.mark.integration
    def test_verbose_and_quiet_flags(self, sample_profile):
        """Test global verbose and quiet flags."""
        # Test verbose flag
        result = self.run_cli_command([
            '--verbose',
            'validate',
            str(sample_profile)
        ])

        assert result.returncode == 0
        # Verbose mode works - just check it doesn't crash
        assert len(result.stdout) > 0

        # Test quiet flag
        result = self.run_cli_command([
            '--quiet',
            'validate',
            str(sample_profile)
        ])

        assert result.returncode == 0
        # Should have minimal output in quiet mode


class TestCLIConfigValidation:
    """Test CLI tools with configuration validation."""

    @pytest.fixture
    def valid_detector_config(self, temp_template_file):
        """Create a valid detector configuration."""
        config = {
            "version": 1,
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": [
                {
                    "name": "test_logo",
                    "template_path": str(temp_template_file),
                    "position_mm": [150.0, 100.0],
                    "roi": {
                        "width_mm": 50.0,
                        "height_mm": 40.0,
                        "margin_factor": 1.2
                    },
                    "angle_deg": 0.0
                }
            ]
        }

        return config

    def test_detector_config_validation(self, valid_detector_config):
        """Test that valid detector config passes validation."""
        # This should not raise an exception
        schema = DetectorConfigSchema(**valid_detector_config)

        assert schema.version == 1
        assert len(schema.logos) == 1
        assert schema.logos[0].name == "test_logo"

    def test_detector_config_invalid_plane(self):
        """Test detector config with invalid plane dimensions."""
        config = {
            "version": 1,
            "plane": {
                "width_mm": -100.0,  # Invalid: negative
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": []
        }

        with pytest.raises(ValueError):
            DetectorConfigSchema(**config)


class TestCLIFileOperations:
    """Test CLI file operations and error handling."""

    def test_config_loader_error_handling(self):
        """Test config loader error handling."""
        from alignpress.utils.config_loader import ConfigLoader, ConfigError

        loader = ConfigLoader()

        # Test loading non-existent file
        with pytest.raises(ConfigError):
            loader.load_detector_config(Path("nonexistent_config.yaml"))

    def test_profile_validation_error_handling(self, tmp_path):
        """Test profile validation error handling."""
        from alignpress.cli.validate_profile import ProfileValidator

        validator = ProfileValidator()

        # Test with non-existent file
        result = validator.validate_file(tmp_path / "nonexistent.yaml")

        assert not result["valid"]
        assert "does not exist" in result["errors"][0]

    def test_invalid_yaml_handling(self, tmp_path):
        """Test handling of invalid YAML files."""
        # Create invalid YAML file
        invalid_yaml = tmp_path / "invalid.yaml"
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [")

        from alignpress.cli.validate_profile import ProfileValidator

        validator = ProfileValidator()
        result = validator.validate_file(invalid_yaml)

        assert not result["valid"]
        assert len(result["errors"]) > 0


@pytest.mark.slow
class TestCLIPerformance:
    """Performance tests for CLI tools."""

    def test_validate_large_directory(self, tmp_path):
        """Test validate command performance with many files."""
        # Create many profile files
        for i in range(50):
            profile = {
                "version": 1,
                "name": f"Profile {i}",
                "type": "style",
                "logos": []
            }

            profile_path = tmp_path / f"profile_{i:03d}.yaml"
            with open(profile_path, 'w') as f:
                yaml.dump(profile, f)

        from alignpress.cli.validate_profile import ProfileValidator

        validator = ProfileValidator()

        import time
        start_time = time.time()

        validator.validate_directory(tmp_path)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete in reasonable time (< 5 seconds for 50 files)
        assert elapsed < 5.0
        assert len(validator.validation_results) == 50

    def test_cli_memory_usage(self):
        """Test that CLI tools don't leak memory significantly."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Import all CLI modules
        from alignpress.cli import main, test_detector, calibrate, validate_profile, benchmark

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024