"""
Geometric utility functions for logo detection and positioning.

This module provides common geometric operations used throughout the alignment system,
including angle calculations, distance measurements, and polygon operations.
"""

import math
from typing import List, Tuple, Union
import numpy as np


def angle_deg(p0: Tuple[float, float], p1: Tuple[float, float]) -> float:
    """
    Calculate angle in degrees between two points.

    Args:
        p0: First point (x, y)
        p1: Second point (x, y)

    Returns:
        Angle in degrees from p0 to p1, range [-180, 180]
    """
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    return math.degrees(math.atan2(dy, dx))


def l2(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """
    Calculate Euclidean distance between two points.

    Args:
        a: First point (x, y)
        b: Second point (x, y)

    Returns:
        Euclidean distance between points
    """
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


def polygon_center(poly: Union[List[Tuple[float, float]], np.ndarray]) -> Tuple[float, float]:
    """
    Calculate the center (centroid) of a polygon.

    Args:
        poly: List of polygon vertices as (x, y) tuples or numpy array

    Returns:
        Center point (x, y) of the polygon

    Raises:
        ValueError: If polygon has less than 3 points
    """
    if isinstance(poly, np.ndarray):
        if len(poly.shape) == 3:  # Handle OpenCV contour format
            poly = poly.reshape(-1, 2)
        points = [(float(p[0]), float(p[1])) for p in poly]
    else:
        points = list(poly)

    if len(points) < 3:
        raise ValueError("Polygon must have at least 3 points")

    x_sum = sum(p[0] for p in points)
    y_sum = sum(p[1] for p in points)
    n = len(points)

    return (x_sum / n, y_sum / n)


def angle_diff_circular(a: float, b: float) -> float:
    """
    Calculate the minimum angular difference between two angles.

    Handles circular nature of angles (e.g., 350° - 10° = 20°, not 340°).

    Args:
        a: First angle in degrees
        b: Second angle in degrees

    Returns:
        Minimum angular difference in degrees, range [-180, 180]
    """
    diff = b - a
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return diff


def clamp(val: float, lo: float, hi: float) -> float:
    """
    Clamp a value to a specified range.

    Args:
        val: Value to clamp
        lo: Minimum value
        hi: Maximum value

    Returns:
        Clamped value within [lo, hi] range

    Raises:
        ValueError: If lo > hi
    """
    if lo > hi:
        raise ValueError(f"Invalid range: lo ({lo}) > hi ({hi})")

    return max(lo, min(val, hi))


def point_distance_to_line(
    point: Tuple[float, float],
    line_start: Tuple[float, float],
    line_end: Tuple[float, float]
) -> float:
    """
    Calculate perpendicular distance from a point to a line segment.

    Args:
        point: Point (x, y)
        line_start: Start of line segment (x, y)
        line_end: End of line segment (x, y)

    Returns:
        Perpendicular distance from point to line
    """
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end

    # Calculate line length
    line_length = l2(line_start, line_end)
    if line_length == 0:
        return l2(point, line_start)

    # Calculate perpendicular distance using cross product
    numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    return numerator / line_length


def rotate_point(
    point: Tuple[float, float],
    center: Tuple[float, float],
    angle_deg: float
) -> Tuple[float, float]:
    """
    Rotate a point around a center by a given angle.

    Args:
        point: Point to rotate (x, y)
        center: Center of rotation (x, y)
        angle_deg: Rotation angle in degrees (positive = counterclockwise)

    Returns:
        Rotated point (x, y)
    """
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Translate to origin
    dx = point[0] - center[0]
    dy = point[1] - center[1]

    # Rotate
    rotated_x = dx * cos_a - dy * sin_a
    rotated_y = dx * sin_a + dy * cos_a

    # Translate back
    return (rotated_x + center[0], rotated_y + center[1])


def is_point_in_polygon(
    point: Tuple[float, float],
    polygon: List[Tuple[float, float]]
) -> bool:
    """
    Check if a point is inside a polygon using ray casting algorithm.

    Args:
        point: Point to test (x, y)
        polygon: List of polygon vertices as (x, y) tuples

    Returns:
        True if point is inside polygon, False otherwise
    """
    x, y = point
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside