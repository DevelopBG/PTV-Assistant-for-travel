"""
Tests for realtime time utility functions.
"""

import pytest
from src.realtime.time_utils import (
    unix_to_hhmmss,
    hhmmss_to_seconds,
    seconds_to_hhmmss,
    add_delay_to_time,
    format_delay,
    time_diff_seconds
)


class TestHHMMSSToSeconds:
    """Test HH:MM:SS to seconds conversion."""

    def test_midnight(self):
        """Test midnight conversion."""
        assert hhmmss_to_seconds("00:00:00") == 0

    def test_noon(self):
        """Test noon conversion."""
        assert hhmmss_to_seconds("12:00:00") == 12 * 3600

    def test_afternoon(self):
        """Test afternoon time."""
        assert hhmmss_to_seconds("14:30:45") == 14 * 3600 + 30 * 60 + 45

    def test_end_of_day(self):
        """Test end of day (23:59:59)."""
        assert hhmmss_to_seconds("23:59:59") == 23 * 3600 + 59 * 60 + 59

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            hhmmss_to_seconds("14:30")  # Missing seconds

        with pytest.raises(ValueError):
            hhmmss_to_seconds("invalid")


class TestSecondsToHHMMSS:
    """Test seconds to HH:MM:SS conversion."""

    def test_midnight(self):
        """Test midnight conversion."""
        assert seconds_to_hhmmss(0) == "00:00:00"

    def test_noon(self):
        """Test noon conversion."""
        assert seconds_to_hhmmss(12 * 3600) == "12:00:00"

    def test_afternoon(self):
        """Test afternoon time."""
        assert seconds_to_hhmmss(14 * 3600 + 30 * 60 + 45) == "14:30:45"

    def test_wraps_past_midnight(self):
        """Test times past midnight wrap around."""
        # 25 hours = 1:00 AM next day
        assert seconds_to_hhmmss(25 * 3600) == "01:00:00"


class TestRoundTripConversion:
    """Test that conversions are reversible."""

    def test_hhmmss_to_seconds_and_back(self):
        """Test HH:MM:SS → seconds → HH:MM:SS."""
        original = "14:30:45"
        seconds = hhmmss_to_seconds(original)
        result = seconds_to_hhmmss(seconds)
        assert result == original

    def test_seconds_to_hhmmss_and_back(self):
        """Test seconds → HH:MM:SS → seconds."""
        original = 52245  # 14:30:45
        time_str = seconds_to_hhmmss(original)
        result = hhmmss_to_seconds(time_str)
        assert result == original


class TestAddDelayToTime:
    """Test adding delays to times."""

    def test_add_positive_delay(self):
        """Test adding delay (late arrival)."""
        # 14:30:00 + 5 min = 14:35:00
        result = add_delay_to_time("14:30:00", 300)
        assert result == "14:35:00"

    def test_add_negative_delay(self):
        """Test subtracting delay (early arrival)."""
        # 14:30:00 - 2 min = 14:28:00
        result = add_delay_to_time("14:30:00", -120)
        assert result == "14:28:00"

    def test_zero_delay(self):
        """Test zero delay returns same time."""
        result = add_delay_to_time("14:30:00", 0)
        assert result == "14:30:00"

    def test_large_delay(self):
        """Test large delay (over 1 hour)."""
        # 14:30:00 + 90 min = 16:00:00
        result = add_delay_to_time("14:30:00", 90 * 60)
        assert result == "16:00:00"

    def test_delay_crosses_midnight(self):
        """Test delay that crosses midnight."""
        # 23:50:00 + 20 min = 00:10:00
        result = add_delay_to_time("23:50:00", 20 * 60)
        assert result == "00:10:00"

    def test_early_before_midnight(self):
        """Test early arrival before midnight."""
        # 00:10:00 - 20 min = 23:50:00 (previous day)
        result = add_delay_to_time("00:10:00", -20 * 60)
        assert result == "23:50:00"


class TestFormatDelay:
    """Test delay formatting."""

    def test_no_delay(self):
        """Test zero delay."""
        assert format_delay(0) == "On time"

    def test_small_delay_rounds_down(self):
        """Test delay less than 1 minute."""
        assert format_delay(30) == "On time"  # 30 seconds
        assert format_delay(-45) == "On time"  # 45 seconds early

    def test_positive_delay(self):
        """Test late arrival."""
        assert format_delay(300) == "5 min delay"  # 5 minutes
        assert format_delay(600) == "10 min delay"  # 10 minutes

    def test_negative_delay(self):
        """Test early arrival."""
        assert format_delay(-120) == "2 min early"  # 2 minutes
        assert format_delay(-600) == "10 min early"  # 10 minutes

    def test_large_delay(self):
        """Test large delay (over 1 hour)."""
        assert format_delay(3600) == "60 min delay"
        assert format_delay(5400) == "90 min delay"


class TestTimeDiffSeconds:
    """Test time difference calculation."""

    def test_simple_difference(self):
        """Test basic time difference."""
        # 14:35:00 - 14:30:00 = 5 minutes
        assert time_diff_seconds("14:30:00", "14:35:00") == 300

    def test_negative_difference(self):
        """Test later time before earlier time."""
        # 14:30:00 - 14:35:00 = -5 minutes
        assert time_diff_seconds("14:35:00", "14:30:00") == -300

    def test_same_time(self):
        """Test same time."""
        assert time_diff_seconds("14:30:00", "14:30:00") == 0

    def test_hour_difference(self):
        """Test 1 hour difference."""
        assert time_diff_seconds("14:00:00", "15:00:00") == 3600

    def test_transfer_wait_time(self):
        """Test calculating transfer wait time."""
        # Arrive at 14:51:00, depart at 14:54:00 = 3 min wait
        assert time_diff_seconds("14:51:00", "14:54:00") == 180


class TestUnixToHHMMSS:
    """Test Unix timestamp conversion."""

    def test_basic_conversion(self):
        """Test basic timestamp conversion."""
        # This is a rough test since timezone handling is complex
        # Just verify it returns valid HH:MM:SS format
        result = unix_to_hhmmss(1705201234)
        assert len(result) == 8
        assert result.count(':') == 2

    def test_returns_valid_time_format(self):
        """Test result is valid HH:MM:SS."""
        result = unix_to_hhmmss(1705201234)
        # Should not raise error
        hhmmss_to_seconds(result)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_very_large_delay(self):
        """Test delay larger than 24 hours."""
        # 14:00:00 + 25 hours = 15:00:00 next day
        result = add_delay_to_time("14:00:00", 25 * 3600)
        assert result == "15:00:00"

    def test_very_negative_delay(self):
        """Test early arrival more than 24 hours."""
        # 14:00:00 - 25 hours = 13:00:00 previous day
        result = add_delay_to_time("14:00:00", -25 * 3600)
        assert result == "13:00:00"

    def test_midnight_rollover(self):
        """Test midnight boundary."""
        result = add_delay_to_time("23:59:59", 1)
        assert result == "00:00:00"

    def test_negative_midnight_rollover(self):
        """Test midnight boundary going backwards."""
        result = add_delay_to_time("00:00:00", -1)
        assert result == "23:59:59"
