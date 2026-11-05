"""Connexion à PostgreSQL avec SQLAlchemy 2.

- engine       : l'objet qui sait parler à la base (pool de connexions).
- SessionLocal : fabrique de sessions (une session = une unité de travail).
- Base         : classe mère de TOUS les modèles (style moderne DeclarativeBase).
- get_db       : dépendance FastAPI qui ouvre une session par requête et la ferme ensuite.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe mère des modèles. Base.metadata contient la description de toutes les tables."""


def get_db() -> Generator[Session, None, None]:
    """Fournit une session à la route, puis l'annule (rollback) en cas d'erreur et la ferme.

    Le commit est fait explicitement par le routeur quand tout s'est bien passé.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
