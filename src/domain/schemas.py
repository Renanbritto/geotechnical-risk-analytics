"""Pydantic schemas for API inputs, outputs and analytical serialization."""

from pydantic import BaseModel

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app_name: str
    version: str
    uptime_status: str
