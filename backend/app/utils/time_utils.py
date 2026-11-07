"""Time and interval utility functions."""

from datetime import datetime, time, timedelta
from typing import Optional


def time_to_datetime(t: time, base_date: Optional[datetime] = None) -> datetime:
    """
    Convert a time to a datetime using a base date.
    
    Args:
        t: Time to convert
        base_date: Base date to use (defaults to today)
    
    Returns:
        datetime combining base date and time
    """
    if base_date is None:
        base_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    return datetime.combine(base_date.date(), t)


def is_within_time_range(
    check_time: datetime,
    range_start: datetime,
    range_end: datetime
) -> bool:
    """
    Check if a time falls within a range.
    
    Args:
        check_time: Time to check
        range_start: Start of range (inclusive)
        range_end: End of range (inclusive)
    
    Returns:
        True if check_time is within range
    """
    return range_start <= check_time <= range_end


def intervals_overlap(
    start1: datetime,
    end1: datetime,
    start2: datetime,
    end2: datetime
) -> bool:
    """
    Check if two time intervals overlap.
    
    Args:
        start1: Start of first interval
        end1: End of first interval
        start2: Start of second interval
        end2: End of second interval
    
    Returns:
        True if intervals overlap
    """
    return start1 < end2 and start2 < end1


def time_fits_within_shift(
    job_start: datetime,
    job_duration_minutes: int,
    shift_start: time,
    shift_end: time
) -> bool:
    """
    Check if a job fits within a technician's shift.
    
    Args:
        job_start: Job start time
        job_duration_minutes: Job duration in minutes
        shift_start: Shift start time
        shift_end: Shift end time
    
    Returns:
        True if job fits within shift
    """
    job_end = job_start + timedelta(minutes=job_duration_minutes)
    
    # Convert shift times to datetime for comparison
    shift_start_dt = time_to_datetime(shift_start, job_start)
    shift_end_dt = time_to_datetime(shift_end, job_start)
    
    # Handle overnight shifts
    if shift_end < shift_start:
        shift_end_dt += timedelta(days=1)
    
    return shift_start_dt <= job_start and job_end <= shift_end_dt


def generate_time_slots(
    window_start: datetime,
    window_end: datetime,
    slot_interval_minutes: int = 15
) -> list[datetime]:
    """
    Generate time slots at regular intervals within a window.
    
    Args:
        window_start: Start of time window
        window_end: End of time window
        slot_interval_minutes: Interval between slots in minutes
    
    Returns:
        List of datetime slots
    """
    slots = []
    current = window_start
    
    while current <= window_end:
        slots.append(current)
        current += timedelta(minutes=slot_interval_minutes)
    
    return slots


def minutes_between(start: datetime, end: datetime) -> int:
    """
    Calculate minutes between two datetimes.
    
    Args:
        start: Start time
        end: End time
    
    Returns:
        Minutes between times (can be negative if end < start)
    """
    delta = end - start
    return int(delta.total_seconds() / 60)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Add minutes to a datetime.
    
    Args:
        dt: Base datetime
        minutes: Minutes to add (can be negative)
    
    Returns:
        New datetime
    """
    return dt + timedelta(minutes=minutes)


def format_duration(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        Formatted string like "2h 30m"
    """
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def round_to_interval(dt: datetime, interval_minutes: int = 15) -> datetime:
    """
    Round datetime to nearest interval.
    
    Args:
        dt: Datetime to round
        interval_minutes: Interval in minutes
    
    Returns:
        Rounded datetime
    """
    minutes = dt.minute
    rounded_minutes = (minutes // interval_minutes) * interval_minutes
    
    return dt.replace(minute=rounded_minutes, second=0, microsecond=0)
