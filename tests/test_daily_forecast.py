import pytest
from src.services.weather_service import WeatherService, LiveWeatherMetrics, DailyForecastItem

def test_daily_forecast_parsing():
    service = WeatherService()
    mock_payload = {
        "current": {
            "time": "2026-11-05T12:00",
            "temperature_2m": 24.0,
            "apparent_temperature": 25.0,
            "weather_code": 1,
            "precipitation": 0.0
        },
        "hourly": {
            "time": [f"2026-11-05T{h % 24:02d}:00" for h in range(96)],
            "temperature_2m": [22.0] * 96,
            "apparent_temperature": [23.0] * 96,
            "precipitation": [0.0] * 96,
            "precipitation_probability": [20] * 96,
            "weather_code": [1] * 96,
            "wind_speed_10m": [12.0] * 96,
            "wind_direction_10m": [90.0] * 96,
            "wind_gusts_10m": [25.0] * 96,
            "soil_moisture_0_to_7cm": [0.35] * 96,
            "soil_moisture_7_to_28cm": [0.40] * 96,
            "relative_humidity_2m": [70.0] * 96
        },
        "daily": {
            "time": [
                "2026-11-05", "2026-11-06", "2026-11-07", "2026-11-08",
                "2026-11-09", "2026-11-10", "2026-11-11"
            ],
            "weather_code": [1, 80, 95, 2, 3, 51, 0],
            "temperature_2m_max": [28.0, 26.5, 29.0, 24.0, 22.0, 21.0, 23.5],
            "temperature_2m_min": [19.0, 18.5, 20.0, 16.0, 15.0, 14.5, 15.0],
            "apparent_temperature_max": [30.0, 28.0, 32.0, 25.0, 23.0, 22.0, 24.0],
            "apparent_temperature_min": [20.0, 19.0, 21.0, 17.0, 16.0, 15.0, 16.0],
            "precipitation_sum": [0.0, 6.5, 18.2, 0.0, 0.2, 2.1, 0.0],
            "precipitation_probability_max": [10, 85, 95, 20, 30, 60, 5],
            "wind_speed_10m_max": [12.0, 15.0, 22.0, 14.0, 11.0, 10.0, 9.0],
            "wind_gusts_10m_max": [25.0, 35.0, 55.0, 28.0, 20.0, 18.0, 15.0],
            "uv_index_max": [8.0, 7.5, 9.0, 6.0, 5.0, 4.0, 7.0]
        }
    }
    metrics = service._parse_open_meteo_payload(
        latitude=-21.76,
        longitude=-43.35,
        payload=mock_payload
    )

    assert len(metrics.daily_forecast) == 7
    d0 = metrics.daily_forecast[0]
    assert d0.day_label == "Hoje"
    assert d0.temp_max_c == 28.0
    assert d0.temp_min_c == 19.0
    assert d0.precipitation_sum_mm == 0.0

    d1 = metrics.daily_forecast[1]
    assert d1.day_label == "Amanhã"
    assert d1.temp_max_c == 26.5
    assert d1.precipitation_sum_mm == 6.5
    assert d1.precipitation_probability_pct == 85

    d2 = metrics.daily_forecast[2]
    assert "Sáb" in d2.day_label
    assert d2.weather_code == 95
    assert "Tempestade" in d2.weather_description
    assert d2.precipitation_sum_mm == 18.2

def test_daily_forecast_fallback():
    service = WeatherService(timeout_seconds=0.001)
    service.OPEN_METEO_URL = "http://127.0.0.1:9999/invalid"
    metrics = service.fetch_live_weather(latitude=-21.76, longitude=-43.35)
    assert len(metrics.daily_forecast) == 8
    assert metrics.daily_forecast[0].day_label == "Hoje"
    assert metrics.daily_forecast[1].day_label == "Amanhã"
