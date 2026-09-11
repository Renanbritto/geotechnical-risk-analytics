"""Geospatial morphometry algorithms for digital elevation model (DEM) derivatives."""

import numpy as np
from typing import Tuple, Dict, Any


def compute_slope_and_aspect(
    elevation_grid: np.ndarray,
    cell_size_meters: float = 30.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate slope (degrees) and aspect (degrees azimuth from North) using Horn's algorithm.

    Args:
        elevation_grid: 2D numpy array representing DEM heights in meters.
        cell_size_meters: Spatial resolution (pixel size) in meters.

    Returns:
        Tuple of (slope_deg, aspect_deg) arrays with identical shape.
    """
    if elevation_grid.ndim != 2:
        raise ValueError("elevation_grid must be a 2-dimensional array.")

    # Compute directional gradients via Sobel-type central difference (Horn, 1981)
    dz_dx = np.zeros_like(elevation_grid, dtype=float)
    dz_dy = np.zeros_like(elevation_grid, dtype=float)

    # Internal grid boundaries
    dz_dx[1:-1, 1:-1] = (
        (elevation_grid[:-2, 2:] + 2 * elevation_grid[1:-1, 2:] + elevation_grid[2:, 2:]) -
        (elevation_grid[:-2, :-2] + 2 * elevation_grid[1:-1, :-2] + elevation_grid[2:, :-2])
    ) / (8.0 * cell_size_meters)

    dz_dy[1:-1, 1:-1] = (
        (elevation_grid[2:, :-2] + 2 * elevation_grid[2:, 1:-1] + elevation_grid[2:, 2:]) -
        (elevation_grid[:-2, :-2] + 2 * elevation_grid[:-2, 1:-1] + elevation_grid[:-2, 2:])
    ) / (8.0 * cell_size_meters)

    # Pad edges with adjacent interior values
    dz_dx[0, :] = dz_dx[1, :]
    dz_dx[-1, :] = dz_dx[-2, :]
    dz_dx[:, 0] = dz_dx[:, 1]
    dz_dx[:, -1] = dz_dx[:, -2]

    dz_dy[0, :] = dz_dy[1, :]
    dz_dy[-1, :] = dz_dy[-2, :]
    dz_dy[:, 0] = dz_dy[:, 1]
    dz_dy[:, -1] = dz_dy[:, -2]

    # Slope in radians and degrees
    gradient_magnitude = np.sqrt(dz_dx**2 + dz_dy**2)
    slope_rad = np.arctan(gradient_magnitude)
    slope_deg = np.degrees(slope_rad)

    # Aspect in degrees (0 to 360 clockwise from North)
    aspect_rad = np.arctan2(-dz_dx, dz_dy)
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = (aspect_deg + 360.0) % 360.0

    return slope_deg, aspect_deg


def compute_topographic_wetness_index(
    slope_deg: np.ndarray,
    contributing_area: np.ndarray = None,
    min_slope_rad: float = 0.001
) -> np.ndarray:
    """
    Calculate Topographic Wetness Index (TWI = ln(a / tan(beta))).
    High TWI corresponds to convergent flow zones and saturated drainage hollows.
    """
    slope_rad = np.radians(np.maximum(slope_deg, np.degrees(min_slope_rad)))

    if contributing_area is None:
        # Synthetic contributing area heuristic based on slope inverse
        contributing_area = 100.0 / (np.sin(slope_rad) + 0.1)

    twi = np.log(np.maximum(contributing_area, 1.0) / np.tan(slope_rad))
    # Clip extreme values to realistic physical boundaries [1.0, 20.0]
    return np.clip(twi, 1.0, 20.0)


def calculate_point_morphometry(
    elevation: float,
    slope_deg: float,
    aspect_deg: float,
    accumulated_flow_area: float = 250.0
) -> Dict[str, float]:
    """Compute morphometric metrics for a single coordinate."""
    slope_rad = np.radians(max(slope_deg, 0.05))
    twi = float(np.log(max(accumulated_flow_area, 1.0) / np.tan(slope_rad)))
    twi = max(1.0, min(twi, 20.0))

    # Solar radiation index proxy based on aspect (North-facing vs South-facing slopes in Southern Hemisphere)
    solar_insolation_index = float(np.cos(np.radians(aspect_deg - 0.0)))

    return {
        "elevation_m": elevation,
        "slope_deg": slope_deg,
        "aspect_deg": aspect_deg,
        "twi": twi,
        "solar_insolation_index": solar_insolation_index
    }
