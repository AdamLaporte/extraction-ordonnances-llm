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

    ACCORD: Literal["0", "1"]
    RENVOI_FOND: Literal["0", "1"]
    OP_DUREE: Optional[float] = None
    ART_696_DEC: Literal["1", "2", "3", "9", "X"]
    ENFT_IEC_TOT_DEC: Literal["0", "1", "X"]
    ENFT_IEC_MEDIA_DEC: Literal["0", "1", "X"]
    ENFT_MEDIA_DEC: Literal["0", "1", "2", "X"]
    ENFT_VISIT_DEC: Literal["0", "1", "2", "3", "9", "X"]
    ENFT_DVH_DEC: Literal["0", "1", "2", "3", "X"]
    ENFT_PASS_BRAS_DEC: Literal["0", "1", "2", "3", "4", "5", "9", "X"]
    ENFT_RESERVE_DEC: Literal["0", "1", "X"]
    ENFT_REVISION_DEC: Literal["0", "1", "X"]
    ENFT_AUTRE_DEC: Literal["0", "1", "X"]
    ENFT_AP_CONJ_DEC: Literal["0", "1", "X"]
    ENFT_AP_DEM_DEC: Literal["0", "1", "X"]
    ENFT_RESID_DEM_DEC: Literal["0", "1", "X"]
    ENFT_RESID_DEC: Literal["1", "2", "3", "4", "5", "9", "X"]
    ENFT_CEE_DEC: Literal["0", "1", "X"]
    ENFT_CEE_VIA_DEC: Literal["0", "1"]
    RAISONNEMENT_MONTANT_CEE: str = Field(
        description="Chain of Thought: Explique brièvement le calcul ou la lecture du texte concernant la contribution à l'entretien des enfants (ex: 'Le texte indique 150€ par enfant, il y a 2 enfants, mais la consigne demande le montant par enfant, donc 150')."
    )
    ENFT_CEE_DEC_MT: Optional[float] = Field(
        description="Montant mensuel de la contribution à l'entretien des enfants décidé (par enfant)"
    )
    ENFT_SORTIE_TERR_DEC: Literal["0", "1"]
    ENFT_EXPERT_PSY_DEC: Literal["0", "1"]
    ENFT_INVESTIG_DEC: Literal["0", "1"]
    ENFT_MAJ_IEC_DEC: Literal["0", "1", "X"]
    DEM_IEC_DEC: Literal["0", "1", "X"]
    NOUV_CONJ_IEC_DEC: Literal["0", "1", "X"]
    AUTRE_IEC_DEC: Literal["0", "1", "X"]
    ARME_INTERDI_DEC: Literal["0", "1", "X"]
    LIEU_INTERDI_DEC: Literal["0", "1", "X"]
    LIEU_INTERDI_DOMIC_DEC: Literal["0", "1"]
    LIEU_INTERDI_ECOLE_DEC: Literal["0", "1"]
    LIEU_INTERDI_W_DEC: Literal["0", "1"]
    INTERDI_AUTRE_DEC: Literal["0", "1", "X"]
    RESID_SEPARE_DEC: Literal["0", "1", "X"]
    ADR_INSTANCE_DEC: Literal["0", "1", "X"]
    ADR_VIE_DEC: Literal["0", "1", "X"]
    LOGT_USAGE_DEC: Literal["0", "1", "X"]
    LOGT_BAIL_DEC: Literal["0", "1", "5", "X"]
    LOGT_PEC_FRAIS_DEC: Literal["0", "1", "2", "3", "X"]
    EXPULS_LOGT_DEC: Literal["0", "1", "X"]
    LOGT_AUTRE_DEC: Literal["0", "1", "5", "9", "X"]
    PEC_SANITAIRE_DEC: Literal["0", "1", "X"]
    CONTRIB_MRGE_DEC: Literal["0", "1", "X"]
    CONTRIB_MRGE_DEC_MT: Optional[float] = None
    ART_700_DEM_DEC: Literal["0", "1", "X"]
    ART_700_DEF_DEC: Literal["0", "1", "X"]
    ART_700_MT: Optional[float] = None
    AJ_PROV_DEM_DEC: Literal["0", "1"]
    AJ_PROV_DEF_DEC: Literal["0", "1"]

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.ACCORD != "1":
            self.OP_DUREE = None
        if self.ENFT_CEE_DEC != "1":
            self.ENFT_CEE_VIA_DEC = None
            self.ENFT_CEE_DEC_MT = None
        if self.CONTRIB_MRGE_DEC != "1":
            self.CONTRIB_MRGE_DEC_MT = None
        if self.ART_700_DEM_DEC != "1" and self.ART_700_DEF_DEC != "1":
            self.ART_700_MT = None
        
        return self
