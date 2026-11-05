from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constantes import STATUTS_FINAUX
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.catalogue import TypeVetement
    from app.models.client import Client
    from app.models.livraison import Livraison
    from app.models.mesure import Mesure
    from app.models.paiement import Paiement
    from app.models.utilisateur import Utilisateur


class Commande(Base):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)  # CMD-AAAA-NNNNN
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), index=True)
    mesure_id: Mapped[int | None] = mapped_column(ForeignKey("mesures.id", ondelete="RESTRICT"))
    statut: Mapped[str] = mapped_column(String(20), default="en_attente", index=True)
    date_commande: Mapped[date] = mapped_column(Date, default=date.today)
    date_livraison_prevue: Mapped[date] = mapped_column(Date)
    date_livraison_reelle: Mapped[date | None] = mapped_column(Date)
    remise: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    montant_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    montant_paye: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    cree_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="commandes")
    mesure: Mapped["Mesure | None"] = relationship()
    cree_par: Mapped["Utilisateur | None"] = relationship()
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan", order_by="LigneCommande.id"
    )
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan",
        order_by="(Paiement.created_at, Paiement.id)",
    )
    historique: Mapped[list["HistoriqueStatut"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan",
        order_by="(HistoriqueStatut.date_changement, HistoriqueStatut.id)",
    )
    livraison: Mapped["Livraison | None"] = relationship(
        back_populates="commande", cascade="all, delete-orphan", uselist=False
    )

    # ---- Champs CALCULÉS (pas de colonne en base) ----
    @property
    def solde(self) -> int:
        """RG7 : solde = total - payé."""
        return self.montant_total - self.montant_paye

    @property
    def en_retard(self) -> bool:
        """RG11 : date prévue dépassée et commande ni livrée ni annulée."""
        return self.date_livraison_prevue < date.today() and self.statut not in STATUTS_FINAUX

    @property
    def client_nom(self) -> str:
        return f"{self.client.prenom} {self.client.nom}" if self.client else ""


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    type_vetement_id: Mapped[int] = mapped_column(ForeignKey("types_vetement.id"))
    description: Mapped[str | None] = mapped_column(Text)
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix_unitaire: Mapped[int] = mapped_column(Integer)  # COPIÉ du catalogue (RG6)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    type_vetement: Mapped["TypeVetement"] = relationship()

    @property
    def sous_total(self) -> int:
        return self.quantite * self.prix_unitaire

    @property
    def nom_prestation(self) -> str:
        return self.type_vetement.nom if self.type_vetement else ""


class HistoriqueStatut(Base):
    __tablename__ = "historique_statuts"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    ancien_statut: Mapped[str | None] = mapped_column(String(20))  # NULL à la création (RG15)
    nouveau_statut: Mapped[str] = mapped_column(String(20))
    commentaire: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    date_changement: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commande: Mapped["Commande"] = relationship(back_populates="historique")
    utilisateur: Mapped["Utilisateur | None"] = relationship()

    @property
    def utilisateur_nom(self) -> str | None:
        return self.utilisateur.nom_complet if self.utilisateur else None
