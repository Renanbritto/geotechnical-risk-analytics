"""Unit and integration tests for the real-time weather service."""

import pytest
from fastapi.testclient import TestClient
from src.services.weather_service import WeatherService, LiveWeatherMetrics
from src.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_weather_service_parsing():
    service = WeatherService()
    # Mock Open-Meteo response structure
    mock_payload = {
        "hourly": {
            "precipitation": [0.0] * 50 + [5.0] * 10 + [10.0] * 12 + [2.0] * 24,
            "soil_moisture_0_to_7cm": [0.38] * 96,
            "soil_moisture_7_to_28cm": [0.42] * 96,
            "temperature_2m": [24.0] * 96,
            "relative_humidity_2m": [82.0] * 96
        }
    }
    metrics = service._parse_open_meteo_payload(
        latitude=-22.42,
        longitude=-42.97,
        payload=mock_payload
    )

    assert isinstance(metrics, LiveWeatherMetrics)
    assert metrics.accumulated_rain_24h_mm > 0.0
    assert metrics.accumulated_rain_72h_mm >= metrics.accumulated_rain_24h_mm
    assert metrics.soil_moisture_volumetric_m3_m3 == 0.40
    assert metrics.temperature_c == 24.0


def test_weather_service_fallback():
    service = WeatherService(timeout_seconds=0.001)
    # Simulate timeout / bad URL
    service.OPEN_METEO_URL = "http://127.0.0.1:9999/invalid-endpoint"
    metrics = service.fetch_live_weather(latitude=-22.42, longitude=-42.97)

    assert isinstance(metrics, LiveWeatherMetrics)
    assert metrics.is_live_data is False
    assert "Fallback" in metrics.data_source
    assert metrics.accumulated_rain_24h_mm > 0.0


def test_api_live_weather_endpoint(client):
    response = client.get("/api/v1/weather/live?latitude=-22.42&longitude=-42.97")
    assert response.status_code == 200
    data = response.json()
    assert "accumulated_rain_24h_mm" in data
    assert "accumulated_rain_72h_mm" in data
    assert "soil_moisture_volumetric_m3_m3" in data


def test_api_evaluate_live_endpoint(client):
    response = client.get("/api/v1/risk/evaluate-live?latitude=-22.42&longitude=-42.97&slope_angle_deg=35.0")
    assert response.status_code == 200
    data = response.json()
    assert "factor_of_safety" in data
    assert "combined_risk_level" in data
    assert "live_weather" in data
    assert "recommendations" in data
    assert data["live_weather"]["latitude"] == -22.42

def test_weather_service_hourly_forecast_and_temperature():
    service = WeatherService()
    mock_payload = {
        "current": {
            "temperature_2m": 26.5,
            "apparent_temperature": 28.2,
            "weather_code": 2,
            "precipitation": 0.0,
            "wind_speed_10m": 12.0
        },
        "hourly": {
            "time": [f"2026-09-11T{h % 24:02d}:00" for h in range(96)],
            "temperature_2m": [22.0 + (h % 8) for h in range(96)],
            "apparent_temperature": [23.0 + (h % 8) for h in range(96)],
            "precipitation": [0.5 if h % 4 == 0 else 0.0 for h in range(96)],
            "precipitation_probability": [40 if h % 4 == 0 else 10 for h in range(96)],
            "weather_code": [80 if h % 4 == 0 else 1 for h in range(96)],
            "wind_speed_10m": [15.0 for h in range(96)],
            "wind_direction_10m": [90.0 for h in range(96)],
            "wind_gusts_10m": [30.0 for h in range(96)],
            "soil_moisture_0_to_7cm": [0.35] * 96,
            "soil_moisture_7_to_28cm": [0.40] * 96,
            "relative_humidity_2m": [75.0] * 96
        }
    }
    metrics = service._parse_open_meteo_payload(latitude=-21.76, longitude=-43.35, payload=mock_payload)
    assert metrics.temperature_c == 26.5
    assert metrics.apparent_temperature_c == 28.2
    assert metrics.weather_condition_text == "Parcialmente Nublado"
    assert len(metrics.hourly_forecast) == 24
    assert metrics.hourly_forecast[0].time is not None
    assert metrics.hourly_forecast[0].weather_description is not None
