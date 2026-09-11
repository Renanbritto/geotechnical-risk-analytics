"""Application settings and configuration parameters."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class RainfallThresholds(BaseModel):
    """Critical precipitation thresholds inspired by CEMADEN and Civil Defense."""
    attention_24h_mm: float = Field(default=50.0, description="24h rainfall threshold for Attention level (mm)")
    alert_72h_mm: float = Field(default=90.0, description="72h accumulated rainfall for Alert level (mm)")
    emergency_96h_mm: float = Field(default=140.0, description="96h accumulated rainfall for Emergency level (mm)")


class SoilDefaultProperties(BaseModel):
    """Default physical properties for residual tropical soils (Zona da Mata Mineira / Complexo Juiz de Fora)."""
    cohesion_kpa: float = Field(default=12.5, description="Effective soil cohesion c' in kPa")
    friction_angle_deg: float = Field(default=28.0, description="Effective internal friction angle phi' in degrees")
    saturated_unit_weight_kn_m3: float = Field(default=18.5, description="Saturated soil unit weight in kN/m3")
    water_unit_weight_kn_m3: float = Field(default=9.81, description="Water unit weight in kN/m3")
    soil_depth_m: float = Field(default=2.5, description="Representative soil mantle depth in meters")


class AppSettings(BaseModel):
    """Global configuration for the geotechnical risk analysis system."""
    app_name: str = "Geotechnical Risk Analytics Engine"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    random_seed: int = 42

    rainfall_thresholds: RainfallThresholds = Field(default_factory=RainfallThresholds)
    soil_defaults: SoilDefaultProperties = Field(default_factory=SoilDefaultProperties)

    # Reference study area (Zona da Mata Mineira - Juiz de Fora e microrregioes)
    center_latitude: float = -21.7642
    center_longitude: float = -43.3496


settings = AppSettings()
