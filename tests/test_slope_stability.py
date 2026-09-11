"""Unit tests for the Infinite Slope Stability geotechnical model."""

import pytest
from src.models.slope_stability import InfiniteSlopeModel
from src.domain.models import RiskLevel


def test_flat_terrain_is_highly_stable():
    engine = InfiniteSlopeModel()
    res = engine.evaluate_stability(slope_angle_deg=0.5, rain_24h_mm=100.0)
    assert res.is_stable is True
    assert res.factor_of_safety > 10.0
    assert res.risk_level == RiskLevel.LOW


def test_steep_slope_with_heavy_rain_fails():
    engine = InfiniteSlopeModel()
    # 48 degree slope with 120mm 24h rain and high 72h rain
    res = engine.evaluate_stability(
        slope_angle_deg=48.0,
        cohesion_kpa=8.0,
        friction_angle_deg=25.0,
        soil_depth_m=3.0,
        rain_24h_mm=110.0,
        rain_72h_mm=160.0
    )
    assert res.is_stable is False
    assert res.factor_of_safety < 1.0
    assert res.risk_level == RiskLevel.CRITICAL


def test_groundwater_saturation_reduces_factor_of_safety():
    engine = InfiniteSlopeModel()
    slope = 32.0

    # Dry condition
    res_dry = engine.evaluate_stability(slope_angle_deg=slope, rain_24h_mm=0.0, rain_72h_mm=0.0)

    # Saturated condition (heavy rainfall)
    res_wet = engine.evaluate_stability(slope_angle_deg=slope, rain_24h_mm=80.0, rain_72h_mm=140.0)

    assert res_wet.factor_of_safety < res_dry.factor_of_safety
    assert res_wet.resisting_shear_strength_kpa < res_dry.resisting_shear_strength_kpa


def test_soil_cohesion_effect():
    engine = InfiniteSlopeModel()
    slope = 30.0

    res_low_c = engine.evaluate_stability(slope_angle_deg=slope, cohesion_kpa=5.0)
    res_high_c = engine.evaluate_stability(slope_angle_deg=slope, cohesion_kpa=25.0)

    assert res_high_c.factor_of_safety > res_low_c.factor_of_safety
