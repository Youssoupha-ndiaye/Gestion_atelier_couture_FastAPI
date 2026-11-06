"""Dépendances FastAPI (Depends) : utilisateur connecté et contrôle des rôles."""
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.utilisateur import Utilisateur

# tokenUrl -> Swagger affiche le bouton « Authorize » (formulaire username/password)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _erreur_401(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Utilisateur:
    """Décode le JWT, charge l'utilisateur et vérifie qu'il est ACTIF (RG22)."""
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise _erreur_401("Jeton expiré : veuillez vous reconnecter")
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise _erreur_401("Jeton invalide")

    user = db.get(Utilisateur, user_id)
    if user is None:
        raise _erreur_401("Utilisateur introuvable")
    if not user.actif:
        # RG22 : un compte désactivé est refusé immédiatement, même avec un jeton encore valide
        raise _erreur_401("Compte désactivé")
    return user


def require_role(*roles: str) -> Callable[..., Utilisateur]:
    """Fabrique une dépendance qui exige un des rôles donnés.

    L'admin est TOUJOURS autorisé (« l'admin peut tout faire ») :
    require_role("tailleur") accepte donc tailleur ET admin.
    """
    autorises = set(roles) | {"admin"}

    def _verifier(user: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if user.role not in autorises:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : rôle requis {' ou '.join(sorted(autorises))} (votre rôle : {user.role})",
            )
        return user

    return _verifier
