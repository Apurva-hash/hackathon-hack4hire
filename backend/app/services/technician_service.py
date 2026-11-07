"""Technician service - Business logic for technician management."""

from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from fastapi import HTTPException, status

from app.models import Technician, Skill, ServiceZone, AvailabilityBlock
from app.schemas.technician import TechnicianCreate, TechnicianUpdate, AvailabilityBlockCreate


class TechnicianService:
    """Service for technician-related operations."""
    
    @staticmethod
    def create_technician(db: Session, tech_data: TechnicianCreate) -> Technician:
        """Create a new technician."""
        # Validate shift times
        if tech_data.shift_end <= tech_data.shift_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="shift_end must be after shift_start"
            )
        
        # Validate skills exist
        if tech_data.skill_ids:
            skills = db.query(Skill).filter(Skill.id.in_(tech_data.skill_ids)).all()
            if len(skills) != len(tech_data.skill_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more skills not found"
                )
        
        # Validate service zones exist
        if tech_data.service_zone_ids:
            zones = db.query(ServiceZone).filter(ServiceZone.id.in_(tech_data.service_zone_ids)).all()
            if len(zones) != len(tech_data.service_zone_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more service zones not found"
                )
        
        # Resolve zone_ids alias
        zone_ids = tech_data.service_zone_ids or tech_data.zone_ids or []

        # Create technician
        technician = Technician(
            name=tech_data.name,
            email=getattr(tech_data, 'email', None),
            phone=getattr(tech_data, 'phone', None),
            current_location=tech_data.current_location,
            shift_start=tech_data.shift_start,
            shift_end=tech_data.shift_end,
            status=tech_data.status,
        )
        
        # Add skills
        if tech_data.skill_ids:
            skills = db.query(Skill).filter(Skill.id.in_(tech_data.skill_ids)).all()
            technician.skills = skills
        
        # Add service zones
        if zone_ids:
            zones = db.query(ServiceZone).filter(ServiceZone.id.in_(zone_ids)).all()
            technician.service_zones = zones
        
        db.add(technician)
        db.commit()
        db.refresh(technician)
        return technician
    
    @staticmethod
    def get_technician(db: Session, technician_id: str) -> Optional[Technician]:
        """Get a technician by ID."""
        return (
            db.query(Technician)
            .options(
                joinedload(Technician.skills),
                joinedload(Technician.service_zones),
                joinedload(Technician.availability_blocks),
            )
            .filter(Technician.id == technician_id)
            .first()
        )
    
    @staticmethod
    def list_technicians(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Technician], int]:
        """List technicians."""
        query = db.query(Technician).options(
            joinedload(Technician.skills),
            joinedload(Technician.service_zones),
        )
        
        total = query.count()
        technicians = query.offset(skip).limit(limit).all()
        return technicians, total
    
    @staticmethod
    def update_technician(db: Session, technician_id: str, tech_data: TechnicianUpdate) -> Technician:
        """Update a technician."""
        technician = TechnicianService.get_technician(db, technician_id)
        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician {technician_id} not found"
            )
        
        update_data = tech_data.model_dump(exclude_unset=True)
        
        # Validate shift times if both are being updated
        if 'shift_start' in update_data and 'shift_end' in update_data:
            if update_data['shift_end'] <= update_data['shift_start']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="shift_end must be after shift_start"
                )
        
        # Handle skill_ids separately
        if 'skill_ids' in update_data:
            skill_ids = update_data.pop('skill_ids')
            if skill_ids is not None:
                skills = db.query(Skill).filter(Skill.id.in_(skill_ids)).all()
                if len(skills) != len(skill_ids):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or more skills not found"
                    )
                technician.skills = skills
        
        # Handle service_zone_ids separately
        if 'service_zone_ids' in update_data:
            zone_ids = update_data.pop('service_zone_ids')
            if zone_ids is not None:
                zones = db.query(ServiceZone).filter(ServiceZone.id.in_(zone_ids)).all()
                if len(zones) != len(zone_ids):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or more service zones not found"
                    )
                technician.service_zones = zones
        
        for key, value in update_data.items():
            setattr(technician, key, value)
        
        db.commit()
        db.refresh(technician)
        return technician
    
    @staticmethod
    def add_availability_block(
        db: Session,
        technician_id: str,
        block_data: AvailabilityBlockCreate
    ) -> AvailabilityBlock:
        """Add an unavailable period for a technician."""
        technician = TechnicianService.get_technician(db, technician_id)
        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician {technician_id} not found"
            )
        
        if block_data.end_time <= block_data.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be after start_time"
            )
        
        block = AvailabilityBlock(
            technician_id=technician_id,
            start_time=block_data.start_time,
            end_time=block_data.end_time,
            reason=block_data.reason,
        )
        
        db.add(block)
        db.commit()
        db.refresh(block)
        return block
