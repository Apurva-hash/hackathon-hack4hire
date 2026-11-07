"""Travel time matrix for zone-to-zone travel estimation."""

from typing import Dict

# Travel times in minutes between service zones
# This is a simplified deterministic model for the hackathon
# In production, this would integrate with a mapping service
TRAVEL_TIME_MATRIX: Dict[tuple[str, str], int] = {
    # North Zone connections
    ("North", "North"): 10,      # Within same zone
    ("North", "South"): 45,      # Cross-city
    ("North", "East"): 30,       # Adjacent
    ("North", "West"): 30,       # Adjacent
    ("North", "Downtown"): 25,   # To center
    ("North", "Suburbs"): 20,    # To suburbs
    
    # South Zone connections
    ("South", "North"): 45,
    ("South", "South"): 10,
    ("South", "East"): 30,
    ("South", "West"): 30,
    ("South", "Downtown"): 25,
    ("South", "Suburbs"): 35,
    
    # East Zone connections
    ("East", "North"): 30,
    ("East", "South"): 30,
    ("East", "East"): 10,
    ("East", "West"): 40,
    ("East", "Downtown"): 20,
    ("East", "Suburbs"): 25,
    
    # West Zone connections
    ("West", "North"): 30,
    ("West", "South"): 30,
    ("West", "East"): 40,
    ("West", "West"): 10,
    ("West", "Downtown"): 20,
    ("West", "Suburbs"): 30,
    
    # Downtown connections
    ("Downtown", "North"): 25,
    ("Downtown", "South"): 25,
    ("Downtown", "East"): 20,
    ("Downtown", "West"): 20,
    ("Downtown", "Downtown"): 5,   # Central, quick moves
    ("Downtown", "Suburbs"): 35,
    
    # Suburbs connections
    ("Suburbs", "North"): 20,
    ("Suburbs", "South"): 35,
    ("Suburbs", "East"): 25,
    ("Suburbs", "West"): 30,
    ("Suburbs", "Downtown"): 35,
    ("Suburbs", "Suburbs"): 15,
}


def get_travel_time(from_zone: str, to_zone: str) -> int:
    """
    Get travel time in minutes between two zones.
    
    Args:
        from_zone: Origin zone name
        to_zone: Destination zone name
    
    Returns:
        Travel time in minutes
    """
    # Normalize zone names
    from_zone = from_zone.strip()
    to_zone = to_zone.strip()
    
    # Check if exact match exists
    if (from_zone, to_zone) in TRAVEL_TIME_MATRIX:
        return TRAVEL_TIME_MATRIX[(from_zone, to_zone)]
    
    # If not found, use a default heuristic
    # Same zone: 10 minutes
    if from_zone == to_zone:
        return 10
    
    # Different zones: default to 30 minutes
    return 30


def get_all_zones() -> list[str]:
    """Get list of all known zones."""
    zones = set()
    for from_zone, to_zone in TRAVEL_TIME_MATRIX.keys():
        zones.add(from_zone)
        zones.add(to_zone)
    return sorted(zones)


# Zone descriptions for seed data
ZONE_DESCRIPTIONS = {
    "North": "Northern residential and commercial district",
    "South": "Southern industrial and warehouse area",
    "East": "Eastern suburban communities",
    "West": "Western business and retail corridor",
    "Downtown": "Central business district with high-rise buildings",
    "Suburbs": "Outer suburban residential areas",
}
