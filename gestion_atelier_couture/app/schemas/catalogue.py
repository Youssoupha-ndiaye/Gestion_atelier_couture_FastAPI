from pydantic import BaseModel, ConfigDict, Field, model_validator


class TypeVetementCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str = Field(min_length=1, max_length=100)
    description: str | None = None
    prix_base: int = Field(ge=0)  # FCFA
    delai_jours: int = Field(ge=0)
    actif: bool = True


class TypeVetementUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nom: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    prix_base: int | None = Field(default=None, ge=0)
    delai_jours: int | None = Field(default=None, ge=0)
    actif: bool | None = None

    @model_validator(mode="after")
    def _pas_de_null(self):
        for champ in ("nom", "prix_base", "delai_jours", "actif"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ {champ} ne peut pas être vidé")
        return self


class TypeVetementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
