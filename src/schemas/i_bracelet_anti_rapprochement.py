# Fichier : schemas/a_procedure.py
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from typing import Optional, Literal
from datetime import datetime, date


class Schema(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=False,   # désactive les “any object”
        extra="forbid",
        serialization_exclude_none=True,
    )

    NO_CMPST: str

    RAISONNEMENT_GLOBAL: Optional[str] = Field(
        default=None,
        description="Explique brièvement ton raisonnement pour les variables complexes ou les montants (ex: 'Le texte indique 150€ par enfant, il y a 2 enfants, la consigne demande le montant par enfant, donc 150'). S'il n'y a pas de complexité, écris 'Rien à signaler'."
    )

    BAR_DEM: Literal["0", "1", "X"]
    BAR_POS: Literal["0", "1", "X"]
    BAR_DEF: Literal["0", "1", "X"]
    BAR_PARQUET: Literal["0", "1", "2", "X"]
    BAR_PARQUET_REFUS: Literal["1", "2", "3", "4", "9", "X"]
    BAR_JAF: Literal["0", "1", "X"]
    BAR_JAF_REFUS: Literal["1", "2", "3", "4", "9", "X"]
    BAR_DUREE: Optional[float] = None
    BAR_DISTANCE: Optional[float] = None

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.BAR_DEM != "1":
            self.BAR_POS = None
        if self.BAR_DEM != "1" and self.BAR_DEF != "1":
            self.BAR_PARQUET = None
            self.BAR_JAF = None
        if self.BAR_PARQUET != "0":
            self.BAR_PARQUET_REFUS = None
        if self.BAR_JAF != "0":
            self.BAR_JAF_REFUS = None
        if self.BAR_JAF != "1":
            self.BAR_DUREE = None
            self.BAR_DISTANCE = None
        return self
