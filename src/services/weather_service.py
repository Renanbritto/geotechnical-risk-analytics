"""Real-time meteorological and hydrological data ingestion service."""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


def degrees_to_cardinal(deg: float) -> str:
    """Convert meteorological wind direction in degrees to 16-point cardinal compass string."""
    dirs = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return dirs[idx]


def wmo_code_to_description(code: int) -> str:
    """Translate WMO weather interpretation code into friendly Portuguese text."""
    wmo_map = {
        0: "Céu Limpo",
        1: "Predomínio de Sol",
        2: "Parcialmente Nublado",
        3: "Nublado",
        45: "Nevoeiro",
        48: "Nevoeiro com Depósito",
        51: "Chuvisco Fraco",
        53: "Chuvisco Moderado",
        55: "Chuvisco Denso",
        56: "Garoa Congelante Fraca",
        57: "Garoa Congelante Densa",
        61: "Chuva Fraca",
        63: "Chuva Moderada",
        65: "Chuva Forte",
        66: "Chuva Congelante Fraca",
        67: "Chuva Congelante Forte",
        71: "Queda de Neve Fraca",
        73: "Queda de Neve Moderada",
        75: "Queda de Neve Forte",
        80: "Pancadas de Chuva Leves",
        81: "Pancadas de Chuva Moderadas",
        82: "Pancadas de Chuva Torrenciais",
        85: "Pancadas de Neve Fracas",
        86: "Pancadas de Neve Fortes",
        95: "Tempestade com Trovoadas",
        96: "Tempestade com Granizo Leve",
        99: "Tempestade Severa com Granizo"
    }
    return wmo_map.get(code, "Tempo Estável")


class HourlyForecastItem(BaseModel):
    """Forecast metrics for a specific upcoming hour."""
    time: str = Field(..., description="Hour label (e.g. 15:00)")
    datetime_iso: str = Field(..., description="Full ISO timestamp")
    temperature_c: float = Field(..., description="Ambient temperature in Celsius")
    apparent_temperature_c: float = Field(default=22.0, description="Apparent thermal sensation in Celsius")
    precipitation_mm: float = Field(..., description="Forecast rainfall volume in mm")
    precipitation_probability_pct: int = Field(default=0, description="Rainfall probability (0-100%)")
    weather_code: int = Field(default=0, description="WMO weather code")
    weather_description: str = Field(default="Tempo Estável", description="Friendly weather description in Portuguese")
    wind_speed_kmh: float = Field(default=10.0, description="Wind speed at 10m in km/h")


class LiveWeatherMetrics(BaseModel):
    """Normalized live hydrometeorological data for public awareness and geotechnical analysis."""
    latitude: float
    longitude: float
    temperature_c: float = Field(default=22.0, description="Current ambient temperature in Celsius")
    apparent_temperature_c: float = Field(default=23.0, description="Current thermal sensation in Celsius")
    weather_code: int = Field(default=1, description="Current WMO weather code")
    weather_condition_text: str = Field(default="Predomínio de Sol", description="Friendly weather condition text")
    temp_max_24h_c: float = Field(default=28.0, description="Maximum forecast temperature for the next 24 hours in Celsius")
    temp_min_24h_c: float = Field(default=18.0, description="Minimum forecast temperature for the next 24 hours in Celsius")
    accumulated_rain_24h_mm: float = Field(..., description="Observed rainfall over the last 24 hours (mm)")
    accumulated_rain_72h_mm: float = Field(..., description="Observed rainfall over the last 72 hours (mm)")
    forecast_rain_next_24h_mm: float = Field(default=0.0, description="Forecast precipitation for the next 24h (mm)")
    current_rain_rate_mmh: float = Field(default=0.0, description="Current instantaneous precipitation rate (mm/h)")
    soil_moisture_volumetric_m3_m3: float = Field(default=0.35, description="Volumetric soil moisture (0-28cm) in m3/m3")
    relative_humidity_pct: float = Field(default=80.0, description="Relative humidity percentage")
    wind_speed_10m_kmh: float = Field(default=14.0, description="Current wind speed at 10m height (km/h)")
    wind_gusts_10m_kmh: float = Field(default=28.0, description="Current wind gusts at 10m height (km/h)")
    wind_direction_10m_deg: float = Field(default=135.0, description="Wind direction in meteorological degrees")
    wind_cardinal_direction: str = Field(default="SE", description="Wind cardinal compass direction")
    hourly_forecast: List[HourlyForecastItem] = Field(default_factory=list, description="Hour-by-hour forecast for the next 24 hours")
    data_source: str = Field(default="Open-Meteo API (ECMWF ERA5-Land / GFS)")
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_live_data: bool = True


