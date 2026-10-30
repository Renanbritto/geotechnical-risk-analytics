import pytest
from datetime import datetime, timedelta
from src.services.weather_service import WeatherService, LiveWeatherMetrics

def test_weather_service_current_rain_detection():
    service = WeatherService()
    
    base_dt = datetime(2026, 10, 27, 0, 0)
    times = [(base_dt + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00") for h in range(96)]
    now_time = times[72]  # day 3 (today) at 00:00 or hour 72

    mock_payload = {
        "current": {
            "time": now_time,
            "temperature_2m": 22.0,
            "apparent_temperature": 23.0,
            "weather_code": 3,
            "precipitation": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "wind_speed_10m": 10.0
        },
        "hourly": {
            "time": times,
            "temperature_2m": [22.0] * 96,
            "apparent_temperature": [23.0] * 96,
            "precipitation": [0.0] * 96,
            "precipitation_probability": [90] * 96,
            "weather_code": [3] * 96,
            "wind_speed_10m": [10.0] * 96,
            "wind_direction_10m": [90.0] * 96,
            "wind_gusts_10m": [20.0] * 96,
            "soil_moisture_0_to_7cm": [0.35] * 96,
            "soil_moisture_7_to_28cm": [0.40] * 96,
            "relative_humidity_2m": [85.0] * 96
        }
    }
    # Test case 1: icon_current detects light rain when default is 0.0
    icon_mock = {
        "precipitation": 0.3,
        "rain": 0.0,
        "showers": 0.3,
        "weather_code": 80
    }
    metrics = service._parse_open_meteo_payload(
        latitude=-21.76,
        longitude=-43.35,
        payload=mock_payload,
        icon_current=icon_mock
    )
    assert metrics.current_rain_rate_mmh == 0.3
    assert metrics.is_currently_raining is True
    assert "Pancadas de chuva" in metrics.rain_status_description
    assert metrics.weather_code == 80
    assert metrics.weather_condition_text == "Pancadas de Chuva Leves"

    # Test case 2: no active rain, but recent rain in past hours
    mock_payload_recent = dict(mock_payload)
    mock_hourly = dict(mock_payload["hourly"])
    # Put rain in the past 24h (hours 48 to 71)
    mock_hourly["precipitation"] = [0.8 if 50 <= h <= 71 else 0.0 for h in range(96)]
    mock_payload_recent["hourly"] = mock_hourly

    metrics_recent = service._parse_open_meteo_payload(
        latitude=-21.76,
        longitude=-43.35,
        payload=mock_payload_recent,
        icon_current=None
    )
    assert metrics_recent.is_currently_raining is False
    assert metrics_recent.accumulated_rain_24h_mm > 0.0
    assert "Trégua momentânea" in metrics_recent.rain_status_description or "Sem chuva" in metrics_recent.rain_status_description
