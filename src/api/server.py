"""FastAPI application factory and middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.config.settings import settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    app = FastAPI(
        title="Alerta Chuva - Monitoramento Climatico em Tempo Real",
        version=settings.app_version,
        description=(
            "Alerta Chuva - Plataforma de monitoramento climatico e meteorologico em tempo real. "
            "Previsao do tempo, chuva, ventos e dinamica atmosferica."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Cross-Origin Resource Sharing (CORS) configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
