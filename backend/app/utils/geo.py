"""Haversine distance and ETA utilities."""
import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in kilometres between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def eta_minutes(distance_km: float, avg_speed_kmh: float = 30.0) -> float:
    """Estimate travel time in minutes given distance and average speed."""
    return (distance_km / avg_speed_kmh) * 60.0

