"""FastAPI endpoint routers for geotechnical risk evaluation."""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Dict, Any, List
from src.domain.schemas import (
    SlopePointEvaluationRequest,
    SlopePointEvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    AHPConsistencyResponse,
    HealthResponse
)
from src.domain.models import RiskLevel
from src.models.classifier import GeotechnicalRiskClassifier
from src.data.terrain_generator import GeotechnicalDataGenerator
from src.visualization.map_renderer import GeotechnicalMapRenderer
from src.config.settings import settings

router = APIRouter()

# Singletons for memory efficiency
risk_engine = GeotechnicalRiskClassifier()
data_generator = GeotechnicalDataGenerator()
map_renderer = GeotechnicalMapRenderer()


@router.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
def health_check():
    """Health check endpoint confirming operational readiness."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        uptime_status="online"
    )


@router.post("/api/v1/risk/evaluate-point", response_model=SlopePointEvaluationResponse, tags=["Avaliacao Geotecnica"])
def evaluate_slope_point(request: SlopePointEvaluationRequest):
    """
    Evaluate stability, AHP susceptibility and failure probability for a specific slope coordinate.
    """
    try:
        return risk_engine.evaluate_point(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento da encosta: {str(e)}")


@router.post("/api/v1/risk/batch-assessment", response_model=BatchEvaluationResponse, tags=["Avaliacao Geotecnica"])
def batch_assessment(request: BatchEvaluationRequest):
    """
    Execute batch evaluation across multiple monitored slope sectors.
    """
    if not request.points:
        raise HTTPException(status_code=400, detail="A lista de pontos nao pode ser vazia.")

    evaluated = [risk_engine.evaluate_point(p) for p in request.points]

    low_count = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.LOW)
    med_count = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.MEDIUM)
    high_count = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.HIGH)
    crit_count = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.CRITICAL)

    avg_fs = sum(p.factor_of_safety for p in evaluated) / len(evaluated)
    hotspots = [p for p in evaluated if p.combined_risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

    return BatchEvaluationResponse(
        total_evaluated=len(evaluated),
        low_risk_count=low_count,
        medium_risk_count=med_count,
        high_risk_count=high_count,
        critical_risk_count=crit_count,
        average_factor_of_safety=round(avg_fs, 2),
        critical_hotspots=hotspots
    )


@router.get("/api/v1/risk/ahp-consistency", response_model=AHPConsistencyResponse, tags=["Metodologia AHP"])
def get_ahp_consistency():
    """
    Return Saaty Analytic Hierarchy Process consistency metrics (CR, CI, Lambda Max).
    """
    return risk_engine.ahp_engine.get_consistency_report()


@router.get("/api/v1/risk/thresholds", tags=["Pluviometria & Alertas"])
def get_rainfall_thresholds():
    """Return configured civil defense and CEMADEN rainfall alert thresholds."""
    return settings.rainfall_thresholds.model_dump()


@router.get("/api/v1/spatial/geojson", tags=["Camadas Espaciais"])
def get_spatial_geojson(n_points: int = Query(default=35, ge=5, le=200)):
    """
    Generate GeoJSON FeatureCollection of evaluated slope monitoring points.
    Ready for integration into QGIS, ArcGIS or Leaflet frontend web applications.
    """
    simulated_points = data_generator.generate_monitored_points(n_points=n_points)
    evaluated = [risk_engine.evaluate_point(p) for p in simulated_points]
    return data_generator.to_geojson(evaluated)


@router.get("/api/v1/spatial/map-html", tags=["Camadas Espaciais"])
def get_interactive_map_html(n_points: int = Query(default=40, ge=10, le=150)):
    """
    Render and return the full HTML of the interactive Folium Leaflet map.
    """
    simulated_points = data_generator.generate_monitored_points(n_points=n_points)
    evaluated = [risk_engine.evaluate_point(p) for p in simulated_points]
    folium_map = map_renderer.render_map(evaluated, output_filepath=None)
    html_content = folium_map.get_root().render()
    return Response(content=html_content, media_type="text/html")
