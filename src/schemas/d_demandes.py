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

    MOTIV_DEM: Literal["1", "2", "3", "9", "X"]
    MOTIV_DEM_DET: Optional[str] = None
    ENFT_IEC_TOT_DEM: Literal["0", "1"]
    ENFT_IEC_MEDIA_SUBS_DEM: Literal["0", "1"]
    ENFT_IEC_MEDIA_DEM: Literal["0", "1"]
    ENFT_MEDIA_DEM: Literal["0", "1"]
    ENFT_VISIT_SUBS_DEM: Literal["0", "1"]
    ENFT_VISIT_DEM: Literal["0", "1"]
    ENFT_DVH_DEM: Literal["0", "1"]
    ENFT_PASS_BRAS_DEM: Literal["0", "1"]
    ENFT_RESERVE_DEM: Literal["0", "1"]
    ENFT_REVISION_DEM: Literal["0", "1"]
    ENFT_AUTRE_DEM: Literal["0", "1"]
    ENFT_AUTRE_DEM_DET: Optional[str] = None
    ENFT_AP_CONJ_DEM: Literal["0", "1"]
    ENFT_AP_DEM_DEM: Literal["0", "1"]
    ENFT_RESID_DEM_DEM: Literal["0", "1"]
    ENFT_CEE_DEM: Literal["0", "1"]
    ENFT_CEE_DEM_MT: Optional[float] = None
    ENFT_SORTIE_TERR_DEM: Literal["0", "1"]
    ENFT_EXPERT_PSY_DEM: Literal["0", "1"]
    ENFT_INVESTIG_DEM: Literal["0", "1"]
    ENFT_MAJ_IEC_DEM: Literal["0", "1"]
    DEM_IEC_DEM: Literal["0", "1"]
    NOUV_CONJ_IEC_DEM: Literal["0", "1"]
    AUTRE_IEC_DEM: Literal["0", "1"]
    ARME_INTERDI_DEM: Literal["0", "1"]
    LIEU_INTERDI_DEM: Literal["0", "1"]
    LIEU_INTERDI_DOMIC_DEM: Literal["0", "1"]
    LIEU_INTERDI_ECOLE_DEM: Literal["0", "1"]
    LIEU_INTERDI_W_DEM: Literal["0", "1"]
    INTERDI_AUTRE_DEM: Literal["0", "1"]
    INTERDI_AUTRE_DEM_DET: Optional[str] = None
    RESID_SEPARE_DEM: Literal["0", "1"]
    ADR_INSTANCE_DEM: Literal["0", "1"]
    ADR_INSTANCE_CHEZ_DEM: Literal["1", "2", "9", "X"]
    ADR_VIE_DEM: Literal["0", "1"]
    LOGT_USAGE_DEM: Literal["0", "1"]
    LOGT_BAIL_DEM: Literal["0", "1"]
    LOGT_PEC_FRAIS_DEM: Literal["0", "1", "2", "3"]
    EXPULS_LOGT_DEM: Literal["0", "1"]
    LOGT_AUTRE_DEM: Literal["0", "1"]
    LOGT_AUTRE_DEM_DET: Optional[str] = None
    PEC_SANITAIRE_DEM: Literal["0", "1"]
    CONTRIB_MRGE_DEM: Literal["0", "1"]
    CONTRIB_MRGE_DEM_MT: Optional[float] = None
    ART_700_DEM: Literal["0", "1"]
    ART_696_DEM: Literal["0", "1"]
    AJ_PROV_DEM: Literal["0", "1"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.MOTIV_DEM != "9":
            self.MOTIV_DEM_DET = None
        
        if self.ENFT_IEC_TOT_DEM != "1":
            self.ENFT_IEC_MEDIA_SUBS_DEM = None
        if self.ENFT_IEC_MEDIA_DEM != "1" and self.ENFT_MEDIA_DEM != "1":
            self.ENFT_VISIT_SUBS_DEM = None
        if self.ENFT_VISIT_SUBS_DEM != "1":
            self.ENFT_AUTRE_DEM_DET = None
        if self.ENFT_CEE_DEM != "1":
            self.ENFT_CEE_DEM_MT = None
        if self.LIEU_INTERDI_DEM != "1":
            self.LIEU_INTERDI_DOMIC_DEM = None
            self.LIEU_INTERDI_ECOLE_DEM = None
            self.LIEU_INTERDI_W_DEM = None
        if self.INTERDI_AUTRE_DEM != "1":
            self.INTERDI_AUTRE_DEM_DET = None
        if self.LOGT_AUTRE_DEM != "1":
            self.LOGT_AUTRE_DEM_DET = None
        if self.CONTRIB_MRGE_DEM != "1":
            self.CONTRIB_MRGE_DEM_MT = None
        return self
