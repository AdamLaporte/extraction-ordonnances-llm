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

    PHYS_DEM_RETENU: Literal["0", "1"]
    MENACE_DEM_RETENU: Literal["0", "1"]
    MENACE_MORT_DEM_RETENU: Literal["0", "1"]
    MENACE_ARME_DEM_RETENU: Literal["0", "1"]
    PSY_DEM_RETENU: Literal["0", "1"]
    PSY_HARCEL_DEM_RETENU: Literal["0", "1"]
    PSY_CONTROL_DEM_RETENU: Literal["0", "1"]
    SEXUEL_DEM_RETENU: Literal["0", "1"]
    ECONOMIC_DEM_RETENU: Literal["0", "1"]
    VOLPAPIER_DEM_RETENU: Literal["0", "1"]
    INTRUSION_DEM_RETENU: Literal["0", "1"]
    DEGRAD_DEM_RETENU: Literal["0", "1"]
    PHYS_ENFT_RETENU: Literal["0", "1"]
    MENACE_ENFT_RETENU: Literal["0", "1"]
    PSY_ENFT_RETENU: Literal["0", "1"]
    SEXUEL_ENFT_RETENU: Literal["0", "1"]
    ENLEVT_ENFT_RETENU: Literal["0", "1"]
    TENSION_RETENU: Literal["0", "1"]
    VIOLENCE_RECIPROC_RETENU: Literal["0", "1"]
    DANGER_RETENU: Literal["0", "1"]
    VIOLENT_DEF_RETENU: Literal["0", "1"]
    VIOLENCE_REPETE_RETENU: Literal["0", "1"]
    SEPAR_CONFLIT_RETENU: Literal["0", "1"]
    VIOLENCE_FIN_SEPARE_RETENU: Literal["0", "1"]
    VIOLENCE_ANCIEN_RETENU: Literal["0", "1"]
    MENSONGE_DEM_RETENU: Literal["0", "1"]
    NERVEUX_DEM_RETENU: Literal["0", "1"]
    REPONSE_EVASIVE_DEM_RETENU: Literal["0", "1"]
    PAS_DIVORCE_DEM_RETENU: Literal["0", "1"]
    MENSONGE_DEF_RETENU: Literal["0", "1"]
    NERVEUX_DEF_RETENU: Literal["0", "1"]
    REPONSE_EVASIVE_DEF_RETENU: Literal["0", "1"]
    PB_PARENT_DEF_RETENU: Literal["0", "1"]
    PB_PSY_DEF_RETENU: Literal["0", "1"]
    PRISON_DEF: Literal["0", "1"]
    HOPITAL_DEF: Literal["0", "1"]
    PASSE_VCONJ_CONDA: Literal["0", "1"]
    PASSE_VCONJ_CONDA_NB: Optional[int] = None
    PASSE_VCONJ_PRISON: Literal["0", "1"]
    PASSE_VCONJ_MAP: Literal["0", "1"]
    PASSE_VENFT_CONDA_MAP: Literal["0", "1"]
    PROCES_ENCOURS: Literal["0", "1"]
    PROCES_ENCOURS_LIEN_OP: Literal["0", "1"]
    PROCES_ENCOURS_PREVENTIVE: Literal["0", "1"]
    PRISON_ENCOURS_AUTRE: Literal["0", "1"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        
        if self.PASSE_VCONJ_CONDA != "1":
            self.PASSE_VCONJ_CONDA_NB = None
            self.PASSE_VCONJ_PRISON = None
        if self.PROCES_ENCOURS != "1":
            self.PROCES_ENCOURS_LIEN_OP = None
            self.PROCES_ENCOURS_PREVENTIVE = None
        return self