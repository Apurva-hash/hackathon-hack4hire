"""Skill API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.skill import SkillCreate, SkillResponse
from app.models.skill import Skill

router = APIRouter()


@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(skill_data: SkillCreate, db: Session = Depends(get_db)):
    """Create a new skill."""
    # Check if skill already exists
    existing = db.query(Skill).filter(Skill.name == skill_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill_data.name}' already exists"
        )
    
    skill = Skill(**skill_data.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/", response_model=List[SkillResponse])
def list_skills(db: Session = Depends(get_db)):
    """List all skills."""
    skills = db.query(Skill).all()
    return skills


@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    """Get a skill by ID."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_id} not found"
        )
    return skill
