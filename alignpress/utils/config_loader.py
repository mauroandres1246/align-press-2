"""
Centralized configuration loading and management.

This module provides utilities for loading and validating application
configurations from various sources (files, environment variables).
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json

import yaml
from pydantic import ValidationError

from ..core.schemas import AppConfigSchema, DetectorConfigSchema, CalibrationDataSchema


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class ConfigLoader:
    """
    Centralized configuration loader with caching and validation.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize config loader.

        Args:
            base_path: Base path for resolving relative paths (defaults to current directory)
        """
        self.base_path = base_path or Path.cwd()
        self._cache: Dict[str, Any] = {}

    def load_app_config(self, config_path: Optional[Path] = None) -> AppConfigSchema:
        """
        Load application configuration.

        Args:
            config_path: Path to config file (defaults to config/app.yaml)

        Returns:
            Validated application configuration

        Raises:
            ConfigError: If configuration is invalid or cannot be loaded
        """
        if config_path is None:
            config_path = self.base_path / "config" / "app.yaml"

        cache_key = f"app_config:{config_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Load config with environment variable substitution
            config_dict = self._load_file_with_env_substitution(config_path)

            # Resolve paths relative to base path
            config_dict = self._resolve_paths(config_dict)

            # Validate and create schema
            config = AppConfigSchema(**config_dict)

            # Cache the result
            self._cache[cache_key] = config

            return config

        except Exception as e:
            raise ConfigError(f"Failed to load app config from {config_path}: {e}")

    def load_detector_config(self, config_path: Path) -> DetectorConfigSchema:
        """
        Load detector configuration.

        Args:
            config_path: Path to detector config file

        Returns:
            Validated detector configuration

        Raises:
            ConfigError: If configuration is invalid or cannot be loaded
        """
        cache_key = f"detector_config:{config_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            config_dict = self._load_file_with_env_substitution(config_path)
            config_dict = self._resolve_paths(config_dict)

            # Validate template paths exist
            if "logos" in config_dict:
                for logo in config_dict["logos"]:
                    if "template_path" in logo:
                        template_path = Path(logo["template_path"])
                        if not template_path.is_absolute():
                            template_path = self.base_path / template_path

                        if not template_path.exists():
                            raise ConfigError(f"Template file not found: {template_path}")

                        # Update path to absolute
                        logo["template_path"] = str(template_path)

            config = DetectorConfigSchema(**config_dict)
            self._cache[cache_key] = config

            return config

        except Exception as e:
            raise ConfigError(f"Failed to load detector config from {config_path}: {e}")

    def load_calibration_data(self, calibration_path: Path) -> CalibrationDataSchema:
        """
        Load camera calibration data.

        Args:
            calibration_path: Path to calibration file

        Returns:
            Validated calibration data

        Raises:
            ConfigError: If calibration data is invalid or cannot be loaded
        """
        cache_key = f"calibration:{calibration_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            calibration_dict = self._load_file_with_env_substitution(calibration_path)
            calibration = CalibrationDataSchema(**calibration_dict)

            self._cache[cache_key] = calibration
            return calibration

        except Exception as e:
            raise ConfigError(f"Failed to load calibration data from {calibration_path}: {e}")

    def _load_file_with_env_substitution(self, file_path: Path) -> Dict[str, Any]:
        """
        Load file with environment variable substitution.

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration dictionary with environment variables substituted

        Raises:
            ConfigError: If file cannot be loaded or parsed
        """
        if not file_path.exists():
            raise ConfigError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Substitute environment variables
            content = self._substitute_env_vars(content)

            # Parse based on file extension
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            else:
                return json.loads(content)

        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {file_path}: {e}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ConfigError(f"Error reading {file_path}: {e}")

    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in configuration content.

        Supports formats:
        - ${VAR_NAME}
        - ${VAR_NAME:default_value}

        Args:
            content: Configuration file content

        Returns:
            Content with environment variables substituted
        """
        import re

        def replace_env_var(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                return os.getenv(var_name, default_value)
            else:
                var_name = var_expr
                value = os.getenv(var_name)
                if value is None:
                    raise ConfigError(f"Environment variable {var_name} not found")
                return value

        # Replace ${VAR_NAME} and ${VAR_NAME:default}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_env_var, content)

    def _resolve_paths(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve relative paths in configuration dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Configuration with resolved paths
        """
        resolved_config = config_dict.copy()

        # Common path fields to resolve
        path_fields = [
            'profiles_path', 'templates_path', 'calibration_path',
            'datasets_path', 'logs_path', 'log_output_path'
        ]

        for field in path_fields:
            if field in resolved_config:
                path_value = resolved_config[field]
                if isinstance(path_value, str):
                    path_obj = Path(path_value)
                    if not path_obj.is_absolute():
                        resolved_config[field] = str(self.base_path / path_obj)

        return resolved_config

    def create_default_app_config(self, output_path: Optional[Path] = None) -> AppConfigSchema:
        """
        Create default application configuration file.

        Args:
            output_path: Path to save config (defaults to config/app.yaml)

        Returns:
            Default configuration schema

        Raises:
            ConfigError: If configuration cannot be created
        """
        if output_path is None:
            output_path = self.base_path / "config" / "app.yaml"

        try:
            # Create default config
            default_config = AppConfigSchema()

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            config_dict = default_config.dict()
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)

            return default_config

        except Exception as e:
            raise ConfigError(f"Failed to create default config at {output_path}: {e}")

    def validate_paths_exist(self, config: AppConfigSchema) -> Dict[str, bool]:
        """
        Validate that configured paths exist.

        Args:
            config: Application configuration

        Returns:
            Dictionary mapping path names to existence status
        """
        paths_to_check = {
            'profiles_path': config.profiles_path,
            'templates_path': config.templates_path,
            'calibration_path': config.calibration_path,
            'datasets_path': config.datasets_path,
            'logs_path': config.logs_path,
        }

        return {name: Path(path).exists() for name, path in paths_to_check.items()}

    def create_missing_directories(self, config: AppConfigSchema) -> None:
        """
        Create missing directories from configuration.

        Args:
            config: Application configuration

        Raises:
            ConfigError: If directories cannot be created
        """
        directories = [
            config.profiles_path,
            config.templates_path,
            config.calibration_path,
            config.datasets_path,
            config.logs_path,
            config.log_output_path,
        ]

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigError(f"Failed to create directory {directory}: {e}")

    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._cache.clear()

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about cached configurations.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_items": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "memory_usage_estimate": sum(
                len(str(value)) for value in self._cache.values()
            )
        }


# Global config loader instance
_global_config_loader: Optional[ConfigLoader] = None


def get_config_loader(base_path: Optional[Path] = None) -> ConfigLoader:
    """
    Get global configuration loader instance.

    Args:
        base_path: Base path for configuration (only used on first call)

    Returns:
        Global ConfigLoader instance
    """
    global _global_config_loader

    if _global_config_loader is None:
        _global_config_loader = ConfigLoader(base_path)

    return _global_config_loader


def load_app_config(config_path: Optional[Path] = None) -> AppConfigSchema:
    """
    Convenience function to load application configuration.

    Args:
        config_path: Path to config file

    Returns:
        Application configuration
    """
    loader = get_config_loader()
    return loader.load_app_config(config_path)


def load_detector_config(config_path: Path) -> DetectorConfigSchema:
    """
    Convenience function to load detector configuration.

    Args:
        config_path: Path to detector config file

    Returns:
        Detector configuration
    """
    loader = get_config_loader()
    return loader.load_detector_config(config_path)


def load_calibration_data(calibration_path: Path) -> CalibrationDataSchema:
    """
    Convenience function to load calibration data.

    Args:
        calibration_path: Path to calibration file

    Returns:
        Calibration data
    """
    loader = get_config_loader()
    return loader.load_calibration_data(calibration_path)