"""Predictive Machine Learning classifier and multi-criteria risk integrator."""

import numpy as np
from typing import List, Tuple
from sklearn.ensemble import RandomForestClassifier
from src.domain.models import RiskLevel, RainfallAlertLevel, LithologyType, LandCoverType
from src.domain.schemas import SlopePointEvaluationRequest, SlopePointEvaluationResponse
from src.models.slope_stability import InfiniteSlopeModel
from src.models.ahp import LandslideAHPModel
from src.config.settings import settings


class GeotechnicalRiskClassifier:
    """
    Hybrid geotechnical risk evaluation system marrying deterministic physical models
    (Infinite Slope FS) with multi-criteria AHP and ensemble supervised classification.
    """

    def __init__(self):
        self.slope_engine = InfiniteSlopeModel()
        self.ahp_engine = LandslideAHPModel()
        self.ml_model = self._train_baseline_model()

    def _train_baseline_model(self) -> RandomForestClassifier:
        """
        Train a calibrated Random Forest on a synthetic calibration set
        mapping (Slope, Rainfall, TWI, Lithology, Cover, FS) -> Failure State.
        """
        np.random.seed(settings.random_seed)
        n_samples = 300

        # Generate synthetic feature distribution
        slopes = np.random.uniform(2.0, 55.0, n_samples)
        rain_72h = np.random.uniform(5.0, 220.0, n_samples)
        twis = np.random.uniform(2.0, 14.0, n_samples)
        litho_enc = np.random.randint(0, 5, n_samples)
        cover_enc = np.random.randint(0, 5, n_samples)

        # Approximate physical FS for training features
        fs_values = []
        for s, r, t in zip(slopes, rain_72h, twis):
            res = self.slope_engine.evaluate_stability(
                slope_angle_deg=s,
                rain_72h_mm=r,
                rain_24h_mm=r * 0.45,
                twi=t
            )
            fs_values.append(res.factor_of_safety)

        fs_array = np.array(fs_values)

        # Synthetic ground truth label (1 = Landslide Occurrence / 0 = Stable)
        logits = (
            (1.4 - fs_array) * 3.2 +
            (slopes / 35.0) * 1.8 +
            (rain_72h / 120.0) * 2.1 +
            (twis / 10.0) * 0.9 - 2.5
        )
        probabilities = 1.0 / (1.0 + np.exp(-logits))
        labels = (probabilities > 0.48).astype(int)

        X = np.column_stack([slopes, rain_72h, twis, litho_enc, cover_enc, fs_array])
        clf = RandomForestClassifier(
            n_estimators=20,
            max_depth=5,
            n_jobs=1,
            random_state=settings.random_seed
        )
        clf.fit(X, labels)
        return clf

    @staticmethod
    def _encode_lithology(lithology: LithologyType) -> int:
        mapping = {
            LithologyType.BASALT: 0,
            LithologyType.GNEISS_GRANITE: 1,
            LithologyType.SANDSTONE: 2,
            LithologyType.SCHIST: 3,
            LithologyType.COLLUVIAL_DEPOSITS: 4
        }
        return mapping.get(lithology, 2)

    @staticmethod
    def _encode_land_cover(land_cover: LandCoverType) -> int:
        mapping = {
            LandCoverType.DENSE_FOREST: 0,
            LandCoverType.SECONDARY_VEGETATION: 1,
            LandCoverType.PASTURE: 2,
            LandCoverType.URBAN_OCCUPATION: 3,
            LandCoverType.EXPOSED_SOIL: 4
        }
        return mapping.get(land_cover, 2)

    def evaluate_rainfall_alert(self, rain_24h_mm: float, rain_72h_mm: float) -> RainfallAlertLevel:
        """Categorize hydrological warning based on CEMADEN guidelines."""
        cfg = settings.rainfall_thresholds
        if rain_72h_mm >= cfg.emergency_96h_mm or rain_24h_mm >= 100.0:
            return RainfallAlertLevel.EMERGENCY
        elif rain_72h_mm >= cfg.alert_72h_mm or rain_24h_mm >= 65.0:
            return RainfallAlertLevel.ALERT
        elif rain_24h_mm >= cfg.attention_24h_mm:
            return RainfallAlertLevel.ATTENTION
        else:
            return RainfallAlertLevel.NORMAL

    def generate_recommendations(
        self,
        risk_level: RiskLevel,
        alert_level: RainfallAlertLevel,
        slope_deg: float
    ) -> List[str]:
        """Produce actionable civil defense and geotechnical engineering recommendations."""
        recs = []

        if risk_level == RiskLevel.CRITICAL:
            recs.append("Evacuacao preventiva imediata de residencias e estruturas no setor de encosta.")
            recs.append("Acionamento imediato do plano de contingencia da Defesa Civil Municipal.")
            recs.append("Interdicao de vias de acesso situadas a jusante do talude sob risco de ruptura.")
        elif risk_level == RiskLevel.HIGH:
            recs.append("Vistoria de campo urgente para identificar trincas no solo, inclinacao de arvores ou postes.")
            recs.append("Monitoramento pluviometrico continuo com checagem horaria de indices acumulados.")
            recs.append("Cobertura emergencial de taludes expostos com lonas plasticas impermeaveis.")
        elif risk_level == RiskLevel.MEDIUM:
            recs.append("Manutencao preventiva e desobstrucao de canaletas, valetas e sistemas de drenagem pluvial.")
            recs.append("Instalacao de reguas de controle topografico e marcos de monitoramento superficial.")
            recs.append("Orientacao a comunidade local sobre sinais preliminares de instabilidade de encostas.")
        else:
            recs.append("Condicoes de estabilidade compativeis com os padroes normativos NBR 11682.")
            recs.append("Manutencao da cobertura vegetal nativa para prevencao de processos erosivos laminares.")

        if alert_level in (RainfallAlertLevel.ALERT, RainfallAlertLevel.EMERGENCY):
            recs.append(f"Alerta Pluviometrico Ativo ({alert_level.value}): Manter equipes tecnicas em prontidao 24h.")

        return recs

    def evaluate_point(self, request: SlopePointEvaluationRequest) -> SlopePointEvaluationResponse:
        """Run complete geotechnical, AHP and ML inference pipeline for a given point."""
        # 1. Deterministic Infinite Slope Model
        stability_res = self.slope_engine.evaluate_stability(
            slope_angle_deg=request.slope_angle_deg,
            cohesion_kpa=request.cohesion_kpa if request.cohesion_kpa is not None else 12.0,
            friction_angle_deg=request.friction_angle_deg if request.friction_angle_deg is not None else 28.0,
            soil_depth_m=request.soil_depth_m,
            rain_24h_mm=request.accumulated_rain_24h_mm,
            rain_72h_mm=request.accumulated_rain_72h_mm,
            twi=request.twi or 6.5
        )

        # 2. Multi-Criteria AHP Susceptibility
        ahp_score = self.ahp_engine.calculate_susceptibility(
            slope_deg=request.slope_angle_deg,
            rain_72h_mm=request.accumulated_rain_72h_mm,
            lithology=request.lithology,
            land_cover=request.land_cover
        )

        # 3. Machine Learning Inference
        feat_vector = np.array([[
            request.slope_angle_deg,
            request.accumulated_rain_72h_mm,
            request.twi or 6.5,
            self._encode_lithology(request.lithology),
            self._encode_land_cover(request.land_cover),
            stability_res.factor_of_safety
        ]])

        ml_prob = float(self.ml_model.predict_proba(feat_vector)[0, 1])
        ml_prob = round(ml_prob, 4)

        # 4. Combined Risk Level Harmonization
        if stability_res.factor_of_safety < 1.0 or ml_prob >= 0.75 or ahp_score >= 0.82:
            combined_risk = RiskLevel.CRITICAL
        elif stability_res.factor_of_safety < 1.25 or ml_prob >= 0.50 or ahp_score >= 0.65:
            combined_risk = RiskLevel.HIGH
        elif stability_res.factor_of_safety < 1.55 or ml_prob >= 0.25 or ahp_score >= 0.40:
            combined_risk = RiskLevel.MEDIUM
        else:
            combined_risk = RiskLevel.LOW

        rainfall_alert = self.evaluate_rainfall_alert(
            request.accumulated_rain_24h_mm,
            request.accumulated_rain_72h_mm
        )

        recommendations = self.generate_recommendations(
            combined_risk,
            rainfall_alert,
            request.slope_angle_deg
        )

        stability_str = "Estavel" if stability_res.is_stable else "Instavel (Ruptura Eminente)"

        return SlopePointEvaluationResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            factor_of_safety=stability_res.factor_of_safety,
            stability_status=stability_str,
            geotechnical_risk_level=stability_res.risk_level,
            ahp_susceptibility_score=ahp_score,
            ml_failure_probability=ml_prob,
            combined_risk_level=combined_risk,
            rainfall_alert_level=rainfall_alert,
            recommendations=recommendations
        )
