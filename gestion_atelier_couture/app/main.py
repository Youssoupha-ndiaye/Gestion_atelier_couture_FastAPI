"""Point d'entrée de l'API : crée l'application FastAPI, branche les routeurs.

Lancement : uvicorn app.main:app --reload
"""
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.routers import auth, catalogue, clients, commandes, livraisons, mesures, paiements, statistiques, utilisateurs

API_PREFIX = "/api/v1"

app = FastAPI(
    title=settings.APP_NAME,
    description="Back-end REST de gestion d'un atelier de couture (Dakar). "
                "Cliquez sur **Authorize** et connectez-vous avec votre email / mot de passe.",
    version="1.0.0",
)

register_exception_handlers(app)

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(utilisateurs.router, prefix=API_PREFIX)
app.include_router(clients.router, prefix=API_PREFIX)
app.include_router(catalogue.router, prefix=API_PREFIX)
app.include_router(mesures.router, prefix=API_PREFIX)
app.include_router(commandes.router, prefix=API_PREFIX)
app.include_router(paiements.router, prefix=API_PREFIX)
app.include_router(livraisons.router, prefix=API_PREFIX)
app.include_router(statistiques.router, prefix=API_PREFIX)


@app.get("/health", tags=["Santé"], summary="44 · Vérifier que l'API et la base répondent")
def health(db: Session = Depends(get_db)):
    """Exécute `SELECT 1` sur PostgreSQL puis renvoie {"status": "ok"}."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
