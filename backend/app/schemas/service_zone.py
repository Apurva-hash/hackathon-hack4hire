"""Service Zone schemas."""

from pydantic import BaseModel, Field


class ServiceZoneBase(BaseModel):
    """Base service zone schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ServiceZoneCreate(ServiceZoneBase):
    """Schema for creating a service zone."""
    pass


class ServiceZoneUpdate(BaseModel):
    """Schema for updating a service zone."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class ServiceZoneResponse(ServiceZoneBase):
    """Schema for service zone response."""
    id: str
    
    class Config:
        from_attributes = True
