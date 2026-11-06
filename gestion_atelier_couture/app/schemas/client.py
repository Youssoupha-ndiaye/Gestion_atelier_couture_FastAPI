import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.constantes import Genre


def normaliser_telephone(v: str) -> str:
    """RG1 : on enlève espaces . - ( ) puis on exige +? suivi de 6 à 20 chiffres.

    « 77 123 45 67 » et « 77.123.45.67 » deviennent tous les deux « 771234567 ».
    """
    v = re.sub(r"[\s.\-()]", "", v)
    if not re.fullmatch(r"\+?\d{6,20}", v):
        raise ValueError("Numéro invalide : 6 à 20 chiffres, '+' initial facultatif")
    return v


class ClientCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str
    email: EmailStr | None = None
    adresse: str | None = Field(default=None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("telephone")
    @classmethod
    def _tel(cls, v: str) -> str:
        return normaliser_telephone(v)


class ClientUpdate(BaseModel):
    """PATCH : tout est facultatif, mais nom / prenom / telephone ne peuvent pas être vidés."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    telephone: str | None = None
    email: EmailStr | None = None
    adresse: str | None = Field(default=None, max_length=255)
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("telephone")
    @classmethod
    def _tel(cls, v: str | None) -> str | None:
        return normaliser_telephone(v) if v is not None else v

    @model_validator(mode="after")
    def _obligatoires_non_vides(self):
        for champ in ("nom", "prenom", "telephone"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ {champ} est obligatoire et ne peut pas être vidé")
        return self


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientResume(BaseModel):
    """Route 13 : synthèse financière d'un client (commandes annulées exclues)."""

    client: ClientRead
    nombre_commandes: int
    commandes_en_cours: int
    montant_total: int
    montant_paye: int
    solde: int
    derniere_commande: date | None
    derniere_mesure: date | None
