"""Application settings and configuration parameters."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class RainfallThresholds(BaseModel):
    """Critical precipitation thresholds inspired by CEMADEN and Civil Defense."""
    attention_24h_mm: float = Field(default=50.0, description="24h rainfall threshold for Attention level (mm)")
    alert_72h_mm: float = Field(default=90.0, description="72h accumulated rainfall for Alert level (mm)")
    emergency_96h_mm: float = Field(default=140.0, description="96h accumulated rainfall for Emergency level (mm)")


class AppSettings(BaseModel):
    """Global configuration for the climate monitoring system."""
    app_name: str = "Alerta Zona da Mata - Monitoramento Climatico"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    random_seed: int = 42

    rainfall_thresholds: RainfallThresholds = Field(default_factory=RainfallThresholds)

    # Reference study area (Zona da Mata Mineira - Juiz de Fora e microrregioes)
    center_latitude: float = -21.7642
    center_longitude: float = -43.3496


settings = AppSettings()
