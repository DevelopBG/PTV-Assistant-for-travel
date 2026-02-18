"""
Tests for the transport mode constants module.

Tests the centralized mode definitions, validation, and helper functions.
"""

import pytest
from src.realtime.modes import (
    TransportMode,
    ALL_MODES,
    MODES_WITH_ALERTS,
    MODES_WITHOUT_ALERTS,
    MODE_PATTERN,
    DEFAULT_VEHICLE_MODE,
    DEFAULT_ALERT_MODE,
    is_valid_mode,
    has_service_alerts,
    get_mode_description,
)


class TestTransportModeEnum:
    """Test the TransportMode enum."""

    def test_all_modes_defined(self):
        """Test that all four transport modes are defined."""
        assert TransportMode.METRO.value == "metro"
        assert TransportMode.VLINE.value == "vline"
        assert TransportMode.TRAM.value == "tram"
        assert TransportMode.BUS.value == "bus"

    def test_mode_count(self):
        """Test that exactly 4 modes are defined."""
        assert len(TransportMode) == 4

    def test_enum_is_string(self):
        """Test that enum values are strings."""
        for mode in TransportMode:
            assert isinstance(mode.value, str)


class TestModeConstants:
    """Test the mode constant sets."""

    def test_all_modes_set(self):
        """Test ALL_MODES contains all four modes."""
        assert ALL_MODES == {"metro", "vline", "tram", "bus"}

    def test_modes_with_alerts(self):
        """Test MODES_WITH_ALERTS contains only metro and tram."""
        assert MODES_WITH_ALERTS == {"metro", "tram"}

    def test_modes_without_alerts(self):
        """Test MODES_WITHOUT_ALERTS contains vline and bus."""
        assert MODES_WITHOUT_ALERTS == {"vline", "bus"}

    def test_alert_sets_are_disjoint(self):
        """Test that with/without alert sets don't overlap."""
        assert MODES_WITH_ALERTS.isdisjoint(MODES_WITHOUT_ALERTS)

    def test_alert_sets_cover_all_modes(self):
        """Test that alert sets together cover all modes."""
        assert MODES_WITH_ALERTS | MODES_WITHOUT_ALERTS == ALL_MODES

    def test_mode_pattern_regex(self):
        """Test MODE_PATTERN is a valid regex pattern."""
        import re
        pattern = re.compile(MODE_PATTERN)

        # Valid modes should match
        assert pattern.match("metro")
        assert pattern.match("vline")
        assert pattern.match("tram")
        assert pattern.match("bus")

        # Invalid modes should not match
        assert not pattern.match("ferry")
        assert not pattern.match("train")
        assert not pattern.match("")
        assert not pattern.match("Metro")  # Case sensitive


class TestDefaultModes:
    """Test default mode constants."""

    def test_default_vehicle_mode(self):
        """Test default vehicle mode is vline."""
        assert DEFAULT_VEHICLE_MODE == "vline"

    def test_default_alert_mode(self):
        """Test default alert mode is metro."""
        assert DEFAULT_ALERT_MODE == "metro"

    def test_defaults_are_valid_modes(self):
        """Test default modes are valid."""
        assert DEFAULT_VEHICLE_MODE in ALL_MODES
        assert DEFAULT_ALERT_MODE in ALL_MODES


class TestIsValidMode:
    """Test the is_valid_mode function."""

    def test_valid_modes(self):
        """Test that all valid modes return True."""
        assert is_valid_mode("metro") is True
        assert is_valid_mode("vline") is True
        assert is_valid_mode("tram") is True
        assert is_valid_mode("bus") is True

    def test_invalid_modes(self):
        """Test that invalid modes return False."""
        assert is_valid_mode("ferry") is False
        assert is_valid_mode("train") is False
        assert is_valid_mode("subway") is False
        assert is_valid_mode("") is False

    def test_case_sensitive(self):
        """Test that mode validation is case sensitive."""
        assert is_valid_mode("METRO") is False
        assert is_valid_mode("Metro") is False
        assert is_valid_mode("VLINE") is False


class TestHasServiceAlerts:
    """Test the has_service_alerts function."""

    def test_modes_with_alerts(self):
        """Test modes that have service alerts."""
        assert has_service_alerts("metro") is True
        assert has_service_alerts("tram") is True

    def test_modes_without_alerts(self):
        """Test modes that don't have service alerts."""
        assert has_service_alerts("vline") is False
        assert has_service_alerts("bus") is False

    def test_invalid_mode(self):
        """Test invalid mode returns False."""
        assert has_service_alerts("ferry") is False


class TestGetModeDescription:
    """Test the get_mode_description function."""

    def test_basic_description(self):
        """Test basic mode description without alert info."""
        desc = get_mode_description()
        assert "metro" in desc
        assert "vline" in desc
        assert "tram" in desc
        assert "bus" in desc
        assert "Transport mode" in desc

    def test_description_with_alerts(self):
        """Test description with alert availability info."""
        desc = get_mode_description(include_alerts=True)
        assert "metro" in desc
        assert "tram" in desc
        assert "alerts" in desc.lower()
