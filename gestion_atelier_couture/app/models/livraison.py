from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.commande import Commande


class Livraison(Base):
    """0 ou 1 livraison par commande (commande_id UNIQUE)."""

    __tablename__ = "livraisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(
        ForeignKey("commandes.id", ondelete="CASCADE"), unique=True
    )
    mode: Mapped[str] = mapped_column(String(20))  # retrait_atelier | domicile
    adresse: Mapped[str | None] = mapped_column(String(255))  # obligatoire si domicile (RG18)
    livreur: Mapped[str | None] = mapped_column(String(100))
    date_prevue: Mapped[date] = mapped_column(Date)
    date_effective: Mapped[date | None] = mapped_column(Date)
    statut: Mapped[str] = mapped_column(String(20), default="planifiee")  # planifiee | livree
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="livraison")

    # ---- Champs calculés pour la liste de tournée (GET /livraisons) ----
    @property
    def numero_commande(self) -> str | None:
        return self.commande.numero if self.commande else None

    @property
    def client_nom(self) -> str:
        return self.commande.client_nom if self.commande else ""

    @property
    def client_telephone(self) -> str | None:
        return self.commande.client.telephone if self.commande and self.commande.client else None

    @property
    def solde_commande(self) -> int:
        return self.commande.solde if self.commande else 0
