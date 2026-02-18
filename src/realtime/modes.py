"""
Transport mode constants and utilities for PTV GTFS Realtime.

Centralizes all transport mode definitions to avoid hardcoded values
scattered throughout the codebase.
"""

from enum import Enum
from typing import Set


class TransportMode(str, Enum):
    """PTV transport modes for GTFS Realtime feeds."""
    METRO = "metro"
    VLINE = "vline"
    TRAM = "tram"
    BUS = "bus"


# All supported transport modes
ALL_MODES: Set[str] = {m.value for m in TransportMode}

# Modes that have service alerts available from PTV API
# Note: V/Line and Bus do NOT have service alert feeds
MODES_WITH_ALERTS: Set[str] = {
    TransportMode.METRO.value,
    TransportMode.TRAM.value
}

# Modes WITHOUT service alerts (return empty list gracefully)
MODES_WITHOUT_ALERTS: Set[str] = {
    TransportMode.VLINE.value,
    TransportMode.BUS.value
}

# Regex pattern for FastAPI Query parameter validation
MODE_PATTERN = "^(metro|vline|tram|bus)$"

# Default modes for different use cases
DEFAULT_VEHICLE_MODE = TransportMode.VLINE.value
DEFAULT_ALERT_MODE = TransportMode.METRO.value


def is_valid_mode(mode: str) -> bool:
    """
    Check if a mode string is a valid transport mode.

    Args:
        mode: Transport mode string to validate

    Returns:
        True if mode is valid, False otherwise
    """
    return mode in ALL_MODES


def has_service_alerts(mode: str) -> bool:
    """
    Check if a transport mode has service alerts available.

    Args:
        mode: Transport mode string

    Returns:
        True if mode has service alerts, False otherwise

    Note:
        Only 'metro' and 'tram' have service alert feeds from PTV.
        V/Line and bus do not provide service alerts.
    """
    return mode in MODES_WITH_ALERTS


def get_mode_description(include_alerts: bool = False) -> str:
    """
    Get a description string of available transport modes.

    Args:
        include_alerts: If True, note which modes have alerts

    Returns:
        Human-readable description of available modes
    """
    modes = ", ".join(f"'{m.value}'" for m in TransportMode)
    if include_alerts:
        alert_modes = ", ".join(f"'{m}'" for m in sorted(MODES_WITH_ALERTS))
        return f"Transport mode: {modes}. Service alerts available for: {alert_modes}"
    return f"Transport mode: {modes}"
