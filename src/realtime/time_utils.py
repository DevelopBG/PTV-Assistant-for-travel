"""
Time utility functions for realtime integration.

Handles conversions between Unix timestamps, HH:MM:SS format, and seconds since midnight.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def unix_to_hhmmss(unix_timestamp: int, timezone_offset: int = 11) -> str:
    """
    Convert Unix timestamp to HH:MM:SS format.

    Args:
        unix_timestamp: Unix timestamp (seconds since epoch)
        timezone_offset: Hours offset from UTC (default: 11 for Melbourne)

    Returns:
        Time string in HH:MM:SS format

    Example:
        >>> unix_to_hhmmss(1705201234)
        "14:27:14"
    """
    # Convert to datetime (using timezone-aware UTC)
    dt = datetime.fromtimestamp(unix_timestamp, timezone.utc)

    # Apply timezone offset (Melbourne is UTC+10 or UTC+11 depending on DST)
    dt = dt + timedelta(hours=timezone_offset)

    # Format as HH:MM:SS
    return dt.strftime("%H:%M:%S")


def hhmmss_to_seconds(time_str: str) -> int:
    """
    Convert HH:MM:SS to seconds since midnight.

    Args:
        time_str: Time in HH:MM:SS format

    Returns:
        Seconds since midnight

    Example:
        >>> hhmmss_to_seconds("14:30:00")
        52200
    """
    parts = time_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM:SS")

    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])

    return hours * 3600 + minutes * 60 + seconds


def seconds_to_hhmmss(seconds: int) -> str:
    """
    Convert seconds since midnight to HH:MM:SS format.

    Args:
        seconds: Seconds since midnight

    Returns:
        Time string in HH:MM:SS format

    Example:
        >>> seconds_to_hhmmss(52200)
        "14:30:00"
    """
    # Handle times past midnight (next day)
    seconds = seconds % (24 * 3600)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def add_delay_to_time(time_str: str, delay_seconds: int) -> str:
    """
    Add delay to HH:MM:SS time, return new HH:MM:SS.

    Args:
        time_str: Original time in HH:MM:SS format
        delay_seconds: Delay to add (can be negative for early arrival)

    Returns:
        New time in HH:MM:SS format

    Example:
        >>> add_delay_to_time("14:30:00", 300)  # Add 5 minutes
        "14:35:00"
        >>> add_delay_to_time("14:30:00", -120)  # Subtract 2 minutes
        "14:28:00"
    """
    # Convert to seconds
    original_seconds = hhmmss_to_seconds(time_str)

    # Add delay
    new_seconds = original_seconds + delay_seconds

    # Handle negative times (wrap to previous day)
    if new_seconds < 0:
        new_seconds = (24 * 3600) + new_seconds

    # Convert back to HH:MM:SS
    return seconds_to_hhmmss(new_seconds)


def format_delay(delay_seconds: int) -> str:
    """
    Format delay as human-readable string.

    Args:
        delay_seconds: Delay in seconds (positive = late, negative = early)

    Returns:
        Formatted string like "5 min delay" or "2 min early" or "On time"

    Example:
        >>> format_delay(300)
        "5 min delay"
        >>> format_delay(-120)
        "2 min early"
        >>> format_delay(0)
        "On time"
    """
    if delay_seconds == 0:
        return "On time"

    delay_mins = abs(delay_seconds) // 60
    if delay_mins == 0:
        # Less than a minute
        return "On time"

    if delay_seconds > 0:
        return f"{delay_mins} min delay"
    else:
        return f"{delay_mins} min early"


def time_diff_seconds(time1: str, time2: str) -> int:
    """
    Calculate difference between two HH:MM:SS times in seconds.

    Args:
        time1: First time in HH:MM:SS format
        time2: Second time in HH:MM:SS format

    Returns:
        time2 - time1 in seconds

    Example:
        >>> time_diff_seconds("14:30:00", "14:35:00")
        300
    """
    seconds1 = hhmmss_to_seconds(time1)
    seconds2 = hhmmss_to_seconds(time2)
    return seconds2 - seconds1
