"""Tests for time utility functions."""

import pytest
from datetime import datetime, time, timedelta
from app.utils.time_utils import (
    intervals_overlap,
    time_fits_within_shift,
    generate_time_slots,
    minutes_between,
    format_duration,
)


def test_intervals_overlap():
    """Test interval overlap detection."""
    base = datetime(2026, 10, 31, 10, 0)
    
    # Overlapping intervals
    assert intervals_overlap(
        base, base + timedelta(hours=2),
        base + timedelta(hours=1), base + timedelta(hours=3)
    )
    
    # Non-overlapping intervals
    assert not intervals_overlap(
        base, base + timedelta(hours=1),
        base + timedelta(hours=2), base + timedelta(hours=3)
    )
    
    # Adjacent intervals (no overlap)
    assert not intervals_overlap(
        base, base + timedelta(hours=1),
        base + timedelta(hours=1), base + timedelta(hours=2)
    )


def test_time_fits_within_shift():
    """Test if job fits within shift."""
    job_start = datetime(2026, 10, 31, 10, 0)
    
    # Fits within shift
    assert time_fits_within_shift(
        job_start=job_start,
        job_duration_minutes=120,
        shift_start=time(8, 0),
        shift_end=time(17, 0)
    )
    
    # Does not fit (ends after shift)
    assert not time_fits_within_shift(
        job_start=datetime(2026, 10, 31, 16, 0),
        job_duration_minutes=120,
        shift_start=time(8, 0),
        shift_end=time(17, 0)
    )
    
    # Does not fit (starts before shift)
    assert not time_fits_within_shift(
        job_start=datetime(2026, 10, 31, 7, 0),
        job_duration_minutes=60,
        shift_start=time(8, 0),
        shift_end=time(17, 0)
    )


def test_generate_time_slots():
    """Test time slot generation."""
    start = datetime(2026, 10, 31, 8, 0)
    end = datetime(2026, 10, 31, 10, 0)
    
    slots = generate_time_slots(start, end, slot_interval_minutes=30)
    
    assert len(slots) == 5  # 8:00, 8:30, 9:00, 9:30, 10:00
    assert slots[0] == start
    assert slots[-1] == end
    assert slots[1] == start + timedelta(minutes=30)


def test_minutes_between():
    """Test minutes calculation between datetimes."""
    start = datetime(2026, 10, 31, 10, 0)
    end = datetime(2026, 10, 31, 12, 30)
    
    minutes = minutes_between(start, end)
    assert minutes == 150  # 2.5 hours


def test_format_duration():
    """Test duration formatting."""
    assert format_duration(60) == "1h"
    assert format_duration(90) == "1h 30m"
    assert format_duration(30) == "30m"
    assert format_duration(150) == "2h 30m"
