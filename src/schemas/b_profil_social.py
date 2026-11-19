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

    SEXE_DEM: Literal["1", "2", "X"]
    DA_NAIS_DEM: Optional[date] = None
    PAYS_NAIS_DEM: Optional[str] = None
    CITATION_NATIONALITE: str = Field(
        description="Self-Verification: Extrais la citation EXACTE du texte qui mentionne la nationalité. Si aucune mention explicite n'existe, écris 'Aucune mention'."
    )
    NATIO_DEM: Literal["1", "2", "3", "X"] = Field(
        description="Si CITATION_NATIONALITE est 'Aucune mention', tu DOIS OBLIGATOIREMENT choisir 'X'."
    )
    DEPT_RES_DEM: Optional[str] = None
    STATUT_PRO_DEM: Literal["1", "2", "3", "4", "9", "X"]
    REVENU_DEM: Optional[float] = None
    LOGT_TYPE_DEM: Literal["1", "2", "3", "4", "9", "X"]
    SEXE_DEF: Literal["1", "2", "X"]
    DA_NAIS_DEF: Optional[date] = None
    PAYS_NAIS_DEF: Optional[str] = None
    VILLE_NAIS_DEF: Optional[str] = None
    VILLE_NAIS_ETR_DEF: Optional[str] = None
    NATIO_DEF: Literal["1", "2", "3", "X"]
    DEPT_RES_DEF: Optional[str] = None
    STATUT_PRO_DEF: Literal["1", "2", "3", "4", "9", "X"]
    REVENU_DEF: Optional[float] = None
    LOGT_TYPE_DEF: Literal["1", "2", "3", "4", "9", "X"]
    STATUT_JUR_COUPLE: Literal["11", "12", "13", "21", "22", "23", "31", "99", "XX"]
    AN_MARIAGE_COUPLE: Optional[int] = None
    AN_PACS_COUPLE: Optional[int] = None
    DIVORCE_ENCOURS_COUPLE: Literal["0", "1"]
    ENFT: Literal["0", "1", "X"]
    ENFT_NB: Optional[int] = None
    ENFT_MIN: Literal["0", "1", "X"]
    ENFT_MIN_NB: Optional[int] = None
    ENFT_MAJ: Literal["0", "1", "X"]
    ENFT_MAJ_NB: Optional[int] = None
    ENFT_MINI_AN_NAIS: Optional[int] = None
    ENFT_MAXI_AN_NAIS: Optional[int] = None
    ENFT_GROSSESSE: Literal["0", "1"]
    ENFT_HORS_UNION_DEM: Literal["0", "1"]
    ENFT_MESURE_SOCIOEDUC: Literal["0", "1"]
    ENFT_PROC_JAF: Literal["0", "1"]
    ADDICT_STUP_DEM: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    ADDICT_ALCOOL_DEM: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    PATHO_PSY_DEM: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    DEPRESSION_DEM: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    ADDICT_STUP_DEF: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    ADDICT_ALCOOL_DEF: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    PATHO_PSY_DEF: Literal["0", "1", "2", "3", "4", "5", "6", "7"]
    DEPRESSION_DEF: Literal["0", "1", "2", "3", "4", "5", "6", "7"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.PAYS_NAIS_DEF != "250":
            self.VILLE_NAIS_DEF = None
        if self.PAYS_NAIS_DEF == "250":
            self.VILLE_NAIS_ETR_DEF = None
        if self.STATUT_JUR_COUPLE not in ("11", "21"):
            self.AN_MARIAGE_COUPLE = None
        if self.STATUT_JUR_COUPLE not in ("12", "22"):
            self.AN_PACS_COUPLE = None
        if self.STATUT_JUR_COUPLE not in ("11", "12"):
            self.DIVORCE_ENCOURS_COUPLE = None
        if self.ENFT != "1":
            self.ENFT_NB = None
            self.ENFT_MIN = None
            self.ENFT_MAJ = None
            self.ENFT_MINI_AN_NAIS = None
        if self.ENFT_MIN != "1":
            self.ENFT_MIN_NB = None
            self.ENFT_MESURE_SOCIOEDUC = None
            self.ENFT_PROC_JAF = None
        if self.ENFT_MAJ != "1":
            self.ENFT_MAJ_NB = None
        if self.ENFT_NB is None or self.ENFT_NB < 2:
            self.ENFT_MAXI_AN_NAIS = None 
        return self