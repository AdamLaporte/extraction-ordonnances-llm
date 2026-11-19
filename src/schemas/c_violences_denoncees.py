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

    PHYS_DEM_DENONC: Literal["0", "1"]
    MENACE_DEM_DENONC: Literal["0", "1"]
    MENACE_MORT_DEM_DENONC: Literal["0", "1"]
    MENACE_ARME_DEM_DENONC: Literal["0", "1"]
    PSY_DEM_DENONC: Literal["0", "1"]
    PSY_HARCEL_DEM_DENONC: Literal["0", "1"]
    PSY_CONTROL_DEM_DENONC: Literal["0", "1"]
    SEXUEL_DEM_DENONC: Literal["0", "1"]
    ECONOMIC_DEM_DENONC: Literal["0", "1"]
    VOLPAPIER_DEM_DENONC: Literal["0", "1"]
    INTRUSION_DEM_DENONC: Literal["0", "1"]
    DEGRAD_DEM_DENONC: Literal["0", "1"]
    PHYS_ENFT_DENONC: Literal["0", "1"]
    MENACE_ENFT_DENONC: Literal["0", "1"]
    PSY_ENFT_DENONC: Literal["0", "1"]
    SEXUEL_ENFT_DENONC: Literal["0", "1"]
    ENLEVT_ENFT_DENONC: Literal["0", "1"]
    VIOLENCE_DEBUT_DENONC: Literal["1", "2", "3", "X"]
    LIEU_DOM_COMMUN_DENONC: Literal["0", "1"]
    LIEU_DOM_DEM_DENONC: Literal["0", "1"]
    LIEU_DOM_DEF_DENONC: Literal["0", "1"]
    LIEU_W_DEM_DENONC: Literal["0", "1"]
    LIEU_PUBLIC_DENONC: Literal["0", "1"]
    LIEU_TIERS_DENONC: Literal["0", "1"]
    TEMOIN_ENFT_DENONC: Literal["0", "1"]
    TEMOIN_NOUV_CONJ_DENONC: Literal["0", "1"]
    TEMOIN_PROCHE_DENONC: Literal["0", "1"]
    TEMOIN_AUTRE_DENONC: Literal["0", "1"]
    DEBUT_SEPAR_DENONC: Literal["0", "1"]
    DEBUT_GROSSESSE_DENONC: Literal["0", "1"]
    DEBUT_ENFT_DENONC: Literal["0", "1"]
    DEBUT_ADDICT_DENONC: Literal["0", "1"]
    DEBUT_CONFINE_DENONC: Literal["0", "1"]
    PREUV_PLAINTE_AVANT: Literal["0", "1"]
    PREUV_PLAINTE_AVANT_NB: Optional[int] = None
    PREUV_PLAINTE_ACTUEL: Literal["0", "1"]
    PREUV_MAIN_COURANTE: Literal["0", "1"]
    PREUV_CERTIF_IML: Literal["0", "1"]
    PREUV_CERTIF_MED: Literal["0", "1"]
    PREUV_TEMOIN_PROCHE_ASSIST: Literal["0", "1"]
    PREUV_TEMOIN_W_SOCIAL: Literal["0", "1"]
    PREUV_TEMOIN_PROCHE_NON_ASSIST: Literal["0", "1"]
    PREUV_TEMOIN_ENFT: Literal["0", "1"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.MENACE_DEM_DENONC != "1":
            self.MENACE_MORT_DEM_DENONC = None
            self.MENACE_ARME_DEM_DENONC = None
        if self.PSY_DEM_DENONC != "1":
            self.PSY_HARCEL_DEM_DENONC = None
            self.PSY_CONTROL_DEM_DENONC = None
        
        if self.PREUV_PLAINTE_AVANT != "1":
            self.PREUV_PLAINTE_AVANT_NB = None
        return self