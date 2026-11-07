"""Skill schemas."""

from pydantic import BaseModel, Field


class SkillBase(BaseModel):
    """Base skill schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class SkillCreate(SkillBase):
    """Schema for creating a skill."""
    pass


class SkillUpdate(BaseModel):
    """Schema for updating a skill."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class SkillResponse(SkillBase):
    """Schema for skill response."""
    id: str
    
    class Config:
        from_attributes = True
