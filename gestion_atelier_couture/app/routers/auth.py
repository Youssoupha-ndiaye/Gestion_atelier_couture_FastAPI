from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.auth import Token
from app.schemas.utilisateur import UtilisateurRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Token, summary="1 · Se connecter (formulaire OAuth2)")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """FORMULAIRE (pas JSON) : `username` = email, `password` = mot de passe.

    C'est ce format qui permet au bouton « Authorize » de Swagger de fonctionner.
    """
    return auth_service.connexion(db, form.username, form.password)


@router.get("/me", response_model=UtilisateurRead, summary="2 · Mon profil")
def me(user: Utilisateur = Depends(get_current_user)):
    return user
