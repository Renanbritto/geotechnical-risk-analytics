"""Real-time meteorological and hydrological data ingestion service."""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


def degrees_to_cardinal(deg: float) -> str:
    """Convert meteorological wind direction in degrees to 16-point cardinal compass string."""
    dirs = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return dirs[idx]


class LiveWeatherMetrics(BaseModel):
    """Normalized live hydrometeorological data for geotechnical analysis."""
    latitude: float
    longitude: float
    accumulated_rain_24h_mm: float = Field(..., description="Observed rainfall over the last 24 hours (mm)")
    accumulated_rain_72h_mm: float = Field(..., description="Observed rainfall over the last 72 hours (mm)")
    forecast_rain_next_24h_mm: float = Field(default=0.0, description="Forecast precipitation for the next 24h (mm)")
    current_rain_rate_mmh: float = Field(default=0.0, description="Current instantaneous precipitation rate (mm/h)")
    soil_moisture_volumetric_m3_m3: float = Field(default=0.35, description="Volumetric soil moisture (0-28cm) in m3/m3")
    temperature_c: float = Field(default=22.0, description="Current ambient temperature in Celsius")
    relative_humidity_pct: float = Field(default=80.0, description="Relative humidity percentage")
    wind_speed_10m_kmh: float = Field(default=14.0, description="Current wind speed at 10m height (km/h)")
    wind_gusts_10m_kmh: float = Field(default=28.0, description="Current wind gusts at 10m height (km/h)")
    wind_direction_10m_deg: float = Field(default=135.0, description="Wind direction in meteorological degrees")
    wind_cardinal_direction: str = Field(default="SE", description="Wind cardinal compass direction")
    data_source: str = Field(default="Open-Meteo (ECMWF ERA5-Land / GFS)")
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_live_data: bool = True


