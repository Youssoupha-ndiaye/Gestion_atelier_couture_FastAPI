from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TypeVetement(Base):
    """Prestation du catalogue (boubou, robe, retouche...)."""

    __tablename__ = "types_vetement"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    prix_base: Mapped[int] = mapped_column(Integer, default=0)  # FCFA (jamais Float)
    delai_jours: Mapped[int] = mapped_column(Integer, default=0)  # sert à RG8
    actif: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")  # RG6
