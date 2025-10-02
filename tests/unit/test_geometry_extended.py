"""Extended tests for geometry utilities."""

import pytest
import numpy as np
import math

from alignpress.utils.geometry import (
    angle_deg, l2, polygon_center, angle_diff_circular,
    point_distance_to_line, rotate_point
)


class TestAngleCalculations:
    """Test angle calculation functions."""

    def test_angle_deg_basic(self):
        """Test basic angle calculations."""
        # Horizontal line (0 degrees)
        assert abs(angle_deg((0, 0), (1, 0))) < 0.1

        # Vertical line (90 degrees)
        assert abs(angle_deg((0, 0), (0, 1)) - 90.0) < 0.1

        # 45 degree line
        assert abs(angle_deg((0, 0), (1, 1)) - 45.0) < 0.1

        # -45 degree line
        assert abs(angle_deg((0, 0), (1, -1)) - (-45.0)) < 0.1

    def test_angle_diff_circular(self):
        """Test circular angle difference."""
        # Same angle
        assert angle_diff_circular(0, 0) == 0

        # Small difference
        assert angle_diff_circular(10, 15) == 5

        # Wrap around
        assert abs(angle_diff_circular(350, 10) - 20) < 0.1

        # Negative wrap
        assert abs(angle_diff_circular(10, 350) - (-20)) < 0.1

        # 180 degree difference
        assert abs(angle_diff_circular(0, 180)) == 180


class TestDistanceCalculations:
    """Test distance calculation functions."""

    def test_l2_distance(self):
        """Test L2 distance calculations."""
        # Distance between same point
        assert l2((0, 0), (0, 0)) == 0

        # Distance along X axis
        assert l2((0, 0), (3, 0)) == 3

        # Distance along Y axis
        assert l2((0, 0), (0, 4)) == 4

        # Pythagorean triple
        assert l2((0, 0), (3, 4)) == 5

    def test_l2_with_negative_coords(self):
        """Test L2 distance with negative coordinates."""
        assert l2((-1, -1), (2, 3)) == 5.0


class TestPolygonOperations:
    """Test polygon operation functions."""

    def test_polygon_center_square(self):
        """Test center of square polygon."""
        square = np.array([
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10]
        ], dtype=np.float32)

        center = polygon_center(square)
        assert abs(center[0] - 5.0) < 0.1
        assert abs(center[1] - 5.0) < 0.1

    def test_polygon_center_triangle(self):
        """Test center of triangle polygon."""
        triangle = np.array([
            [0, 0],
            [6, 0],
            [3, 6]
        ], dtype=np.float32)

        center = polygon_center(triangle)
        # Triangle centroid
        assert abs(center[0] - 3.0) < 0.1
        assert abs(center[1] - 2.0) < 0.1

    def test_polygon_center_single_point(self):
        """Test center with single point."""
        # polygon_center requires at least 3 points
        with pytest.raises(ValueError):
            point = np.array([[5, 5]], dtype=np.float32)
            polygon_center(point)


class TestLineOperations:
    """Test line operation functions."""

    def test_distance_point_to_line(self):
        """Test distance from point to line."""
        # Point on horizontal line
        dist = point_distance_to_line((5, 5), (0, 5), (10, 5))
        assert abs(dist) < 0.1

        # Point above horizontal line
        dist = point_distance_to_line((5, 8), (0, 5), (10, 5))
        assert abs(dist - 3.0) < 0.1

        # Point on vertical line
        dist = point_distance_to_line((5, 5), (5, 0), (5, 10))
        assert abs(dist) < 0.1

    def test_rotate_point(self):
        """Test point rotation."""
        # Rotate 90 degrees around origin
        rotated = rotate_point((1, 0), (0, 0), 90)
        assert abs(rotated[0]) < 0.1
        assert abs(rotated[1] - 1.0) < 0.1

        # Rotate 180 degrees
        rotated = rotate_point((1, 0), (0, 0), 180)
        assert abs(rotated[0] - (-1.0)) < 0.1
        assert abs(rotated[1]) < 0.1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_angle_with_identical_points(self):
        """Test angle calculation with identical points."""
        # Should handle gracefully
        result = angle_deg((5, 5), (5, 5))
        assert isinstance(result, (int, float))

    def test_empty_polygon(self):
        """Test polygon center with empty array."""
        empty = np.array([], dtype=np.float32).reshape(0, 2)

        with pytest.raises((ValueError, IndexError)):
            polygon_center(empty)

    def test_distance_with_floats(self):
        """Test distance with floating point coordinates."""
        dist = l2((0.5, 0.5), (3.7, 4.2))
        assert isinstance(dist, float)
        assert dist > 0
