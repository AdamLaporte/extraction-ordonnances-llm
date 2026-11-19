# Fichier : schemas/a_procedure.py
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime, date


class Schema(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=False,   # désactive les “any object”
        extra="forbid",
        serialization_exclude_none=True,
    )

    NO_CMPST: str

    REP_VIOLENCE: Literal["0", "1"]
    PHYS_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    MENACE_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    MENACE_MORT_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    MENACE_ARME_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    PSY_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    PSY_HARCEL_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    PSY_CONTROL_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    SEXUEL_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    ECONOMIC_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    VOLPAPIER_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    INTRUSION_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    DEGRAD_DEM_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    PHYS_ENFT_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    MENACE_ENFT_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    PSY_ENFT_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    SEXUEL_ENFT_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    ENLEVT_ENFT_REPDEF: Literal["1", "2", "3", "5", "6", "X"]
    TEMOIN_ENFT_REPDEF: Literal["0", "1", "X"]
    TEMOIN_NOUV_CONJ_REPDEF: Literal["0", "1", "X"]
    TEMOIN_PROCHE_REPDEF: Literal["0", "1", "X"]
    TEMOIN_AUTRE_REPDEF: Literal["0", "1", "X"]
    TENSION_OK_DEF: Literal["0", "1"]
    ILLEGAL_OK_DEF: Literal["0", "1"]
    MINIM_JUSTIF_DEF: Literal["0", "1"]
    DIVORCE_OK_DEF: Literal["0", "1"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        
        if self.REP_VIOLENCE != "1":
            self.TENSION_OK_DEF = None
            self.ILLEGAL_OK_DEF = None
            self.MINIM_JUSTIF_DEF = None
            self.DIVORCE_OK_DEF = None
        return self