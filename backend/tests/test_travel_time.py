"""Tests for travel time utilities."""

import pytest
from app.utils.travel import estimate_travel_time, calculate_total_travel_time, is_travel_feasible
from app.seed.travel_matrix import get_travel_time


def test_get_travel_time_same_zone():
    """Test travel time within same zone."""
    time = get_travel_time("North", "North")
    assert time == 10, "Same zone should be 10 minutes"


def test_get_travel_time_different_zones():
    """Test travel time between different zones."""
    time = get_travel_time("North", "South")
    assert time > 10, "Cross-city travel should take longer"


def test_get_travel_time_symmetric():
    """Test that travel time is symmetric."""
    time1 = get_travel_time("North", "East")
    time2 = get_travel_time("East", "North")
    assert time1 == time2, "Travel time should be symmetric"


def test_estimate_travel_time_with_zones():
    """Test travel time estimation with zone names."""
    time = estimate_travel_time(
        "123 Main St",
        "456 Oak Ave",
        from_zone="North",
        to_zone="South"
    )
    assert time > 0, "Should return positive travel time"


def test_estimate_travel_time_from_location_string():
    """Test travel time extraction from location strings."""
    time = estimate_travel_time(
        "123 Main St, North",
        "456 Oak Ave, South"
    )
    assert time > 0, "Should extract zones from location strings"


def test_calculate_total_travel_time():
    """Test total travel time calculation."""
    locations = [
        ("Location A, North", "North"),
        ("Location B, East", "East"),
        ("Location C, South", "South"),
    ]
    
    total = calculate_total_travel_time(locations)
    assert total > 0, "Total travel time should be positive"
    
    # Should be sum of two legs
    leg1 = get_travel_time("North", "East")
    leg2 = get_travel_time("East", "South")
    assert total == leg1 + leg2


def test_calculate_total_travel_time_single_location():
    """Test total travel time with single location."""
    locations = [("Location A, North", "North")]
    total = calculate_total_travel_time(locations)
    assert total == 0, "Single location should have zero travel"


def test_is_travel_feasible():
    """Test travel feasibility check."""
    # Feasible: enough time
    assert is_travel_feasible(
        "Location A, North",
        "Location B, South",
        available_time_minutes=60,
        from_zone="North",
        to_zone="South"
    )
    
    # Not feasible: insufficient time
    assert not is_travel_feasible(
        "Location A, North",
        "Location B, South",
        available_time_minutes=5,
        from_zone="North",
        to_zone="South"
    )
