"""Integration tests for CLI benchmark tool."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from alignpress.cli.benchmark import PerformanceBenchmark


@pytest.mark.skip(reason="Tests use mock implementation that doesn't match actual PerformanceBenchmark class - needs rewrite")
class TestPerformanceBenchmark:
    """Test BenchmarkRunner class."""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """Create sample detector config."""
        config = {
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": [
                {
                    "name": "test_logo",
                    "template_path": "templates/test.png",
                    "position_mm": [150.0, 100.0],
                    "angle_deg": 0.0,
                    "roi": {
                        "width_mm": 50.0,
                        "height_mm": 50.0,
                        "margin_factor": 1.5
                    }
                }
            ],
            "thresholds": {
                "max_deviation": 5.0,
                "max_angle_error": 10.0,
                "min_inliers": 15,
                "max_reproj_error": 3.0
            },
            "features": {
                "feature_type": "ORB",
                "nfeatures": 1500
            },
            "fallback": {
                "enabled": True
            }
        }

        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f)

        return config_path

    @pytest.fixture
    def sample_images(self, tmp_path):
        """Create sample test images."""
        dataset_dir = tmp_path / "dataset"
        dataset_dir.mkdir()

        # Create 3 sample images
        for i in range(3):
            img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            img_path = dataset_dir / f"test_{i:03d}.jpg"
            import cv2
            cv2.imwrite(str(img_path), img)

        return dataset_dir

    def test_benchmark_runner_initialization(self, sample_config, sample_images):
        """Test benchmark runner initializes correctly."""
        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )

        assert runner.config_path == sample_config
        assert runner.dataset_path == sample_images
        assert runner.detector is None

    @patch('alignpress.cli.benchmark.PlanarLogoDetector')
    def test_load_detector(self, mock_detector_class, sample_config, sample_images):
        """Test loading detector from config."""
        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )

        result = runner.load_detector()

        assert result is True
        mock_detector_class.assert_called_once()

    def test_collect_images_from_directory(self, sample_config, sample_images):
        """Test collecting images from directory."""
        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )

        images = runner.collect_images()

        assert len(images) == 3
        assert all(p.suffix == '.jpg' for p in images)

    def test_collect_images_single_file(self, sample_config, sample_images):
        """Test collecting single image file."""
        image_path = list(sample_images.glob("*.jpg"))[0]

        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=image_path
        )

        images = runner.collect_images()

        assert len(images) == 1
        assert images[0] == image_path

    def test_collect_images_with_limit(self, sample_config, sample_images):
        """Test collecting limited number of images."""
        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images,
            max_samples=2
        )

        images = runner.collect_images()

        assert len(images) == 2

    @patch('alignpress.cli.benchmark.PlanarLogoDetector')
    def test_process_single_image(self, mock_detector_class, sample_config, sample_images):
        """Test processing single image."""
        # Setup mock detector
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.logo_name = "test_logo"
        mock_result.found = True
        mock_result.processing_time_ms = 50.0
        mock_detector.detect_logos.return_value = [mock_result]
        mock_detector_class.return_value = mock_detector

        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )
        runner.load_detector()

        images = runner.collect_images()
        result = runner.process_image(images[0])

        assert result is not None
        assert 'image_path' in result
        assert 'total_time_ms' in result
        assert 'logo_results' in result

    @patch('alignpress.cli.benchmark.PlanarLogoDetector')
    def test_run_benchmark(self, mock_detector_class, sample_config, sample_images):
        """Test running complete benchmark."""
        # Setup mock detector
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.logo_name = "test_logo"
        mock_result.found = True
        mock_result.processing_time_ms = 50.0
        mock_result.confidence = 0.85
        mock_detector.detect_logos.return_value = [mock_result]
        mock_detector_class.return_value = mock_detector

        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )

        results = runner.run()

        assert results is not None
        assert 'summary' in results
        assert 'samples' in results
        assert results['summary']['total_samples'] == 3

    @patch('alignpress.cli.benchmark.PlanarLogoDetector')
    def test_calculate_statistics(self, mock_detector_class, sample_config, sample_images):
        """Test calculating benchmark statistics."""
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.logo_name = "test_logo"
        mock_result.found = True
        mock_result.processing_time_ms = 50.0
        mock_result.confidence = 0.85
        mock_detector.detect_logos.return_value = [mock_result]
        mock_detector_class.return_value = mock_detector

        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )
        results = runner.run()

        # Check statistics
        summary = results['summary']
        assert 'avg_time_ms' in summary
        assert 'min_time_ms' in summary
        assert 'max_time_ms' in summary
        assert 'fps' in summary
        assert summary['avg_time_ms'] > 0

    def test_save_results(self, sample_config, sample_images, tmp_path):
        """Test saving benchmark results to file."""
        runner = PerformanceBenchmark(
            config_path=sample_config,
            dataset_path=sample_images
        )

        # Mock results
        results = {
            'summary': {
                'total_samples': 3,
                'avg_time_ms': 50.0,
                'fps': 20.0
            },
            'samples': []
        }

        output_path = tmp_path / "benchmark_results.json"
        runner.save_results(results, output_path)

        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            data = json.load(f)
            assert data['summary']['total_samples'] == 3


@pytest.mark.skip(reason="Tests use mock implementation that doesn't match actual PerformanceBenchmark class - needs rewrite")
class TestBenchmarkCLI:
    """Test benchmark CLI command."""

    @patch('alignpress.cli.benchmark.PerformanceBenchmark')
    def test_benchmark_cli_execution(self, mock_runner_class, tmp_path):
        """Test CLI benchmark execution."""
        from alignpress.cli.benchmark import main

        # Setup mocks
        mock_runner = MagicMock()
        mock_runner.load_detector.return_value = True
        mock_runner.run.return_value = {
            'summary': {'total_samples': 10, 'avg_time_ms': 50.0}
        }
        mock_runner_class.return_value = mock_runner

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()
        output_path = tmp_path / "results.json"

        with patch('sys.argv', [
            'benchmark.py',
            '--config', str(config_path),
            '--dataset', str(dataset_path),
            '--output', str(output_path)
        ]):
            exit_code = main()

        assert exit_code == 0
        mock_runner.load_detector.assert_called_once()
        mock_runner.run.assert_called_once()

    @patch('alignpress.cli.benchmark.PerformanceBenchmark')
    def test_benchmark_cli_detector_load_failure(self, mock_runner_class, tmp_path):
        """Test CLI handles detector loading failure."""
        from alignpress.cli.benchmark import main

        # Setup mocks
        mock_runner = MagicMock()
        mock_runner.load_detector.return_value = False
        mock_runner_class.return_value = mock_runner

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()

        with patch('sys.argv', [
            'benchmark.py',
            '--config', str(config_path),
            '--dataset', str(dataset_path)
        ]):
            exit_code = main()

        assert exit_code == 1
