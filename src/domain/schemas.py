"""Pydantic schemas for API inputs, outputs and analytical serialization."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.domain.models import RiskLevel, RainfallAlertLevel, LithologyType, LandCoverType


class SlopePointEvaluationRequest(BaseModel):
    """Input parameters to assess a specific slope point."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    slope_angle_deg: float = Field(..., ge=0.0, le=85.0, description="Slope inclination in degrees")
    elevation_m: float = Field(default=650.0, ge=-500.0, le=9000.0, description="Terrain altitude in meters")
    aspect_deg: float = Field(default=180.0, ge=0.0, le=360.0, description="Aspect azimuth in degrees")
    twi: Optional[float] = Field(default=6.5, ge=0.0, le=30.0, description="Topographic Wetness Index")
    accumulated_rain_24h_mm: float = Field(default=25.0, ge=0.0, description="24h accumulated rainfall in mm")
    accumulated_rain_72h_mm: float = Field(default=60.0, ge=0.0, description="72h accumulated rainfall in mm")
    lithology: LithologyType = Field(default=LithologyType.COLLUVIAL_DEPOSITS)
    land_cover: LandCoverType = Field(default=LandCoverType.URBAN_OCCUPATION)
    soil_depth_m: Optional[float] = Field(default=2.5, gt=0.1, le=20.0, description="Depth of potential slip surface")
    cohesion_kpa: Optional[float] = Field(default=12.0, ge=0.0, le=100.0, description="Soil cohesion c' in kPa")
    friction_angle_deg: Optional[float] = Field(default=27.0, ge=5.0, le=55.0, description="Internal friction angle phi'")


class SlopePointEvaluationResponse(BaseModel):
    """Detailed geotechnical and probabilistic risk report for a slope point."""
    latitude: float
    longitude: float
    factor_of_safety: float
    stability_status: str
    geotechnical_risk_level: RiskLevel
    ahp_susceptibility_score: float
    ml_failure_probability: float
    combined_risk_level: RiskLevel
    rainfall_alert_level: RainfallAlertLevel
    recommendations: List[str]


class BatchEvaluationRequest(BaseModel):
    """Batch assessment request for multiple monitored sectors."""
    points: List[SlopePointEvaluationRequest]


class BatchEvaluationResponse(BaseModel):
    """Summary of batch evaluation across monitored points."""
    total_evaluated: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    average_factor_of_safety: float
    critical_hotspots: List[SlopePointEvaluationResponse]


class AHPConsistencyResponse(BaseModel):
    """Result of Saaty Analytic Hierarchy Process consistency verification."""
    criteria: List[str]
    weights: Dict[str, float]
    principal_eigenvalue: float
    consistency_index: float
    consistency_ratio: float
    is_consistent: bool
    explanation: str


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    app_name: str
    version: str
    uptime_status: str
