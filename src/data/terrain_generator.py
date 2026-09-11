"""Georeferenced synthetic terrain and slope monitoring dataset generator."""

import numpy as np
from typing import List, Dict, Any
from src.domain.schemas import SlopePointEvaluationRequest
from src.domain.models import LithologyType, LandCoverType
from src.config.settings import settings


class GeotechnicalDataGenerator:
    """
    Generates realistic georeferenced slope monitoring points situated in the
    Brazilian Serra do Mar / Regiao Serrana (geomorphological hotspot for mass movements).
    """

    def __init__(
        self,
        center_lat: float = None,
        center_lon: float = None,
        random_seed: int = 42
    ):
        self.center_lat = center_lat or settings.center_latitude
        self.center_lon = center_lon or settings.center_longitude
        self.rng = np.random.RandomState(random_seed)

    def generate_monitored_points(
        self,
        n_points: int = 45,
        storm_scenario: bool = True
    ) -> List[SlopePointEvaluationRequest]:
        """
        Synthesize monitored slope points with realistic spatial coherence and physical attributes.
        """
        points = []

        # Coordinate dispersion around center (~15 km radius)
        lat_offsets = self.rng.normal(0.0, 0.045, n_points)
        lon_offsets = self.rng.normal(0.0, 0.045, n_points)

        lithologies = list(LithologyType)
        land_covers = list(LandCoverType)

        for i in range(n_points):
            lat = round(float(self.center_lat + lat_offsets[i]), 5)
            lon = round(float(self.center_lon + lon_offsets[i]), 5)

            # Altitude realistic for Brazilian crystalline escarpments (400m to 1400m)
            elevation = round(float(self.rng.uniform(420.0, 1380.0)), 1)

            # Slope distribution (Gamma distribution: high proportion of moderate to steep slopes)
            raw_slope = float(self.rng.gamma(shape=4.5, scale=6.0))
            slope_deg = round(float(np.clip(raw_slope, 4.0, 68.0)), 1)

            aspect_deg = round(float(self.rng.uniform(0.0, 360.0)), 1)

            # Topographic wetness index (higher in valleys and convergent hollows)
            slope_rad = np.radians(max(slope_deg, 1.0))
            twi = round(float(np.clip(np.log(200.0 / np.tan(slope_rad)), 2.0, 14.5)), 2)

            # Rainfall scenario
            if storm_scenario:
                # Critical summer tropical squall event
                rain_24h = round(float(self.rng.uniform(15.0, 125.0)), 1)
                rain_72h = round(float(rain_24h + self.rng.uniform(20.0, 110.0)), 1)
            else:
                rain_24h = round(float(self.rng.uniform(2.0, 30.0)), 1)
                rain_72h = round(float(rain_24h + self.rng.uniform(5.0, 40.0)), 1)

            # Geotechnical parameters
            soil_depth = round(float(self.rng.uniform(1.2, 4.5)), 2)
            cohesion = round(float(self.rng.uniform(8.0, 18.0)), 1)
            friction_angle = round(float(self.rng.uniform(24.0, 34.0)), 1)

            # Use integer indexing to preserve exact Enum types
            litho = lithologies[int(self.rng.randint(0, len(lithologies)))]
            cover = land_covers[int(self.rng.randint(0, len(land_covers)))]

            req = SlopePointEvaluationRequest(
                latitude=lat,
                longitude=lon,
                slope_angle_deg=slope_deg,
                elevation_m=elevation,
                aspect_deg=aspect_deg,
                twi=twi,
                accumulated_rain_24h_mm=rain_24h,
                accumulated_rain_72h_mm=rain_72h,
                lithology=litho,
                land_cover=cover,
                soil_depth_m=soil_depth,
                cohesion_kpa=cohesion,
                friction_angle_deg=friction_angle
            )
            points.append(req)

        return points

    def to_geojson(self, evaluated_responses: List[Any]) -> Dict[str, Any]:
        """Convert evaluated slope point responses into standard GeoJSON FeatureCollection."""
        features = []
        for item in evaluated_responses:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [item.longitude, item.latitude]
                },
                "properties": {
                    "factor_of_safety": item.factor_of_safety,
                    "stability_status": item.stability_status,
                    "risk_level": item.combined_risk_level.value,
                    "ahp_score": item.ahp_susceptibility_score,
                    "failure_probability": item.ml_failure_probability,
                    "rainfall_alert": item.rainfall_alert_level.value,
                    "recommendations": item.recommendations
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }
