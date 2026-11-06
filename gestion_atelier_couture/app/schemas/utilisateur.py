from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.constantes import Role


class UtilisateurCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    nom_complet: str = Field(min_length=1, max_length=150)
    mot_de_passe: str = Field(min_length=8, max_length=128)  # RG21 : au moins 8 caractères
    role: Role

    @field_validator("email")
    @classmethod
    def email_minuscule(cls, v: str) -> str:
        return v.lower()


class UtilisateurUpdate(BaseModel):
    """PATCH : tous les champs facultatifs, seuls ceux envoyés sont modifiés."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr | None = None
    nom_complet: str | None = Field(default=None, min_length=1, max_length=150)
    mot_de_passe: str | None = Field(default=None, min_length=8, max_length=128)
    role: Role | None = None
    actif: bool | None = None

    @field_validator("email")
    @classmethod
    def email_minuscule(cls, v: str | None) -> str | None:
        return v.lower() if v else v

    @model_validator(mode="after")
    def pas_de_null(self):
        for champ in ("email", "nom_complet", "mot_de_passe", "role", "actif"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ {champ} ne peut pas être vidé")
        return self


class UtilisateurRead(BaseModel):
    """Ce qu'on renvoie : PAS de mot_de_passe_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: str
    actif: bool
    created_at: datetime
