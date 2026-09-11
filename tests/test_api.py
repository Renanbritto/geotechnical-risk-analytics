"""Integration tests for the FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_ahp_consistency_endpoint(client):
    response = client.get("/api/v1/risk/ahp-consistency")
    assert response.status_code == 200
    data = response.json()
    assert data["is_consistent"] is True
    assert data["consistency_ratio"] < 0.10
    assert "declividade" in data["weights"]


def test_rainfall_thresholds_endpoint(client):
    response = client.get("/api/v1/risk/thresholds")
    assert response.status_code == 200
    data = response.json()
    assert "attention_24h_mm" in data
    assert "alert_72h_mm" in data


def test_evaluate_point_endpoint(client):
    payload = {
        "latitude": -22.4250,
        "longitude": -42.9720,
        "slope_angle_deg": 38.0,
        "elevation_m": 820.0,
        "aspect_deg": 140.0,
        "twi": 7.2,
        "accumulated_rain_24h_mm": 65.0,
        "accumulated_rain_72h_mm": 115.0,
        "lithology": "Depositos Coluvionares",
        "land_cover": "Ocupacao Urbana / Encosta Antropizada",
        "soil_depth_m": 2.8,
        "cohesion_kpa": 10.0,
        "friction_angle_deg": 26.0
    }
    response = client.post("/api/v1/risk/evaluate-point", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "factor_of_safety" in data
    assert "combined_risk_level" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0


def test_spatial_geojson_endpoint(client):
    response = client.get("/api/v1/spatial/geojson?n_points=10")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 10
    first_feat = data["features"][0]
    assert first_feat["geometry"]["type"] == "Point"
    assert "factor_of_safety" in first_feat["properties"]


def test_batch_assessment_endpoint(client):
    point = {
        "latitude": -22.41,
        "longitude": -42.98,
        "slope_angle_deg": 25.0,
        "accumulated_rain_24h_mm": 30.0,
        "accumulated_rain_72h_mm": 50.0
    }
    response = client.post("/api/v1/risk/batch-assessment", json={"points": [point, point]})
    assert response.status_code == 200
    data = response.json()
    assert data["total_evaluated"] == 2
    assert "average_factor_of_safety" in data
