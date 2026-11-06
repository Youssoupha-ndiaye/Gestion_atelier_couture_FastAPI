"""Service d'authentification."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models.utilisateur import Utilisateur

MESSAGE_ECHEC = "Email ou mot de passe incorrect"  # RG23 : message identique dans tous les cas


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur:
    user = db.scalar(select(Utilisateur).where(Utilisateur.email == email.strip().lower()))
    # RG23 : on ne dit JAMAIS si c'est l'email ou le mot de passe qui est faux
    if user is None or not verify_password(mot_de_passe, user.mot_de_passe_hash):
        raise UnauthorizedError(MESSAGE_ECHEC)
    if not user.actif:
        raise UnauthorizedError("Compte désactivé")
    return user


def connexion(db: Session, email: str, mot_de_passe: str) -> dict:
    user = authentifier(db, email, mot_de_passe)
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
