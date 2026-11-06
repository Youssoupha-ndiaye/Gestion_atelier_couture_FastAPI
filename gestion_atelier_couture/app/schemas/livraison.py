from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constantes import ModeLivraison


class LivraisonUpsert(BaseModel):
    """PUT /commandes/{id}/livraison : crée OU remplace l'unique livraison de la commande."""

    model_config = ConfigDict(str_strip_whitespace=True)

    mode: ModeLivraison
    adresse: str | None = Field(default=None, max_length=255)
    livreur: str | None = Field(default=None, max_length=100)
    date_prevue: date
    notes: str | None = None

    @model_validator(mode="after")
    def adresse_si_domicile(self):
        """RG18 : livraison à domicile => adresse obligatoire."""
        if self.mode == "domicile" and not self.adresse:
            raise ValueError("L'adresse est obligatoire pour une livraison à domicile")
        return self


class LivraisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: str
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: str
    notes: str | None


class LivraisonTournee(LivraisonRead):
    """Une ligne de la liste de tournée du livreur."""

    numero_commande: str | None
    client_nom: str
    client_telephone: str | None
    solde_commande: int
