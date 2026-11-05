"""Fixtures partagées par tous les tests.

Base de test : une base PostgreSQL DÉDIÉE (atelier_test), créée par
`alembic upgrade head` (jamais create_all) puis VIDÉE avant chaque test.
"""
import os

# ⚠ À faire AVANT d'importer l'application : on bascule l'API sur la base de test.
from app.core.config import settings  # noqa: E402

TEST_URL = os.getenv("TEST_DATABASE_URL", settings.TEST_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_URL

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
import app.seed as module_seed  # noqa: E402
from app.seed import seed  # noqa: E402
from functools import lru_cache  # noqa: E402

# Accélère les tests : le seed est rejoué avant CHAQUE test et Argon2 est
# volontairement lent. On mémorise donc le hash de chaque mot de passe de seed.
module_seed.hash_password = lru_cache(maxsize=None)(module_seed.hash_password)

engine_test = create_engine(TEST_URL, pool_pre_ping=True)
SessionTest = sessionmaker(bind=engine_test, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def schema_de_test():
    """Une fois par session pytest : applique les migrations Alembic sur la base de test."""
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")
    yield
    engine_test.dispose()


@pytest.fixture(autouse=True)
def base_propre():
    """Avant CHAQUE test : vide toutes les tables, puis recrée admin + démo + catalogue."""
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine_test.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    with SessionTest() as db:
        seed(db, comptes_demo=True)
    yield


@pytest.fixture
def db():
    with SessionTest() as session:
        yield session


@pytest.fixture
def client():
    def override_get_db():
        session = SessionTest()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _token(client, email: str, mot_de_passe: str) -> str:
    r = client.post("/api/v1/auth/login", data={"username": email, "password": mot_de_passe})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def entete(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def token_admin(client):
    return _token(client, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)


@pytest.fixture
def token_accueil(client):
    return _token(client, "accueil@atelier.sn", "accueil123")


@pytest.fixture
def token_tailleur(client):
    return _token(client, "tailleur@atelier.sn", "tailleur123")


@pytest.fixture
def h_admin(token_admin):
    return entete(token_admin)


@pytest.fixture
def h_accueil(token_accueil):
    return entete(token_accueil)


@pytest.fixture
def h_tailleur(token_tailleur):
    return entete(token_tailleur)


# ---------------------------------------------------------------- Données métier
@pytest.fixture
def catalogue(client, h_admin):
    """{"Boubou homme": 1, "Robe": 3, ...} : id de chaque prestation du seed."""
    return {t["nom"]: t["id"] for t in client.get("/api/v1/catalogue", headers=h_admin).json()}


@pytest.fixture
def client_fatou(client, h_accueil):
    r = client.post("/api/v1/clients", headers=h_accueil,
                    json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def mesure_fatou(client, client_fatou, h_tailleur):
    r = client.post(f"/api/v1/clients/{client_fatou['id']}/mesures", headers=h_tailleur,
                    json={"tour_poitrine": 92, "tour_taille": 74, "longueur_robe": 140})
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def commande_exemple(client, client_fatou, mesure_fatou, catalogue, h_accueil):
    """Commande de Fatou : 1 Boubou femme (30 000) + 2 Robes à 15 000 négociées = 60 000 FCFA."""
    r = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": client_fatou["id"],
        "lignes": [
            {"type_vetement_id": catalogue["Boubou femme"], "description": "bazin bleu, broderie dorée"},
            {"type_vetement_id": catalogue["Robe"], "quantite": 2, "prix_unitaire": 15000},
        ],
    })
    assert r.status_code == 201, r.text
    return r.json()


def avancer(client, headers, commande_id: int, *statuts: str):
    """Fait passer une commande par plusieurs statuts successifs."""
    for s in statuts:
        r = client.patch(f"/api/v1/commandes/{commande_id}/statut", headers=headers, json={"statut": s})
        assert r.status_code == 200, r.text
    return r.json()