class WeatherService:
    """
    Ingests live meteorological and forecast data from Open-Meteo API (ECMWF, GFS).
    Provides friendly metrics for the general public and physical parameters for slope stability.
    """

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_seconds: float = 6.0, windy_api_key: Optional[str] = None):
        self.timeout = timeout_seconds
        self.windy_api_key = windy_api_key

    def fetch_live_weather(self, latitude: float, longitude: float) -> LiveWeatherMetrics:
        """
        Synchronously fetch real-time and antecedent precipitation, wind dynamics, temperature,
        apparent temperature, and hour-by-hour forecast.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,weather_code,precipitation,rain,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "hourly": "temperature_2m,apparent_temperature,precipitation,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,soil_moisture_0_to_7cm,soil_moisture_7_to_28cm",
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
        times = hourly.get("time", [])
        precip = hourly.get("precipitation", [])
        precip_probs = hourly.get("precipitation_probability", [])
        weather_codes = hourly.get("weather_code", [])
        soil_0_7 = hourly.get("soil_moisture_0_to_7cm", [])
        soil_7_28 = hourly.get("soil_moisture_7_to_28cm", [])
        temps = hourly.get("temperature_2m", [])
        apparent_temps = hourly.get("apparent_temperature", [])
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

        # 5. Temperature and Apparent Temperature
        curr_temp = current.get("temperature_2m")
        if curr_temp is None:
            curr_temp = temps[current_idx] if (temps and current_idx < len(temps) and temps[current_idx] is not None) else 22.0

        curr_apparent = current.get("apparent_temperature")
        if curr_apparent is None:
            curr_apparent = apparent_temps[current_idx] if (apparent_temps and current_idx < len(apparent_temps) and apparent_temps[current_idx] is not None) else curr_temp

        curr_weather_code = current.get("weather_code")
        if curr_weather_code is None:
            curr_weather_code = weather_codes[current_idx] if (weather_codes and current_idx < len(weather_codes) and weather_codes[current_idx] is not None) else 1

        weather_desc = wmo_code_to_description(int(curr_weather_code))

        # 6. Temperature Min and Max for upcoming 24 hours
        next_24_temps = [t for t in temps[current_idx:end_forecast] if t is not None]
        temp_max_24h = max(next_24_temps) if next_24_temps else (float(curr_temp) + 4.0)
        temp_min_24h = min(next_24_temps) if next_24_temps else (float(curr_temp) - 5.0)

        curr_rh = current.get("relative_humidity_2m")
        if curr_rh is None:
            curr_rh = humidities[current_idx] if (humidities and current_idx < len(humidities) and humidities[current_idx] is not None) else 80.0

        # 7. Wind speed, gusts and direction
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

        # 8. Hour-by-hour forecast items for next 24 hours
        hourly_items = []
        for i in range(current_idx, min(len(precip), current_idx + 24)):
            t_str = times[i] if (times and i < len(times)) else f"H+{i - current_idx}"
            # Extract time e.g. "2026-09-11T16:00" -> "16:00"
            short_time = t_str.split("T")[-1] if "T" in t_str else t_str
            t_val = float(temps[i]) if (temps and i < len(temps) and temps[i] is not None) else float(curr_temp)
            app_t_val = float(apparent_temps[i]) if (apparent_temps and i < len(apparent_temps) and apparent_temps[i] is not None) else t_val
            p_val = float(precip[i]) if (precip and i < len(precip) and precip[i] is not None) else 0.0
            p_prob = int(precip_probs[i]) if (precip_probs and i < len(precip_probs) and precip_probs[i] is not None) else 0
            w_code = int(weather_codes[i]) if (weather_codes and i < len(weather_codes) and weather_codes[i] is not None) else 1
            w_spd = float(wind_speeds[i]) if (wind_speeds and i < len(wind_speeds) and wind_speeds[i] is not None) else float(curr_wind)

            hourly_items.append(HourlyForecastItem(
                time=short_time,
                datetime_iso=t_str,
                temperature_c=round(t_val, 1),
                apparent_temperature_c=round(app_t_val, 1),
                precipitation_mm=round(p_val, 1),
                precipitation_probability_pct=p_prob,
                weather_code=w_code,
                weather_description=wmo_code_to_description(w_code),
                wind_speed_kmh=round(w_spd, 1)
            ))

        return LiveWeatherMetrics(
            latitude=latitude,
            longitude=longitude,
            temperature_c=round(float(curr_temp), 1),
            apparent_temperature_c=round(float(curr_apparent), 1),
            weather_code=int(curr_weather_code),
            weather_condition_text=weather_desc,
            temp_max_24h_c=round(float(temp_max_24h), 1),
            temp_min_24h_c=round(float(temp_min_24h), 1),
            accumulated_rain_24h_mm=round(float(rain_24h), 1),
            accumulated_rain_72h_mm=round(float(rain_72h), 1),
            forecast_rain_next_24h_mm=round(float(rain_forecast_24h), 1),
            current_rain_rate_mmh=round(float(curr_rain_rate), 2),
            soil_moisture_volumetric_m3_m3=round(float(avg_soil_moisture), 3),
            relative_humidity_pct=round(float(curr_rh), 1),
            wind_speed_10m_kmh=round(float(curr_wind), 1),
            wind_gusts_10m_kmh=round(float(curr_gust), 1),
            wind_direction_10m_deg=round(float(curr_dir), 1),
            wind_cardinal_direction=cardinal_dir,
            hourly_forecast=hourly_items,
            data_source="Open-Meteo API (ECMWF ERA5-Land)",
            is_live_data=True
        )

    def _generate_fallback(self, latitude: float, longitude: float, reason: str) -> LiveWeatherMetrics:
        """Fallback simulation for offline test environments or network interruptions."""
        # Simulated 24 hours of hourly items
        fallback_hourly = []
        for h in range(24):
            hour_str = f"{h:02d}:00"
            fallback_hourly.append(HourlyForecastItem(
                time=hour_str,
                datetime_iso=f"2026-09-11T{hour_str}:00",
                temperature_c=round(21.0 + 3.0 * (1 if 10 <= h <= 17 else -1), 1),
                apparent_temperature_c=round(22.0 + 3.0 * (1 if 10 <= h <= 17 else -1), 1),
                precipitation_mm=round(0.8 if h in [15, 16, 17] else 0.0, 1),
                precipitation_probability_pct=65 if h in [15, 16, 17] else 15,
                weather_code=80 if h in [15, 16, 17] else 1,
                weather_description="Pancadas de Chuva Leves" if h in [15, 16, 17] else "Predomínio de Sol",
                wind_speed_kmh=16.0
            ))

        return LiveWeatherMetrics(
            latitude=latitude,
            longitude=longitude,
            temperature_c=22.0,
            apparent_temperature_c=23.5,
            weather_code=2,
            weather_condition_text="Parcialmente Nublado",
            temp_max_24h_c=27.5,
            temp_min_24h_c=17.0,
            accumulated_rain_24h_mm=35.0,
            accumulated_rain_72h_mm=75.0,
            forecast_rain_next_24h_mm=20.0,
            current_rain_rate_mmh=1.5,
            soil_moisture_volumetric_m3_m3=0.34,
            relative_humidity_pct=85.0,
            wind_speed_10m_kmh=16.0,
            wind_gusts_10m_kmh=32.0,
            wind_direction_10m_deg=140.0,
            wind_cardinal_direction="SE",
            hourly_forecast=fallback_hourly,
            data_source=f"Modo Fallback / Offline ({reason})",
            is_live_data=False
        )
