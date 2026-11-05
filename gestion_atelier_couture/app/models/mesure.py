from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.client import Client


class Mesure(Base):
    """Une prise de mesures (on garde TOUTES les prises : RG3)."""

    __tablename__ = "mesures"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    date_prise: Mapped[date] = mapped_column(Date, default=date.today, server_default=func.current_date())
    prise_par_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    # Les 18 mesures en cm (toutes facultatives, au moins une renseignée : RG2)
    taille_cm: Mapped[float | None] = mapped_column(Float)
    tour_cou: Mapped[float | None] = mapped_column(Float)
    carrure_dos: Mapped[float | None] = mapped_column(Float)
    longueur_epaule: Mapped[float | None] = mapped_column(Float)
    tour_poitrine: Mapped[float | None] = mapped_column(Float)
    tour_taille: Mapped[float | None] = mapped_column(Float)
    tour_bassin: Mapped[float | None] = mapped_column(Float)
    longueur_manche: Mapped[float | None] = mapped_column(Float)
    tour_bras: Mapped[float | None] = mapped_column(Float)
    tour_poignet: Mapped[float | None] = mapped_column(Float)
    longueur_dos: Mapped[float | None] = mapped_column(Float)
    longueur_haut: Mapped[float | None] = mapped_column(Float)
    longueur_pantalon: Mapped[float | None] = mapped_column(Float)
    tour_cuisse: Mapped[float | None] = mapped_column(Float)
    tour_genou: Mapped[float | None] = mapped_column(Float)
    bas_pantalon: Mapped[float | None] = mapped_column(Float)
    entrejambe: Mapped[float | None] = mapped_column(Float)
    longueur_robe: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship(back_populates="mesures")