class WeatherService:
    """
    Ingests live meteorological data from Open-Meteo API (ECMWF, GFS) and provides optional Windy fallback.
    Free tier requires no API key and provides global coverage at high spatial resolution.
    """

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_seconds: float = 6.0, windy_api_key: Optional[str] = None):
        self.timeout = timeout_seconds
        self.windy_api_key = windy_api_key

    def fetch_live_weather(self, latitude: float, longitude: float) -> LiveWeatherMetrics:
        """
        Synchronously fetch real-time and antecedent precipitation, wind dynamics, and soil moisture.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "hourly": "precipitation,soil_moisture_0_to_7cm,soil_moisture_7_to_28cm,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "past_days": 3,
            "forecast_days": 2,
            "timezone": "America/Sao_Paulo"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.OPEN_METEO_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                return self._parse_open_meteo_payload(latitude, longitude, data)
            else:
                return self._generate_fallback(latitude, longitude, reason=f"Status HTTP {response.status_code}")

        except Exception as exc:
            return self._generate_fallback(latitude, longitude, reason=f"Erro de conexao ({type(exc).__name__})")

    def _parse_open_meteo_payload(
        self,
        latitude: float,
        longitude: float,
        payload: Dict[str, Any]
    ) -> LiveWeatherMetrics:
        current = payload.get("current", {})
        hourly = payload.get("hourly", {})
        precip = hourly.get("precipitation", [])
        soil_0_7 = hourly.get("soil_moisture_0_to_7cm", [])
        soil_7_28 = hourly.get("soil_moisture_7_to_28cm", [])
        temps = hourly.get("temperature_2m", [])
        humidities = hourly.get("relative_humidity_2m", [])
        wind_speeds = hourly.get("wind_speed_10m", [])
        wind_dirs = hourly.get("wind_direction_10m", [])
        wind_gusts = hourly.get("wind_gusts_10m", [])

        # past_days=3 provides 72 hours of antecedent records
        current_idx = min(72, len(precip) - 1) if len(precip) >= 72 else len(precip) // 2

        # 1. Past 24h precipitation sum
        start_24h = max(0, current_idx - 24)
        rain_24h = float(sum(p for p in precip[start_24h:current_idx] if p is not None))

        # 2. Past 72h precipitation sum
        start_72h = max(0, current_idx - 72)
        rain_72h = float(sum(p for p in precip[start_72h:current_idx] if p is not None))

        # 3. Forecast next 24h precipitation
        end_forecast = min(len(precip), current_idx + 24)
        rain_forecast_24h = float(sum(p for p in precip[current_idx:end_forecast] if p is not None))

        # 4. Volumetric soil moisture
        moist_0_7 = soil_0_7[current_idx] if (soil_0_7 and current_idx < len(soil_0_7) and soil_0_7[current_idx] is not None) else 0.32
        moist_7_28 = soil_7_28[current_idx] if (soil_7_28 and current_idx < len(soil_7_28) and soil_7_28[current_idx] is not None) else 0.35
        avg_soil_moisture = float((moist_0_7 + moist_7_28) / 2.0)

        # 5. Temperature and Humidity (prefer current block, fallback to hourly)
        curr_temp = current.get("temperature_2m")
        if curr_temp is None:
            curr_temp = temps[current_idx] if (temps and current_idx < len(temps) and temps[current_idx] is not None) else 22.0

        curr_rh = current.get("relative_humidity_2m")
        if curr_rh is None:
            curr_rh = humidities[current_idx] if (humidities and current_idx < len(humidities) and humidities[current_idx] is not None) else 80.0

        # 6. Wind speed, gusts and direction
        curr_wind = current.get("wind_speed_10m")
        if curr_wind is None:
            curr_wind = wind_speeds[current_idx] if (wind_speeds and current_idx < len(wind_speeds) and wind_speeds[current_idx] is not None) else 14.0

        curr_gust = current.get("wind_gusts_10m")
        if curr_gust is None:
            curr_gust = wind_gusts[current_idx] if (wind_gusts and current_idx < len(wind_gusts) and wind_gusts[current_idx] is not None) else 28.0

        curr_dir = current.get("wind_direction_10m")
        if curr_dir is None:
            curr_dir = wind_dirs[current_idx] if (wind_dirs and current_idx < len(wind_dirs) and wind_dirs[current_idx] is not None) else 135.0

        curr_rain_rate = current.get("precipitation")
        if curr_rain_rate is None:
            curr_rain_rate = precip[current_idx] if (precip and current_idx < len(precip) and precip[current_idx] is not None) else 0.0

        cardinal_dir = degrees_to_cardinal(float(curr_dir))

        return LiveWeatherMetrics(
            latitude=latitude,
            longitude=longitude,
            accumulated_rain_24h_mm=round(float(rain_24h), 1),
            accumulated_rain_72h_mm=round(float(rain_72h), 1),
            forecast_rain_next_24h_mm=round(float(rain_forecast_24h), 1),
            current_rain_rate_mmh=round(float(curr_rain_rate), 2),
            soil_moisture_volumetric_m3_m3=round(float(avg_soil_moisture), 3),
            temperature_c=round(float(curr_temp), 1),
            relative_humidity_pct=round(float(curr_rh), 1),
            wind_speed_10m_kmh=round(float(curr_wind), 1),
            wind_gusts_10m_kmh=round(float(curr_gust), 1),
            wind_direction_10m_deg=round(float(curr_dir), 1),
            wind_cardinal_direction=cardinal_dir,
            data_source="Open-Meteo API (ECMWF ERA5-Land)",
            is_live_data=True
        )

    def _generate_fallback(self, latitude: float, longitude: float, reason: str) -> LiveWeatherMetrics:
        """Fallback simulation for offline test environments or network interruptions."""
        return LiveWeatherMetrics(
            latitude=latitude,
            longitude=longitude,
            accumulated_rain_24h_mm=35.0,
            accumulated_rain_72h_mm=75.0,
            forecast_rain_next_24h_mm=20.0,
            current_rain_rate_mmh=1.5,
            soil_moisture_volumetric_m3_m3=0.34,
            temperature_c=21.5,
            relative_humidity_pct=85.0,
            wind_speed_10m_kmh=16.0,
            wind_gusts_10m_kmh=32.0,
            wind_direction_10m_deg=140.0,
            wind_cardinal_direction="SE",
            data_source=f"Modo Fallback / Offline ({reason})",
            is_live_data=False
        )
