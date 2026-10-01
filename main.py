"""Command-Line Interface (CLI) and entry point for Alerta Zona da Mata."""

import argparse
import uvicorn
from src.services.weather_service import WeatherService


def evaluate_live(lat: float, lon: float):
    """Query live weather API and print results in real time."""
    print("================================================================================")
    print(" MONITORAMENTO CLIMATICO EM TEMPO REAL (INTEGRACAO METEOROLOGICA AO VIVO)")
    print("================================================================================")
    print(f"Consultando coordenadas: Latitude {lat:.5f}, Longitude {lon:.5f}...")

    weather_svc = WeatherService()
    weather = weather_svc.fetch_live_weather(lat, lon)
    
    print(f"[OK] Dados meteorologicos obtidos via: {weather.data_source}")
    print(f"     Temperatura:         {weather.temperature_c:.1f} oC | Sensacao: {weather.apparent_temperature_c:.1f} oC")
    print(f"     Chuva Observada 24h: {weather.accumulated_rain_24h_mm:.1f} mm")
    print(f"     Chuva Prevista 24h:  {weather.forecast_rain_next_24h_mm:.1f} mm")
    print(f"     Vento:               {weather.wind_speed_10m_kmh:.1f} km/h | Rajadas: {weather.wind_gusts_10m_kmh:.1f} km/h")
    print("================================================================================")


def serve_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start uvicorn server for the FastAPI application."""
    print(f"Iniciando API Monitoramento Climatico em http://{host}:{port}")
    print(f"Documentacao interativa OpenAPI disponivel em http://{host}:{port}/docs")
    uvicorn.run("src.api.server:app", host=host, port=port, reload=reload)


def main():
    parser = argparse.ArgumentParser(
        description="Alerta Zona da Mata - Motor de Monitoramento Climatico"
    )
    parser.add_argument("--eval-live", action="store_true", help="Avaliar clima em tempo real consultando API meteorologica")
    parser.add_argument("--lat", type=float, default=-21.7642, help="Latitude para avaliacao em tempo real (Padrao: Juiz de Fora)")
    parser.add_argument("--lon", type=float, default=-43.3496, help="Longitude para avaliacao em tempo real")
    parser.add_argument("--serve-api", action="store_true", help="Iniciar servidor FastAPI")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host para a API REST")
    parser.add_argument("--port", type=int, default=8000, help="Porta para a API REST")
    parser.add_argument("--reload", action="store_true", help="Modo reload para desenvolvimento da API")

    args = parser.parse_args()

    if args.eval_live:
        evaluate_live(lat=args.lat, lon=args.lon)
    elif args.serve_api:
        serve_api(host=args.host, port=args.port, reload=args.reload)
    else:
        serve_api(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
