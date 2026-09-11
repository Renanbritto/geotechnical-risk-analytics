"""Unit tests for geospatial morphometric derivatives."""

import pytest
import numpy as np
from src.geo.morphometry import (
    compute_slope_and_aspect,
    compute_topographic_wetness_index,
    calculate_point_morphometry
)


def test_flat_surface_has_zero_slope():
    flat_grid = np.full((10, 10), fill_value=500.0)
    slope, aspect = compute_slope_and_aspect(flat_grid, cell_size_meters=30.0)

    assert np.allclose(slope, 0.0, atol=1e-5)


def test_tilted_plane_slope():
    # Grid with constant gradient in X direction: 30m rise every 30m = 45 degree slope
    x = np.arange(10) * 30.0
    grid = np.tile(x, (10, 1))

    slope, aspect = compute_slope_and_aspect(grid, cell_size_meters=30.0)
    # Check interior cell slopes
    interior_slope = slope[2:8, 2:8]
    assert np.allclose(interior_slope, 45.0, atol=0.1)


def test_point_morphometry_calculation():
    res = calculate_point_morphometry(elevation=850.0, slope_deg=28.0, aspect_deg=180.0)
    assert res["elevation_m"] == 850.0
    assert res["slope_deg"] == 28.0
    assert 1.0 <= res["twi"] <= 20.0
