"""FastAPI endpoint routers for hydrometeorological monitoring."""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, FileResponse
import os

from src.domain.schemas import HealthResponse
from src.services.weather_service import WeatherService, LiveWeatherMetrics
from src.config.settings import settings

router = APIRouter()

# Singletons for memory efficiency
weather_service = WeatherService()

ZONA_DA_MATA_CITIES = [
    {"id": "juiz-de-fora", "name": "Juiz de Fora", "latitude": -21.7642, "longitude": -43.3496, "role": "Polo Regional"},
    {"id": "uba", "name": "Ub\u00e1", "latitude": -21.1211, "longitude": -42.9431, "role": "Polo Moveleiro"},
    {"id": "vicosa", "name": "Vi\u00e7osa", "latitude": -20.7546, "longitude": -42.8817, "role": "Zona Universit\u00e1ria"},
    {"id": "muriae", "name": "Muria\u00e9", "latitude": -21.1306, "longitude": -42.3664, "role": "Bacia do Muria\u00e9"},
    {"id": "cataguases", "name": "Cataguases", "latitude": -21.3892, "longitude": -42.6967, "role": "Vale do Pomba"},
    {"id": "santos-dumont", "name": "Santos Dumont", "latitude": -21.4567, "longitude": -43.5525, "role": "Alto da Mantiqueira"},
    {"id": "leopoldina", "name": "Leopoldina", "latitude": -21.5322, "longitude": -42.6431, "role": "Entroncamento Sul"},
    {"id": "sao-joao-nepomuceno", "name": "S\u00e3o Jo\u00e3o Nepomuceno", "latitude": -21.5436, "longitude": -43.0089, "role": "Vale Central"},
    {"id": "lima-duarte", "name": "Lima Duarte", "latitude": -21.8436, "longitude": -43.7928, "role": "Serra de Ibitipoca"}
]


@router.get("/", response_class=HTMLResponse, tags=["Painel Operacional"])
def get_dashboard_ui():
    """Render the operational real-time hydrometeorological dashboard."""
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            response = HTMLResponse(content=content)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    return HTMLResponse(content="<h1>Monitoramento Climatico</h1><p><a href='/docs'>Swagger API</a></p>")


@router.get("/static/logo.png", tags=["Assets"])
def get_site_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo nao encontrado")


@router.get("/static/alertageo_logo.jpg", tags=["Assets"])
def get_alertageo_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "alertageo_logo.jpg")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/jpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404, detail="Logo AlertaGeo nao encontrado")


@router.get("/static/alerta_chuva.png", tags=["Assets"])
def get_alerta_chuva_banner():
    banner_path = os.path.join(os.path.dirname(__file__), "..", "static", "alerta_chuva.png")
    if os.path.exists(banner_path):
        return FileResponse(banner_path, media_type="image/png", headers={"Cache-Control": "max-age=86400"})
    raise HTTPException(status_code=404, detail="Banner Alerta Chuva nao encontrado")


@router.get("/favicon.ico", include_in_schema=False)
def get_favicon():
    logo_path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon nao encontrado")


@router.get("/health", response_model=HealthResponse, tags=["Monitoramento"])
def health_check():
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
            "weather": w
        })

    return {
        "region": "Zona da Mata Mineira",
        "state": "MG",
        "total_monitored": len(results),
        "municipalities": results
    }

@router.get("/api/v1/risk/thresholds", tags=["Pluviometria & Alertas"])
def get_rainfall_thresholds():
    """Return configured civil defense and CEMADEN rainfall alert thresholds."""
    return settings.rainfall_thresholds.model_dump()
