"""Travel time estimation utilities."""

from typing import Optional
from app.seed.travel_matrix import get_travel_time as get_zone_travel_time


def estimate_travel_time(
    from_location: str,
    to_location: str,
    from_zone: Optional[str] = None,
    to_zone: Optional[str] = None
) -> int:
    """
    Estimate travel time between two locations.
    
    This is a simplified model for the hackathon. In production, this would:
    - Parse addresses
    - Use geocoding
    - Query real-time traffic data
    - Consider route options
    
    Args:
        from_location: Origin location string
        to_location: Destination location string
        from_zone: Origin service zone (if known)
        to_zone: Destination service zone (if known)
    
    Returns:
        Estimated travel time in minutes
    """
    # If zones are provided, use zone-to-zone matrix
    if from_zone and to_zone:
        return get_zone_travel_time(from_zone, to_zone)
    
    # Try to extract zone from location string
    # Format: "123 Main St, ZoneName"
    if "," in from_location and "," in to_location:
        from_parts = from_location.split(",")
        to_parts = to_location.split(",")
        
        if len(from_parts) >= 2 and len(to_parts) >= 2:
            from_zone_extracted = from_parts[-1].strip()
            to_zone_extracted = to_parts[-1].strip()
            return get_zone_travel_time(from_zone_extracted, to_zone_extracted)
    
    # Default fallback
    return 30


def calculate_total_travel_time(locations: list[tuple[str, Optional[str]]]) -> int:
    """
    Calculate total travel time for a sequence of locations.
    
    Args:
        locations: List of (location, zone) tuples in visit order
    
    Returns:
        Total travel time in minutes
    """
    if len(locations) < 2:
        return 0
    
    total = 0
    for i in range(len(locations) - 1):
        from_loc, from_zone = locations[i]
        to_loc, to_zone = locations[i + 1]
        total += estimate_travel_time(from_loc, to_loc, from_zone, to_zone)
    
    return total


def is_travel_feasible(
    from_location: str,
    to_location: str,
    available_time_minutes: int,
    from_zone: Optional[str] = None,
    to_zone: Optional[str] = None
) -> bool:
    """
    Check if travel between locations is feasible within available time.
    
    Args:
        from_location: Origin location
        to_location: Destination location
        available_time_minutes: Available time for travel
        from_zone: Origin zone (optional)
        to_zone: Destination zone (optional)
    
    Returns:
        True if travel is feasible
    """
    required_time = estimate_travel_time(
        from_location,
        to_location,
        from_zone,
        to_zone
    )
    return available_time_minutes >= required_time
