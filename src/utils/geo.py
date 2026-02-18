"""
Geospatial utilities for distance and walking time calculations.

Provides functions for calculating distances between coordinates
and estimating walking times for transfers.
"""

import math
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Uses the Haversine formula to calculate distance in meters.

    Args:
        lat1: Latitude of first point (degrees)
        lon1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lon2: Longitude of second point (degrees)

    Returns:
        Distance in meters

    Example:
        >>> haversine_distance(-37.8136, 144.9631, -37.8183, 144.9671)
        585.2  # ~585 meters between Melbourne Central and Flinders Street
    """
    # Earth's radius in meters
    R = 6371000

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance


def calculate_walking_time(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Calculate estimated walking time between two coordinates.

    Assumes average walking speed of 4.5 km/h (75 m/min) plus a 2-minute
    buffer for navigating stations, stairs, etc.

    Args:
        lat1: Latitude of origin (degrees)
        lon1: Longitude of origin (degrees)
        lat2: Latitude of destination (degrees)
        lon2: Longitude of destination (degrees)

    Returns:
        Walking time in minutes (clamped to 3-15 minute range)

    Example:
        >>> calculate_walking_time(-37.8136, 144.9631, -37.8183, 144.9671)
        10  # ~10 minutes walking time
    """
    # Calculate distance in meters
    distance_m = haversine_distance(lat1, lon1, lat2, lon2)

    # Walking speed: 4.5 km/h = 75 m/min
    # Add 2-minute buffer for station navigation
    walking_minutes = (distance_m / 75) + 2

    # Clamp to reasonable range: 3-15 minutes
    # Minimum 3 min (even for same platform)
    # Maximum 15 min (longer walks are impractical for transfers)
    return int(max(3, min(walking_minutes, 15)))


def are_stops_nearby(lat1: float, lon1: float, lat2: float, lon2: float,
                     threshold_meters: float = 100) -> bool:
    """
    Check if two stops are within threshold distance (same physical location).

    Useful for identifying transfer hubs where different modes serve
    the same station (e.g., metro and tram at the same stop).

    Args:
        lat1: Latitude of first stop
        lon1: Longitude of first stop
        lat2: Latitude of second stop
        lon2: Longitude of second stop
        threshold_meters: Maximum distance to consider "same location" (default: 100m)

    Returns:
        True if stops are within threshold distance

    Example:
        >>> # Southern Cross platform 1 and platform 5
        >>> are_stops_nearby(-37.8183, 144.9527, -37.8185, 144.9529)
        True
    """
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return distance <= threshold_meters


def calculate_transfer_time_seconds(lat1: float, lon1: float,
                                   lat2: float, lon2: float) -> int:
    """
    Calculate transfer time in seconds (for GTFS Connection objects).

    Args:
        lat1: Latitude of origin stop
        lon1: Longitude of origin stop
        lat2: Latitude of destination stop
        lon2: Longitude of destination stop

    Returns:
        Transfer time in seconds
    """
    minutes = calculate_walking_time(lat1, lon1, lat2, lon2)
    return minutes * 60
