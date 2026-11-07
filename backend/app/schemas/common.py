"""Common schemas and base models."""

from pydantic import BaseModel
from datetime import datetime


class TimestampSchema(BaseModel):
    """Mixin for timestamps."""
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: str | None = None
    field: str | None = None
