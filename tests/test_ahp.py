"""Unit tests for the Saaty Analytic Hierarchy Process (AHP) model."""

import pytest
import numpy as np
from src.models.ahp import LandslideAHPModel
from src.domain.models import LithologyType, LandCoverType


def test_ahp_matrix_consistency_ratio():
    model = LandslideAHPModel()
    report = model.get_consistency_report()

    # Saaty criterion: CR must be under 0.10 for acceptable consistency
    assert report.is_consistent is True
    assert report.consistency_ratio < 0.10
    assert report.consistency_ratio >= 0.0


def test_ahp_weights_sum_to_one():
    model = LandslideAHPModel()
    report = model.get_consistency_report()

    total_weight = sum(report.weights.values())
    assert abs(total_weight - 1.0) < 0.005


def test_ahp_susceptibility_scoring_bounds():
    model = LandslideAHPModel()

    # Low risk parameters: flat, no rain, basalt, dense forest
    score_low = model.calculate_susceptibility(
        slope_deg=5.0,
        rain_72h_mm=10.0,
        lithology=LithologyType.BASALT,
        land_cover=LandCoverType.DENSE_FOREST
    )

    # High risk parameters: steep, torrential rain, colluvial deposits, exposed soil
    score_high = model.calculate_susceptibility(
        slope_deg=45.0,
        rain_72h_mm=160.0,
        lithology=LithologyType.COLLUVIAL_DEPOSITS,
        land_cover=LandCoverType.EXPOSED_SOIL
    )

    assert 0.0 <= score_low <= 1.0
    assert 0.0 <= score_high <= 1.0
    assert score_high > score_low
    assert score_high >= 0.80
