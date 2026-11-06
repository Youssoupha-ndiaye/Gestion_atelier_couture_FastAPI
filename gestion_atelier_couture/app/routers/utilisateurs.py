from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.utilisateur import Utilisateur
from app.schemas.common import Page
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurRead, UtilisateurUpdate
from app.services import utilisateur_service

# TOUTES ces routes sont réservées à l'admin (dépendance admin_requis sur chaque route)
router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])
admin_requis = require_role("admin")


@router.post("", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED,
             summary="3 · Créer un compte du personnel")
def creer_utilisateur(data: UtilisateurCreate, db: Session = Depends(get_db),
                      _: Utilisateur = Depends(admin_requis)):
    user = utilisateur_service.creer(db, data)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=Page[UtilisateurRead], summary="4 · Lister le personnel (tri par nom)")
def lister_utilisateurs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                        db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    items, total = utilisateur_service.lister(db, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UtilisateurRead, summary="5 · Détail d'un utilisateur")
def obtenir_utilisateur(user_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    return utilisateur_service.obtenir(db, user_id)


@router.patch("/{user_id}", response_model=UtilisateurRead,
              summary="6 · Modifier / désactiver un compte (RG24)")
def modifier_utilisateur(user_id: int, data: UtilisateurUpdate, db: Session = Depends(get_db),
                         admin: Utilisateur = Depends(admin_requis)):
    user = utilisateur_service.modifier(db, user_id, data, admin)
    db.commit()
    db.refresh(user)
    return user
