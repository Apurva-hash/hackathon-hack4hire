"""Technician API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.technician import (
    TechnicianCreate,
    TechnicianUpdate,
    TechnicianResponse,
    TechnicianListResponse,
    AvailabilityBlockCreate,
    AvailabilityBlockResponse,
)
from app.services.technician_service import TechnicianService

router = APIRouter()


@router.get("/by-skill", response_model=list)
def get_technicians_by_skill(
    skill_name: str = Query(..., description="Skill name keyword to match"),
    db: Session = Depends(get_db)
):
    """Get available technicians matching a skill keyword (for customer booking)."""
    from app.models import Skill, Technician as TechModel
    from sqlalchemy.orm import joinedload
    skills = db.query(Skill).filter(
        Skill.name.ilike(f"%{skill_name}%")
    ).all()
    if not skills:
        return []
    skill_ids = [s.id for s in skills]
    techs = (
        db.query(TechModel)
        .options(joinedload(TechModel.skills), joinedload(TechModel.service_zones))
        .filter(TechModel.status == "available")
        .all()
    )
    matched = []
    for t in techs:
        tech_skill_ids = [s.id for s in t.skills]
        if any(sid in tech_skill_ids for sid in skill_ids):
            matched.append({
                "id": t.id,
                "name": t.name,
                "email": getattr(t, "email", None),
                "phone": getattr(t, "phone", None),
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "shift_start": str(t.shift_start),
                "shift_end": str(t.shift_end),
                "skills": [{"id": s.id, "name": s.name} for s in t.skills],
                "service_zones": [{"id": z.id, "name": z.name} for z in t.service_zones],
            })
    return matched


@router.post("/", response_model=TechnicianResponse, status_code=status.HTTP_201_CREATED)
def create_technician(tech_data: TechnicianCreate, db: Session = Depends(get_db)):
    """Create a new technician."""
    technician = TechnicianService.create_technician(db, tech_data)
    return technician


@router.get("/", response_model=TechnicianListResponse)
def list_technicians(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List technicians."""
    technicians, total = TechnicianService.list_technicians(db, skip=skip, limit=limit)
    return TechnicianListResponse(total=total, technicians=technicians)


@router.get("/{technician_id}", response_model=TechnicianResponse)
def get_technician(technician_id: str, db: Session = Depends(get_db)):
    """Get a technician by ID."""
    technician = TechnicianService.get_technician(db, technician_id)
    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Technician {technician_id} not found"
        )
    return technician


@router.patch("/{technician_id}", response_model=TechnicianResponse)
def update_technician(
    technician_id: str,
    tech_data: TechnicianUpdate,
    db: Session = Depends(get_db)
):
    """Update a technician."""
    technician = TechnicianService.update_technician(db, technician_id, tech_data)
    return technician


@router.post("/{technician_id}/availability", response_model=AvailabilityBlockResponse, status_code=status.HTTP_201_CREATED)
def add_availability_block(
    technician_id: str,
    block_data: AvailabilityBlockCreate,
    db: Session = Depends(get_db)
):
    """Add an unavailable period for a technician."""
    block = TechnicianService.add_availability_block(db, technician_id, block_data)
    return block


@router.delete("/{technician_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_technician(technician_id: str, db: Session = Depends(get_db)):
    """Delete a technician by ID."""
    technician = TechnicianService.get_technician(db, technician_id)
    if not technician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Technician {technician_id} not found"
        )
    db.delete(technician)
    db.commit()
    return None
