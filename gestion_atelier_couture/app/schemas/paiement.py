from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constantes import ModePaiement


class PaiementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    montant: int = Field(gt=0, description="FCFA, > 0 et ≤ solde (RG16)")
    mode: ModePaiement
    reference: str | None = Field(default=None, max_length=100, examples=["WAVE-TX-458796"])
    date_paiement: date | None = Field(default=None, description="Défaut : aujourd'hui")

    @field_validator("date_paiement")
    @classmethod
    def pas_dans_le_futur(cls, v: date | None) -> date | None:
        """RG16 : un paiement ne peut pas être daté dans le futur (422)."""
        if v is not None and v > date.today():
            raise ValueError("La date de paiement ne peut pas être dans le futur")
        return v


class PaiementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: str
    reference: str | None
    date_paiement: date
    enregistre_par_id: int | None
    created_at: datetime
