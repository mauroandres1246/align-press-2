"""
Unit tests for geometry utility functions.
"""

import math
import pytest
import numpy as np

from alignpress.utils.geometry import (
    angle_deg, l2, polygon_center, angle_diff_circular, clamp,
    point_distance_to_line, rotate_point, is_point_in_polygon
)


class TestAngleDeg:
    """Test angle calculation function."""

    def test_angle_deg_quadrants(self):
        """Test angle calculation in all quadrants."""
        # First quadrant (positive x, positive y)
        assert abs(angle_deg((0, 0), (1, 1)) - 45.0) < 1e-6

        # Second quadrant (negative x, positive y)
        assert abs(angle_deg((0, 0), (-1, 1)) - 135.0) < 1e-6

        # Third quadrant (negative x, negative y)
        assert abs(angle_deg((0, 0), (-1, -1)) - (-135.0)) < 1e-6

        # Fourth quadrant (positive x, negative y)
        assert abs(angle_deg((0, 0), (1, -1)) - (-45.0)) < 1e-6

    def test_angle_deg_cardinal_directions(self):
        """Test angle calculation for cardinal directions."""
        # East (0 degrees)
        assert abs(angle_deg((0, 0), (1, 0)) - 0.0) < 1e-6

        # North (90 degrees)
        assert abs(angle_deg((0, 0), (0, 1)) - 90.0) < 1e-6

        # West (180 degrees)
        assert abs(angle_deg((0, 0), (-1, 0)) - 180.0) < 1e-6

        # South (-90 degrees)
        assert abs(angle_deg((0, 0), (0, -1)) - (-90.0)) < 1e-6

    def test_angle_deg_same_point(self):
        """Test angle calculation for same point."""
        assert angle_deg((5, 5), (5, 5)) == 0.0


class TestL2Distance:
    """Test Euclidean distance function."""

    def test_l2_basic_cases(self):
        """Test basic distance calculations."""
        # Unit distance
        assert abs(l2((0, 0), (1, 0)) - 1.0) < 1e-6
        assert abs(l2((0, 0), (0, 1)) - 1.0) < 1e-6

        # Pythagorean triple
        assert abs(l2((0, 0), (3, 4)) - 5.0) < 1e-6

        # Diagonal
        assert abs(l2((0, 0), (1, 1)) - math.sqrt(2)) < 1e-6

    def test_l2_same_point(self):
        """Test distance between same point."""
        assert l2((5, 5), (5, 5)) == 0.0

    def test_l2_negative_coordinates(self):
        """Test distance with negative coordinates."""
        assert abs(l2((-1, -1), (1, 1)) - 2 * math.sqrt(2)) < 1e-6


class TestPolygonCenter:
    """Test polygon center calculation."""

    def test_polygon_center_square(self):
        """Test center of a square."""
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        center = polygon_center(square)
        assert abs(center[0] - 1.0) < 1e-6
        assert abs(center[1] - 1.0) < 1e-6

    def test_polygon_center_triangle(self):
        """Test center of a triangle."""
        triangle = [(0, 0), (3, 0), (1.5, 3)]
        center = polygon_center(triangle)
        assert abs(center[0] - 1.5) < 1e-6
        assert abs(center[1] - 1.0) < 1e-6

    def test_polygon_center_numpy_array(self):
        """Test center calculation with numpy array input."""
        points = np.array([[0, 0], [2, 0], [2, 2], [0, 2]], dtype=np.float32)
        center = polygon_center(points)
        assert abs(center[0] - 1.0) < 1e-6
        assert abs(center[1] - 1.0) < 1e-6

    def test_polygon_center_opencv_format(self):
        """Test center calculation with OpenCV contour format."""
        # OpenCV contours have shape (n, 1, 2)
        contour = np.array([[[0, 0]], [[2, 0]], [[2, 2]], [[0, 2]]], dtype=np.float32)
        center = polygon_center(contour)
        assert abs(center[0] - 1.0) < 1e-6
        assert abs(center[1] - 1.0) < 1e-6

    def test_polygon_center_invalid_input(self):
        """Test error handling for invalid input."""
        with pytest.raises(ValueError):
            polygon_center([(0, 0), (1, 1)])  # Less than 3 points


