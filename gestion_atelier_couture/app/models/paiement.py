from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.commande import Commande


class Paiement(Base):
    """Acompte ou solde versé sur une commande."""

    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), index=True)
    montant: Mapped[int] = mapped_column(Integer)  # FCFA, > 0
    mode: Mapped[str] = mapped_column(String(20))  # especes | wave | orange_money | virement | cheque
    reference: Mapped[str | None] = mapped_column(String(100))
    date_paiement: Mapped[date] = mapped_column(Date, default=date.today)
    enregistre_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    commande: Mapped["Commande"] = relationship(back_populates="paiements")
