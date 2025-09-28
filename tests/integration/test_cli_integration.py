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
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_detector_config(self, temp_dir):
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

        config_path = temp_dir / "detector_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        return config_path

    @pytest.fixture
    def sample_profile(self, temp_dir):
        """Create a sample profile file."""
        profile = {
            "version": 1,
            "name": "Test Profile",
            "type": "style",
            "logos": []
        }

        profile_path = temp_dir / "test_profile.yaml"
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
    def test_validate_command_success(self, sample_profile, temp_dir):
        """Test validate command with valid profile."""
        result = self.run_cli_command([
            'validate',
            str(sample_profile),
            '--quiet'
        ])

        assert result.returncode == 0

    @pytest.mark.integration
    def test_validate_command_invalid_file(self, temp_dir):
        """Test validate command with non-existent file."""
        nonexistent_file = temp_dir / "nonexistent.yaml"

        result = self.run_cli_command([
            'validate',
            str(nonexistent_file),
            '--quiet'
        ])

        assert result.returncode == 1

    @pytest.mark.integration
    def test_validate_command_directory(self, temp_dir):
        """Test validate command with directory."""
        # Create multiple profile files
        for i in range(3):
            profile = {
                "version": 1,
                "name": f"Test Profile {i}",
                "type": "style",
                "logos": []
            }

            profile_path = temp_dir / f"profile_{i}.yaml"
            with open(profile_path, 'w') as f:
                yaml.dump(profile, f)

        result = self.run_cli_command([
            'validate',
            str(temp_dir),
            '--quiet'
        ])

        assert result.returncode == 0

    @pytest.mark.integration
    def test_validate_command_with_schema(self, sample_profile):
        """Test validate command with schema validation."""
        # Create a simple JSON schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["version", "name"],
            "properties": {
                "version": {"type": "integer"},
                "name": {"type": "string"}
            }
        }

        schema_path = sample_profile.parent / "test.schema.json"
        with open(schema_path, 'w') as f:
            json.dump(schema, f)

        result = self.run_cli_command([
            'validate',
            str(sample_profile),
            '--schema', str(schema_path),
            '--quiet'
        ])

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
        assert 'Verbose mode enabled' in result.stdout

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

    def test_profile_validation_error_handling(self, temp_dir):
        """Test profile validation error handling."""
        from alignpress.cli.validate_profile import ProfileValidator

        validator = ProfileValidator()

        # Test with non-existent file
        result = validator.validate_file(temp_dir / "nonexistent.yaml")

        assert not result["valid"]
        assert "does not exist" in result["errors"][0]

    def test_invalid_yaml_handling(self, temp_dir):
        """Test handling of invalid YAML files."""
        # Create invalid YAML file
        invalid_yaml = temp_dir / "invalid.yaml"
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

    def test_validate_large_directory(self, temp_dir):
        """Test validate command performance with many files."""
        # Create many profile files
        for i in range(50):
            profile = {
                "version": 1,
                "name": f"Profile {i}",
                "type": "style",
                "logos": []
            }

            profile_path = temp_dir / f"profile_{i:03d}.yaml"
            with open(profile_path, 'w') as f:
                yaml.dump(profile, f)

        from alignpress.cli.validate_profile import ProfileValidator

        validator = ProfileValidator()

        import time
        start_time = time.time()

        validator.validate_directory(temp_dir)

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