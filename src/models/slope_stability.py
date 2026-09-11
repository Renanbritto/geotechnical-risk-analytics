"""Geotechnical slope stability engine based on the Infinite Slope Model."""

import math
from typing import Optional
from src.domain.models import FactorOfSafetyResult, RiskLevel
from src.config.settings import settings


class InfiniteSlopeModel:
    """
    Infinite Slope Stability Model for planar translational landslides in colluvial/residual soils.

    Formulation:
    FS = [c' + (gamma_sat * z - gamma_w * h_w) * cos^2(beta) * tan(phi')] /
         [gamma_sat * z * sin(beta) * cos(beta)]
    """

    def __init__(
        self,
        default_gamma_sat: float = 18.5,
        default_gamma_w: float = 9.81,
        default_soil_depth: float = 2.5
    ):
        self.gamma_sat = default_gamma_sat
        self.gamma_w = default_gamma_w
        self.default_z = default_soil_depth

    def estimate_water_table_height(
        self,
        soil_depth_z: float,
        rain_24h_mm: float,
        rain_72h_mm: float,
        twi: float = 6.0
    ) -> float:
        """
        Estimate transient groundwater table height (h_w) above slip plane based on rainfall and TWI.
        """
        # Weighted effective hydrological antecedent moisture
        effective_rain = (0.6 * rain_24h_mm) + (0.4 * (rain_72h_mm - rain_24h_mm))

        # Saturation ratio driven by rainfall depth and topographic convergence
        twi_factor = max(0.8, min(twi / 6.0, 2.0))
        saturation_ratio = (effective_rain / 120.0) * twi_factor
        saturation_ratio = max(0.0, min(saturation_ratio, 1.0))

        # Height of water table above basal failure plane
        return soil_depth_z * saturation_ratio

    def evaluate_stability(
        self,
        slope_angle_deg: float,
        cohesion_kpa: float = 12.0,
        friction_angle_deg: float = 28.0,
        soil_depth_m: Optional[float] = None,
        rain_24h_mm: float = 0.0,
        rain_72h_mm: float = 0.0,
        twi: float = 6.0
    ) -> FactorOfSafetyResult:
        """
        Compute the Factor of Safety (FS) for a specific slope profile under hydrometeorological stress.
        """
        z = soil_depth_m if soil_depth_m is not None and soil_depth_m > 0 else self.default_z

        # Handle flat or quasi-horizontal terrain (no shear driving force)
        if slope_angle_deg < 1.0:
            return FactorOfSafetyResult(
                factor_of_safety=99.9,
                is_stable=True,
                risk_level=RiskLevel.LOW,
                driving_shear_stress_kpa=0.01,
                resisting_shear_strength_kpa=cohesion_kpa + 50.0
            )

        beta_rad = math.radians(slope_angle_deg)
        phi_rad = math.radians(friction_angle_deg)

        # Estimate transient perched water table height
        h_w = self.estimate_water_table_height(z, rain_24h_mm, rain_72h_mm, twi)

        # Driving shear stress (tau_d = gamma_sat * z * sin(beta) * cos(beta))
        tau_driving = self.gamma_sat * z * math.sin(beta_rad) * math.cos(beta_rad)

        # Effective normal stress on failure plane (sigma'_n = (gamma_sat * z - gamma_w * h_w) * cos^2(beta))
        sigma_effective = (self.gamma_sat * z - self.gamma_w * h_w) * (math.cos(beta_rad) ** 2)
        sigma_effective = max(0.0, sigma_effective)

        # Resisting shear strength via Mohr-Coulomb criterion (tau_r = c' + sigma'_n * tan(phi'))
        tau_resisting = cohesion_kpa + (sigma_effective * math.tan(phi_rad))

        # Factor of Safety calculation
        fs = tau_resisting / max(tau_driving, 1e-6)
        fs = round(float(fs), 3)

        # Categorical risk classification based on geotechnical standards
        if fs >= 1.5:
            risk_level = RiskLevel.LOW
        elif 1.2 <= fs < 1.5:
            risk_level = RiskLevel.MEDIUM
        elif 1.0 <= fs < 1.2:
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.CRITICAL

        return FactorOfSafetyResult(
            factor_of_safety=fs,
            is_stable=(fs >= 1.0),
            risk_level=risk_level,
            driving_shear_stress_kpa=round(float(tau_driving), 2),
            resisting_shear_strength_kpa=round(float(tau_resisting), 2)
        )
