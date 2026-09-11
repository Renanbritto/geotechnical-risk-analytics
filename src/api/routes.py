"""FastAPI endpoint routers for geotechnical risk evaluation and hydrometeorological monitoring."""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, FileResponse
import os
from typing import Dict, Any, List, Optional
from src.domain.schemas import (
    SlopePointEvaluationRequest,
    SlopePointEvaluationResponse,
    LiveSlopeEvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    AHPConsistencyResponse,
    HealthResponse
)
from src.domain.models import RiskLevel, LithologyType, LandCoverType
from src.models.classifier import GeotechnicalRiskClassifier
from src.data.terrain_generator import GeotechnicalDataGenerator
from src.visualization.map_renderer import GeotechnicalMapRenderer
from src.services.weather_service import WeatherService, LiveWeatherMetrics
from src.config.settings import settings

router = APIRouter()

# Singletons for memory efficiency
risk_engine = GeotechnicalRiskClassifier()
data_generator = GeotechnicalDataGenerator()
map_renderer = GeotechnicalMapRenderer()
weather_service = WeatherService()

ZONA_DA_MATA_CITIES = [
    {"id": "juiz-de-fora", "name": "Juiz de Fora", "latitude": -21.7642, "longitude": -43.3496, "default_slope": 38.0, "role": "Polo Regional"},
    {"id": "uba", "name": "Ubá", "latitude": -21.1211, "longitude": -42.9431, "default_slope": 32.0, "role": "Polo Moveleiro"},
    {"id": "vicosa", "name": "Viçosa", "latitude": -20.7546, "longitude": -42.8817, "default_slope": 36.0, "role": "Zona Universitária"},
    {"id": "muriae", "name": "Muriaé", "latitude": -21.1306, "longitude": -42.3664, "default_slope": 35.0, "role": "Bacia do Muriaé"},
    {"id": "cataguases", "name": "Cataguases", "latitude": -21.3892, "longitude": -42.6967, "default_slope": 30.0, "role": "Vale do Pomba"},
    {"id": "santos-dumont", "name": "Santos Dumont", "latitude": -21.4567, "longitude": -43.5525, "default_slope": 42.0, "role": "Alto da Mantiqueira"},
    {"id": "leopoldina", "name": "Leopoldina", "latitude": -21.5322, "longitude": -42.6431, "default_slope": 33.0, "role": "Entroncamento Sul"},
    {"id": "sao-joao-nepomuceno", "name": "São João Nepomuceno", "latitude": -21.5436, "longitude": -43.0089, "default_slope": 34.0, "role": "Vale Central"},
    {"id": "lima-duarte", "name": "Lima Duarte", "latitude": -21.8436, "longitude": -43.7928, "default_slope": 44.0, "role": "Serra de Ibitipoca"}
]


@router.get("/", response_class=HTMLResponse, tags=["Painel Operacional"])
def get_dashboard_ui():
    """Render the operational real-time geotechnical analytics and hydrometeorological dashboard."""
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Geotechnical Risk Analytics</h1><p><a href='/docs'>Swagger API</a></p>")


@router.get("/static/logo.png", tags=["Assets"])
def get_site_logo():
    """Serve the official site logo."""
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo nao encontrado")


@router.get("/favicon.ico", include_in_schema=False)
def get_favicon():
    """Serve favicon for browser tabs."""
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon nao encontrado")


@router.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
def health_check():
    """Health check endpoint confirming operational readiness."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        uptime_status="online"
    )


@router.get("/api/v1/weather/live", response_model=LiveWeatherMetrics, tags=["Meteorologia em Tempo Real"])
def get_live_weather(
    latitude: float = Query(default=-21.7642, ge=-90.0, le=90.0, description="Latitude (Padrao: Juiz de Fora - MG)"),
    longitude: float = Query(default=-43.3496, ge=-180.0, le=180.0, description="Longitude (Padrao: Juiz de Fora - MG)")
):
    """
    Fetch real-time observed rainfall (24h/72h), wind dynamics, and soil moisture from Open-Meteo.
    """
    return weather_service.fetch_live_weather(latitude, longitude)


@router.get("/api/v1/weather/zona-da-mata", tags=["Meteorologia em Tempo Real"])
def get_zona_da_mata_weather():
    """
    Fetch consolidated live wind, rain and temperature metrics across principal Zona da Mata Mineira municipalities.
    """
    results = []
    for c in ZONA_DA_MATA_CITIES:
        w = weather_service.fetch_live_weather(c["latitude"], c["longitude"])
        results.append({
            "id": c["id"],
            "name": c["name"],
            "role": c["role"],
            "latitude": c["latitude"],
            "longitude": c["longitude"],
            "default_slope": c["default_slope"],
            "weather": w
        })

    return {
        "region": "Zona da Mata Mineira",
        "state": "MG",
        "total_monitored": len(results),
        "municipalities": results
    }


@router.get("/api/v1/risk/evaluate-live", response_model=LiveSlopeEvaluationResponse, tags=["Avaliacao em Tempo Real"])
def evaluate_slope_live(
    latitude: float = Query(default=-21.7642, ge=-90.0, le=90.0, description="Latitude da encosta (Juiz de Fora)"),
    longitude: float = Query(default=-43.3496, ge=-180.0, le=180.0, description="Longitude da encosta (Juiz de Fora)"),
    slope_angle_deg: float = Query(default=38.0, ge=1.0, le=80.0, description="Inclinacao em graus"),
    soil_depth_m: float = Query(default=3.5, ge=0.5, le=15.0, description="Espessura do solo em metros"),
    lithology: LithologyType = Query(default=LithologyType.COLLUVIAL_DEPOSITS),
    land_cover: LandCoverType = Query(default=LandCoverType.URBAN_OCCUPATION)
):
    """
    Query real-time meteorological conditions and evaluate geotechnical stability instantly.
    Integrates actual precipitation, wind speed, and soil saturation from ECMWF ERA5-Land.
    """
    live_weather = weather_service.fetch_live_weather(latitude, longitude)

    eval_req = SlopePointEvaluationRequest(
        latitude=latitude,
        longitude=longitude,
        slope_angle_deg=slope_angle_deg,
        elevation_m=750.0,
        aspect_deg=180.0,
        twi=6.8,
        accumulated_rain_24h_mm=live_weather.accumulated_rain_24h_mm,
        accumulated_rain_72h_mm=live_weather.accumulated_rain_72h_mm,
        lithology=lithology,
        land_cover=land_cover,
        soil_depth_m=soil_depth_m
    )

    base_eval = risk_engine.evaluate_point(eval_req)

    # Predictive warning based on forecast precipitation and wind
    warnings = []
    if live_weather.forecast_rain_next_24h_mm >= 50.0:
        warnings.append(
            f"Alerta Pluviometrico Preventivo: Previsao de {live_weather.forecast_rain_next_24h_mm:.1f} mm de chuva nas proximas 24h. "
            "Risco iminente de saturacao completa do manto de solo."
        )
    if live_weather.wind_gusts_10m_kmh >= 45.0:
        warnings.append(
            f"Alerta de Rajadas de Vento: Rajadas de {live_weather.wind_gusts_10m_kmh:.1f} km/h detectadas. "
            "Forcante eolica adicional sobre copas arboreas em encostas saturadas."
        )

    predictive_warning = " | ".join(warnings) if warnings else None

    return LiveSlopeEvaluationResponse(
        latitude=base_eval.latitude,
        longitude=base_eval.longitude,
        slope_angle_deg=slope_angle_deg,
        factor_of_safety=base_eval.factor_of_safety,
        stability_status=base_eval.stability_status,
        geotechnical_risk_level=base_eval.geotechnical_risk_level,
        ahp_susceptibility_score=base_eval.ahp_susceptibility_score,
        ml_failure_probability=base_eval.ml_failure_probability,
        combined_risk_level=base_eval.combined_risk_level,
        rainfall_alert_level=base_eval.rainfall_alert_level,
        recommendations=base_eval.recommendations,
        live_weather=live_weather,
        predictive_warning=predictive_warning
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
def get_spatial_geojson(n_points: int = Query(default=45, ge=5, le=200)):
    """
    Generate GeoJSON FeatureCollection of evaluated slope monitoring points in Zona da Mata.
    Ready for integration into QGIS, ArcGIS or Leaflet frontend web applications.
    """
    simulated_points = data_generator.generate_monitored_points(n_points=n_points)
    evaluated = [risk_engine.evaluate_point(p) for p in simulated_points]
    return data_generator.to_geojson(evaluated)


@router.get("/api/v1/spatial/map-html", tags=["Camadas Espaciais"])
def get_interactive_map_html(n_points: int = Query(default=45, ge=10, le=150)):
    """
    Render and return the full HTML of the interactive Folium Leaflet map centered in Zona da Mata Mineira.
    """
    simulated_points = data_generator.generate_monitored_points(n_points=n_points)
    evaluated = [risk_engine.evaluate_point(p) for p in simulated_points]
    folium_map = map_renderer.render_map(evaluated, output_filepath=None)
    html_content = folium_map.get_root().render()
    return Response(content=html_content, media_type="text/html")