class TestAngleDiffCircular:
    """Test circular angle difference calculation."""

    def test_angle_diff_circular_basic(self):
        """Test basic angle differences."""
        # Simple case
        assert abs(angle_diff_circular(10, 20) - 10) < 1e-6
        assert abs(angle_diff_circular(20, 10) - (-10)) < 1e-6

    def test_angle_diff_circular_wraparound(self):
        """Test wraparound cases."""
        # Cross 0 degrees
        assert abs(angle_diff_circular(350, 10) - 20) < 1e-6
        assert abs(angle_diff_circular(10, 350) - (-20)) < 1e-6

        # Cross 180 degrees
        assert abs(angle_diff_circular(170, -170) - 20) < 1e-6
        assert abs(angle_diff_circular(-170, 170) - (-20)) < 1e-6

    def test_angle_diff_circular_same_angle(self):
        """Test difference between same angles."""
        assert abs(angle_diff_circular(45, 45)) < 1e-6
        assert abs(angle_diff_circular(-90, -90)) < 1e-6


class TestClamp:
    """Test value clamping function."""

    def test_clamp_within_range(self):
        """Test clamping values within range."""
        assert clamp(5, 0, 10) == 5
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10

    def test_clamp_outside_range(self):
        """Test clamping values outside range."""
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10

    def test_clamp_invalid_range(self):
        """Test error handling for invalid range."""
        with pytest.raises(ValueError):
            clamp(5, 10, 0)  # lo > hi


class TestPointDistanceToLine:
    """Test point to line distance calculation."""

    def test_point_distance_to_line_basic(self):
        """Test basic distance calculations."""
        # Point on horizontal line
        assert abs(point_distance_to_line((1, 1), (0, 0), (2, 0)) - 1.0) < 1e-6

        # Point on vertical line
        assert abs(point_distance_to_line((1, 1), (0, 0), (0, 2)) - 1.0) < 1e-6

    def test_point_distance_to_line_on_line(self):
        """Test distance when point is on the line."""
        assert abs(point_distance_to_line((1, 0), (0, 0), (2, 0))) < 1e-6

    def test_point_distance_to_line_zero_length(self):
        """Test distance to zero-length line (point)."""
        distance = point_distance_to_line((3, 4), (0, 0), (0, 0))
        assert abs(distance - 5.0) < 1e-6  # Should return distance to point


class TestRotatePoint:
    """Test point rotation function."""

    def test_rotate_point_90_degrees(self):
        """Test 90-degree rotation."""
        rotated = rotate_point((1, 0), (0, 0), 90)
        assert abs(rotated[0] - 0.0) < 1e-6
        assert abs(rotated[1] - 1.0) < 1e-6

    def test_rotate_point_180_degrees(self):
        """Test 180-degree rotation."""
        rotated = rotate_point((1, 0), (0, 0), 180)
        assert abs(rotated[0] - (-1.0)) < 1e-6
        assert abs(rotated[1] - 0.0) < 1e-6

    def test_rotate_point_no_rotation(self):
        """Test zero-degree rotation."""
        original = (3, 4)
        rotated = rotate_point(original, (0, 0), 0)
        assert abs(rotated[0] - original[0]) < 1e-6
        assert abs(rotated[1] - original[1]) < 1e-6

    def test_rotate_point_different_center(self):
        """Test rotation around different center."""
        # Rotate (2, 1) around (1, 1) by 90 degrees
        rotated = rotate_point((2, 1), (1, 1), 90)
        assert abs(rotated[0] - 1.0) < 1e-6
        assert abs(rotated[1] - 2.0) < 1e-6


class TestIsPointInPolygon:
    """Test point-in-polygon test."""

    def test_point_in_square(self):
        """Test point inside a square."""
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        assert is_point_in_polygon((1, 1), square) is True

    def test_point_outside_square(self):
        """Test point outside a square."""
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        assert is_point_in_polygon((3, 1), square) is False
        assert is_point_in_polygon((1, 3), square) is False

    def test_point_on_edge(self):
        """Test point on polygon edge."""
        square = [(0, 0), (2, 0), (2, 2), (0, 2)]
        # Point on edge behavior may vary - test specific implementation
        result = is_point_in_polygon((1, 0), square)
        assert isinstance(result, bool)  # Should return a boolean

    def test_point_in_triangle(self):
        """Test point inside a triangle."""
        triangle = [(0, 0), (3, 0), (1.5, 3)]
        assert is_point_in_polygon((1.5, 1), triangle) is True
        assert is_point_in_polygon((4, 1), triangle) is False