# Fichier : schemas/a_procedure.py
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime, date


class Schema(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=False,
        extra="forbid",
        serialization_exclude_none=True,
    )

    NO_CMPST: str

    TYP_JUR: Literal["TJ", "TPI", "TPISD", "TPRX"]
    L_COM_LOC: Optional[str] = None
    NO_RG: Optional[str] = None
    HC_OPVC: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    DA_SAISINE: Optional[date] = None
    DA_FIX_AUDIENCE: Optional[date] = None
    FIX_AUDIENCE_NOTIF: Literal["1", "2", "3", "4", "X"]
    DA_AUDIENCE: Optional[date] = None
    AUDIENCE_CONFIN: Literal["1", "2", "3", "9", "X"]
    DA_DEC: Optional[date] = None
    OP_PREC_REFU: Literal["0", "1"]
    OP_PREC_ACCOR: Literal["0", "1"]
    RENVOI: Literal["0", "1"]
    RENVOI_QUI: Literal["1", "2", "3", "4", "X"]
    DA_RENVOI_AUDIENCE: Optional[date] = None
    RENVOI_MOTIF_CONTRAD: Literal["0", "1"]
    RENVOI_MOTIF_DELAI: Literal["0", "1"]
    RENVOI_MOTIF_PIECES: Literal["0", "1"]
    RENVOI_MOTIF_AVOCAT: Literal["0", "1"]
    RENVOI_MOTIF_PARQUET: Literal["0", "1"]
    RENVOI_MOTIF_INTERP: Literal["0", "1"]
    RENVOI_MOTIF_AJ: Literal["0", "1", "2", "3"]
    RENVOI_MOTIF_AUTRE: Literal["0", "1"]
    RENVOI_MOTIF_AUTRE_DET: Optional[str] = None
    MP_ORIGINE: Literal["0", "1"]
    MP_PRESENCE: Literal["0", "1"]
    MP_CONCLUSION: Literal["0", "1", "2", "9"]
    PRES_AUDIENCE_DEM: Literal["0", "1", "X"]
    AVOC_DEM: Literal["1", "2", "3", "4", "X"]
    AJ_DEM_OK: Literal["0", "1"]
    PRES_AUDIENCE_DEF: Literal["0", "1", "X"]
    AVOC_DEF: Literal["1", "2", "3", "4", "X"]
    AJ_DEF_OK: Literal["0", "1"]
    AUDIENCE_INTERP: Literal["0", "1"]
    AUDITION_SEPARE: Literal["0", "1"]
    AUDITION_SEPARE_QUI: Literal["1", "2", "3", "4", "X"]
    AUDITION_ENFT: Literal["0", "1", "2"]
    TGD: Literal["0", "1"]

    @field_validator("DA_SAISINE", "DA_FIX_AUDIENCE", mode="before")
    def _parse_french_date(cls, v: str | date | None) -> date | None:
        if v is None or isinstance(v, date):
            return v
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            pass
        try:
            return datetime.strptime(v, "%d/%m/%Y").date()
        except ValueError as exc:
            raise ValueError(f"Date invalide : {v!r}. Formats acceptés : YYYY‑MM‑DD ou DD/MM/YYYY.") from exc

    @model_validator(mode="after")
    def passer_a_none_variables_optionnelles(self) -> "Schema":
        if self.RENVOI != "1":
            self.RENVOI_QUI = None
            self.DA_RENVOI_AUDIENCE = None
            self.RENVOI_MOTIF_CONTRAD = None
            self.RENVOI_MOTIF_DELAI = None
            self.RENVOI_MOTIF_PIECES = None
            self.RENVOI_MOTIF_AVOCAT = None
            self.RENVOI_MOTIF_PARQUET = None
            self.RENVOI_MOTIF_INTERP = None
            self.RENVOI_MOTIF_AJ = None
            self.RENVOI_MOTIF_AUTRE = None
        if self.RENVOI_MOTIF_AUTRE != "1":
            self.RENVOI_MOTIF_AUTRE_DET = None
        if self.AUDITION_SEPARE != "1":
            self.AUDITION_SEPARE_QUI = None
        return self

    @model_validator(mode="after")
    def _nullify_fix_audience_if_early(self) -> "Schema":
        if self.DA_SAISINE is None:
            return self
        limite = date(2020, 5, 27)
        if self.DA_SAISINE < limite:
            self.DA_FIX_AUDIENCE = None
            self.FIX_AUDIENCE_NOTIF = None
        return self