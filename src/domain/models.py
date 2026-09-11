"""Domain models, enumerations, and core entities."""

from enum import Enum
from typing import NamedTuple, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Categorical risk classifications for landslide susceptibility."""
    LOW = "BAIXO"
    MEDIUM = "MEDIO"
    HIGH = "ALTO"
    CRITICAL = "CRITICO"


class RainfallAlertLevel(str, Enum):
    """Civil defense precipitation warning stages."""
    NORMAL = "NORMAL"
    ATTENTION = "OBSERVACAO"
    ALERT = "ATENCAO"
    EMERGENCY = "ALERTA_MAXIMO"


class LithologyType(str, Enum):
    """Geological substrate classes."""
    GNEISS_GRANITE = "Gnaisse/Granito"
    SCHIST = "Xisto/Filito"
    SANDSTONE = "Arenito"
    BASALT = "Basalto"
    COLLUVIAL_DEPOSITS = "Depositos Coluvionares"


class LandCoverType(str, Enum):
    """Surface occupation and vegetation cover."""
    DENSE_FOREST = "Floresta Densa / Mata Atlantica"
    SECONDARY_VEGETATION = "Vegetacao Secundaria / Capoeira"
    PASTURE = "Pastagem / Graminea"
    URBAN_OCCUPATION = "Ocupacao Urbana / Encosta Antropizada"
    EXPOSED_SOIL = "Solo Exposto / Corte de Talude"


class FactorOfSafetyResult(NamedTuple):
    """Calculated geotechnical Factor of Safety and failure state."""
    factor_of_safety: float
    is_stable: bool
    risk_level: RiskLevel
    driving_shear_stress_kpa: float
    resisting_shear_strength_kpa: float
