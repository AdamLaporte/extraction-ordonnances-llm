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

    POSTURE_FORME: Literal["0", "1", "2", "X"]
    POSTURE_FOND: Literal["0", "1"]
    REP_DEMANDE: Literal["0", "1"]
    ENFT_HEBERG_POS: Literal["0", "1", "X"]
    ENFT_HEBERG_DEF: Literal["1", "2", "3", "4", "X"]
    ENFT_PASS_BRAS_DEF: Literal["0", "1", "X"]
    ENFT_AP_POS: Literal["0", "1", "X"]
    ENFT_RESID_DEM_POS: Literal["0", "1", "X"]
    ENFT_RESID_DEM_DEF: Literal["1", "2", "3", "4", "5", "9", "X"]
    ENFT_CEE_DEF_MT: Optional[float] = None
    RESID_SEPARE_POS: Literal["0", "1", "X"]
    LOGT_POS: Literal["0", "1", "X"]
    LOGT_PEC_FRAIS_POS: Literal["0", "1", "2", "X"]
    PEC_SANITAIRE_POS: Literal["0", "1", "X"]
    CONTRIB_MRGE_POS: Literal["0", "1", "2", "X"]
    CONTRIB_MRGE_DEF_MT: Optional[float] = None
    ART_700_DEF: Literal["0", "1"]
    ENFT_SORTIE_TERR_DEF: Literal["0", "1"]
    ENFT_EXPERT_PSY_DEF: Literal["0", "1"]
    ENFT_INVESTIG_DEF: Literal["0", "1"]
    AJ_PROV_DEF: Literal["0", "1"]


    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
          
        if self.ENFT_HEBERG_POS != "0":
            self.ENFT_HEBERG_DEF = None
        if self.CONTRIB_MRGE_POS != "2":
            self.CONTRIB_MRGE_DEF_MT = None
        if self.REP_DEMANDE != "1":
            self.ART_700_DEF = None
        return self