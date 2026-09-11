"""Analytic Hierarchy Process (AHP - Saaty) for multi-criteria landslide susceptibility."""

import numpy as np
from typing import Dict, List, Tuple
from src.domain.schemas import AHPConsistencyResponse
from src.domain.models import LithologyType, LandCoverType


class LandslideAHPModel:
    """
    Multi-criteria decision analysis engine based on Thomas Saaty's Analytic Hierarchy Process.
    Evaluates: Slope, Rainfall Trigger, Geological Substrate (Lithology), and Land Cover.
    """

    # Random Index (RI) table for matrices of size n = 1 to 9 (Saaty, 1980)
    RANDOM_INDEX = {
        1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
        6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45
    }

    CRITERIA_NAMES = ["declividade", "pluviometria", "litologia", "uso_do_solo"]

    def __init__(self, pairwise_matrix: np.ndarray = None):
        """
        Default pairwise comparison matrix (4x4):
        Order: [Declividade, Pluviometria, Litologia, Uso do Solo]

        Relative Importance Rationale:
        - Slope is the fundamental gravitational driver.
        - Rainfall is the dynamic triggering event.
        - Lithology dictates shearing plane weakness.
        - Land cover influences infiltration and surface anchorage.
        """
        if pairwise_matrix is None:
            # 4x4 matrix with established geotechnical consistency
            self.matrix = np.array([
                [1.0,  2.0,  3.0,  4.0],  # Declividade
                [0.5,  1.0,  2.0,  3.0],  # Pluviometria
                [0.33, 0.5,  1.0,  2.0],  # Litologia
                [0.25, 0.33, 0.5,  1.0]   # Uso do Solo
            ], dtype=float)
        else:
            self.matrix = np.array(pairwise_matrix, dtype=float)

        self.weights, self.cr, self.ci, self.lambda_max = self._compute_weights_and_consistency()

    def _compute_weights_and_consistency(self) -> Tuple[Dict[str, float], float, float, float]:
        n = self.matrix.shape[0]

        # Calculate principal eigenvector via geometric mean approximation and power iteration
        col_sums = self.matrix.sum(axis=0)
        normalized_matrix = self.matrix / col_sums
        weights_array = normalized_matrix.mean(axis=1)

        # Principal eigenvalue (lambda_max)
        weighted_sum = self.matrix.dot(weights_array)
        lambda_max = float(np.mean(weighted_sum / weights_array))

        # Consistency Index (CI)
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0

        # Consistency Ratio (CR)
        ri = self.RANDOM_INDEX.get(n, 1.45)
        cr = float(ci / ri) if ri > 0 else 0.0

        weights_dict = {
            self.CRITERIA_NAMES[i]: round(float(weights_array[i]), 4)
            for i in range(n)
        }

        return weights_dict, round(cr, 4), round(ci, 4), round(lambda_max, 4)

    def get_consistency_report(self) -> AHPConsistencyResponse:
        """Return structured verification of the AHP matrix consistency."""
        is_consistent = self.cr < 0.10
        explanation = (
            f"Matriz consistente (CR = {self.cr:.4f} < 0.10). Os julgamentos paritarios respeitam "
            "as propriedades de transitividade e coerencia matematica exigidas por Saaty."
            if is_consistent else
            f"Matriz inconsistente (CR = {self.cr:.4f} >= 0.10). Recomenda-se revisar as ponderacoes."
        )

        return AHPConsistencyResponse(
            criteria=self.CRITERIA_NAMES,
            weights=self.weights,
            principal_eigenvalue=self.lambda_max,
            consistency_index=self.ci,
            consistency_ratio=self.cr,
            is_consistent=is_consistent,
            explanation=explanation
        )

    @staticmethod
    def rate_slope(slope_deg: float) -> float:
        """Normalize slope rating to [0, 1] according to geotechnical hazard classes."""
        if slope_deg < 10.0:
            return 0.15  # Planicie / Risco quase nulo
        elif slope_deg < 20.0:
            return 0.35  # Ondulado moderado
        elif slope_deg < 30.0:
            return 0.65  # Forte ondulado / Inicio da instabilidade crítica
        elif slope_deg < 45.0:
            return 0.90  # Escarpa / Talude íngreme
        else:
            return 1.00  # Paredão rochoso vertical

    @staticmethod
    def rate_rainfall(rain_72h_mm: float) -> float:
        """Normalize rainfall rating based on CEMADEN threshold scales."""
        if rain_72h_mm < 30.0:
            return 0.10
        elif rain_72h_mm < 60.0:
            return 0.35
        elif rain_72h_mm < 100.0:
            return 0.65
        elif rain_72h_mm < 150.0:
            return 0.85
        else:
            return 1.00

    @staticmethod
    def rate_lithology(lithology: LithologyType) -> float:
        """Geological substrate susceptibility score."""
        scores = {
            LithologyType.BASALT: 0.20,
            LithologyType.GNEISS_GRANITE: 0.40,
            LithologyType.SANDSTONE: 0.60,
            LithologyType.SCHIST: 0.80,
            LithologyType.COLLUVIAL_DEPOSITS: 0.95
        }
        return scores.get(lithology, 0.50)

    @staticmethod
    def rate_land_cover(land_cover: LandCoverType) -> float:
        """Surface anchorage and anthropological disturbance score."""
        scores = {
            LandCoverType.DENSE_FOREST: 0.15,
            LandCoverType.SECONDARY_VEGETATION: 0.35,
            LandCoverType.PASTURE: 0.60,
            LandCoverType.URBAN_OCCUPATION: 0.85,
            LandCoverType.EXPOSED_SOIL: 0.98
        }
        return scores.get(land_cover, 0.50)

    def calculate_susceptibility(
        self,
        slope_deg: float,
        rain_72h_mm: float,
        lithology: LithologyType,
        land_cover: LandCoverType
    ) -> float:
        """
        Compute weighted composite susceptibility index S in range [0.0, 1.0].
        """
        r_slope = self.rate_slope(slope_deg)
        r_rain = self.rate_rainfall(rain_72h_mm)
        r_litho = self.rate_lithology(lithology)
        r_cover = self.rate_land_cover(land_cover)

        score = (
            (self.weights["declividade"] * r_slope) +
            (self.weights["pluviometria"] * r_rain) +
            (self.weights["litologia"] * r_litho) +
            (self.weights["uso_do_solo"] * r_cover)
        )

        return round(float(np.clip(score, 0.0, 1.0)), 4)
