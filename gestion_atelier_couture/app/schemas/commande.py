from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constantes import StatutCommande
from app.schemas.livraison import LivraisonRead
from app.schemas.paiement import PaiementRead


# ---------------------------------------------------------------- Lignes
class LigneCreate(BaseModel):
    type_vetement_id: int
    description: str | None = Field(default=None, examples=["bazin bleu, broderie dorée"])
    quantite: int = Field(default=1, ge=1)
    prix_unitaire: int | None = Field(default=None, ge=0,
                                      description="Facultatif : défaut = prix_base du catalogue (RG6)")


class LigneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type_vetement_id: int
    nom_prestation: str      # propriété du modèle
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int          # propriété du modèle = quantite × prix_unitaire


# ---------------------------------------------------------------- Commande
class CommandeCreate(BaseModel):
    client_id: int
    mesure_id: int | None = Field(default=None, description="Absent : dernières mesures du client (RG9)")
    lignes: list[LigneCreate] = Field(min_length=1)  # au moins une ligne
    remise: int = Field(default=0, ge=0)
    date_livraison_prevue: date | None = Field(
        default=None, description="Absent : date du jour + plus grand délai des prestations (RG8)")
    notes: str | None = None


class CommandeUpdate(BaseModel):
    """PATCH : seuls les champs envoyés sont modifiés. Les lignes ont leurs propres routes."""

    mesure_id: int | None = None
    date_livraison_prevue: date | None = None
    remise: int | None = Field(default=None, ge=0)
    notes: str | None = None

    @model_validator(mode="after")
    def _pas_de_null(self):
        for champ in ("date_livraison_prevue", "remise"):
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"Le champ {champ} ne peut pas être vidé")
        return self


class StatutUpdate(BaseModel):
    statut: StatutCommande
    commentaire: str | None = None


class HistoriqueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ancien_statut: str | None
    nouveau_statut: str
    commentaire: str | None
    utilisateur_id: int | None
    utilisateur_nom: str | None
    date_changement: datetime


class CommandeListItem(BaseModel):
    """Version courte pour les listes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: str
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int        # calculé
    en_retard: bool   # calculé (RG11)


class CommandeDetail(CommandeListItem):
    """Version complète : lignes, paiements et livraison."""

    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    notes: str | None
    cree_par_id: int | None
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneRead]
    paiements: list[PaiementRead]
    livraison: LivraisonRead | None
