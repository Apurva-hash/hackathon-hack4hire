"""Service Zone API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.service_zone import ServiceZoneCreate, ServiceZoneResponse
from app.models.service_zone import ServiceZone

router = APIRouter()


@router.post("/", response_model=ServiceZoneResponse, status_code=status.HTTP_201_CREATED)
def create_service_zone(zone_data: ServiceZoneCreate, db: Session = Depends(get_db)):
    """Create a new service zone."""
    # Check if zone already exists
    existing = db.query(ServiceZone).filter(ServiceZone.name == zone_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service zone '{zone_data.name}' already exists"
        )
    
    zone = ServiceZone(**zone_data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/", response_model=List[ServiceZoneResponse])
def list_service_zones(db: Session = Depends(get_db)):
    """List all service zones."""
    zones = db.query(ServiceZone).all()
    return zones


@router.get("/{zone_id}", response_model=ServiceZoneResponse)
def get_service_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get a service zone by ID."""
    zone = db.query(ServiceZone).filter(ServiceZone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service zone {zone_id} not found"
        )
    return zone
