"""Integration tests for CLI benchmark tool."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import cv2

from alignpress.cli.benchmark import PerformanceBenchmark


class TestPerformanceBenchmark:
    """Test PerformanceBenchmark class."""

    @pytest.fixture
    def benchmark(self, tmp_path):
        """Create benchmark instance."""
        config_path = tmp_path / "config.yaml"
        return PerformanceBenchmark(config_path=config_path)

    @pytest.fixture
    def valid_config_yaml(self, tmp_path):
        """Create valid config with at least one logo."""
        import yaml

        # Create a minimal template
        template_path = tmp_path / "template.png"
        cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

        config_path = tmp_path / "config.yaml"
        config_data = {
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": [{
                "name": "test_logo",
                "template_path": str(template_path),
                "position_mm": [150.0, 100.0],
                "roi": {"width_mm": 50.0, "height_mm": 40.0}
            }],
            "thresholds": {
                "max_deviation_mm": 5.0,
                "max_angle_error_deg": 10.0,
                "min_inliers": 10,
                "max_reproj_error_px": 3.0
            },
            "features": {
                "feature_type": "ORB",
                "nfeatures": 500
            }
        }
        config_path.write_text(yaml.dump(config_data))
        return config_path

    def test_benchmark_initialization(self, benchmark, tmp_path):
        """Test benchmark initializes correctly."""
        assert benchmark.config_path == tmp_path / "config.yaml"
        assert benchmark.detector is None
        assert benchmark.results == []
        assert isinstance(benchmark.system_info, dict)

    def test_get_system_info(self, benchmark):
        """Test system info collection."""
        info = benchmark.system_info

        assert "cpu_count" in info
        assert "memory_total_gb" in info
        assert "python_version" in info
        assert "opencv_version" in info
        assert info["cpu_count"] > 0
        assert info["memory_total_gb"] > 0

    def test_load_detector_file_not_found(self, benchmark):
        """Test loading detector with missing file."""
        result = benchmark.load_detector()

        assert result is False
        assert benchmark.detector is None

    def test_load_detector_success_yaml(self, benchmark, valid_config_yaml):
        """Test successful detector loading from YAML."""
        benchmark.config_path = valid_config_yaml
        result = benchmark.load_detector()

        assert result is True
        assert benchmark.detector is not None

    def test_load_dataset_directory_not_found(self, benchmark, tmp_path):
        """Test loading dataset from non-existent directory."""
        dataset_path = tmp_path / "nonexistent"

        image_files = benchmark.load_dataset(dataset_path)

        assert len(image_files) == 0

    def test_load_dataset_empty_directory(self, benchmark, tmp_path):
        """Test loading dataset from empty directory."""
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()

        image_files = benchmark.load_dataset(dataset_path)

        assert len(image_files) == 0

    def test_load_dataset_with_images(self, benchmark, tmp_path):
        """Test loading dataset with image files."""
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()

        # Create test images
        for i in range(3):
            img_path = dataset_path / f"test_{i}.jpg"
            cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        image_files = benchmark.load_dataset(dataset_path)

        assert len(image_files) == 3
        assert all(f.suffix == '.jpg' for f in image_files)

    def test_load_dataset_single_file(self, benchmark, tmp_path):
        """Test loading dataset with single file."""
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        image_files = benchmark.load_dataset(img_path)

        assert len(image_files) == 1
        assert image_files[0] == img_path

    def test_load_dataset_mixed_extensions(self, benchmark, tmp_path):
        """Test loading dataset with mixed extensions."""
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()

        # Create images with different extensions
        for ext in ['.jpg', '.png', '.bmp']:
            img_path = dataset_path / f"test{ext}"
            cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        image_files = benchmark.load_dataset(dataset_path)

        assert len(image_files) == 3

    def test_benchmark_single_image_invalid_path(self, benchmark, tmp_path):
        """Test benchmarking with invalid image path."""
        # Mock detector
        benchmark.detector = MagicMock()

        img_path = tmp_path / "nonexistent.jpg"
        result = benchmark.benchmark_single_image(img_path)

        assert result["success"] is False
        assert result["error"] == "Could not load image"

    def test_benchmark_single_image_success(self, benchmark, tmp_path):
        """Test successful image benchmarking."""
        # Create test image
        img_path = tmp_path / "test.jpg"
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(img_path), test_image)

        # Mock detector
        mock_detector = MagicMock()
        mock_result = MagicMock()
        mock_result.dict.return_value = {"logo_name": "test", "found": True}
        mock_detector.detect_logos.return_value = [mock_result]
        benchmark.detector = mock_detector

        result = benchmark.benchmark_single_image(img_path)

        assert result["success"] is True
        assert "timing" in result
        assert "detection_ms" in result["timing"]
        assert "memory" in result
        assert "detection_results" in result
        assert len(result["detection_results"]) == 1

    def test_benchmark_single_image_timing_metrics(self, benchmark, tmp_path):
        """Test benchmark captures timing metrics."""
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        mock_detector = MagicMock()
        mock_detector.detect_logos.return_value = []
        benchmark.detector = mock_detector

        result = benchmark.benchmark_single_image(img_path)

        assert result["success"] is True
        assert "load_ms" in result["timing"]
        assert "detection_ms" in result["timing"]
        assert "total_ms" in result["timing"]
        assert result["timing"]["total_ms"] >= result["timing"]["detection_ms"]

    def test_benchmark_single_image_memory_metrics(self, benchmark, tmp_path):
        """Test benchmark captures memory metrics."""
        img_path = tmp_path / "test.jpg"
        cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        mock_detector = MagicMock()
        mock_detector.detect_logos.return_value = []
        benchmark.detector = mock_detector

        result = benchmark.benchmark_single_image(img_path)

        assert result["success"] is True
        assert "before_mb" in result["memory"]
        assert "after_load_mb" in result["memory"]
        assert "after_detection_mb" in result["memory"]
        assert "peak_usage_mb" in result["memory"]

    def test_benchmark_single_image_includes_image_size(self, benchmark, tmp_path):
        """Test benchmark includes image size info."""
        img_path = tmp_path / "test.jpg"
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite(str(img_path), test_image)

        mock_detector = MagicMock()
        mock_detector.detect_logos.return_value = []
        benchmark.detector = mock_detector

        result = benchmark.benchmark_single_image(img_path)

        assert result["success"] is True
        assert result["image_size"]["width"] == 640
        assert result["image_size"]["height"] == 480
        assert result["image_size"]["channels"] == 3

    def test_save_results_creates_file(self, benchmark, tmp_path):
        """Test saving benchmark results."""
        output_path = tmp_path / "results.json"
        analysis = {
            "summary": {
                "total_images": 5,
                "successful": 5,
                "failed": 0
            },
            "timing": {
                "mean_ms": 100.0,
                "median_ms": 95.0
            }
        }

        result = benchmark.save_results(output_path, analysis)

        assert result is True
        assert output_path.exists()

        # Verify content - results are nested under "analysis"
        with open(output_path) as f:
            data = json.load(f)
            assert "analysis" in data
            assert data["analysis"]["summary"]["total_images"] == 5


class TestBenchmarkIntegration:
    """Integration tests for benchmark workflow."""

    def test_full_benchmark_workflow(self, tmp_path):
        """Test complete benchmark workflow."""
        import yaml

        # Create template
        template_path = tmp_path / "template.png"
        cv2.imwrite(str(template_path), np.zeros((50, 50, 3), dtype=np.uint8))

        # Create config
        config_path = tmp_path / "config.yaml"
        config_data = {
            "plane": {
                "width_mm": 300.0,
                "height_mm": 200.0,
                "mm_per_px": 0.5
            },
            "logos": [{
                "name": "test_logo",
                "template_path": str(template_path),
                "position_mm": [150.0, 100.0],
                "roi": {"width_mm": 50.0, "height_mm": 40.0}
            }],
            "thresholds": {
                "max_deviation_mm": 5.0,
                "max_angle_error_deg": 10.0,
                "min_inliers": 10,
                "max_reproj_error_px": 3.0
            },
            "features": {
                "feature_type": "ORB",
                "nfeatures": 500
            }
        }
        config_path.write_text(yaml.dump(config_data))

        # Create dataset
        dataset_path = tmp_path / "dataset"
        dataset_path.mkdir()
        for i in range(2):
            img_path = dataset_path / f"img_{i}.jpg"
            cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

        # Create benchmark
        benchmark = PerformanceBenchmark(config_path)

        # Load detector
        assert benchmark.load_detector() is True

        # Load dataset
        images = benchmark.load_dataset(dataset_path)
        assert len(images) == 2

        # Benchmark images
        for img in images:
            result = benchmark.benchmark_single_image(img)
            assert result["success"] is True
            benchmark.results.append(result)

        assert len(benchmark.results) == 2
