from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.utilisateur import Utilisateur
from app.schemas.catalogue import TypeVetementCreate, TypeVetementRead, TypeVetementUpdate
from app.services import catalogue_service

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post("", response_model=TypeVetementRead, status_code=status.HTTP_201_CREATED,
             summary="14 · Ajouter une prestation (admin)")
def creer_prestation(data: TypeVetementCreate, db: Session = Depends(get_db),
                     _: Utilisateur = Depends(require_role("admin"))):
    tv = catalogue_service.creer(db, data)
    db.commit()
    db.refresh(tv)
    return tv


@router.get("", response_model=list[TypeVetementRead], summary="15 · Lister le catalogue")
def lister_prestations(actifs_seulement: bool = Query(True), db: Session = Depends(get_db),
                       _: Utilisateur = Depends(get_current_user)):
    return catalogue_service.lister(db, actifs_seulement)


@router.get("/{tv_id}", response_model=TypeVetementRead, summary="16 · Détail d'une prestation")
def obtenir_prestation(tv_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return catalogue_service.obtenir(db, tv_id)


@router.patch("/{tv_id}", response_model=TypeVetementRead,
              summary="17 · Modifier / désactiver une prestation (admin)")
def modifier_prestation(tv_id: int, data: TypeVetementUpdate, db: Session = Depends(get_db),
                        _: Utilisateur = Depends(require_role("admin"))):
    tv = catalogue_service.modifier(db, tv_id, data)
    db.commit()
    db.refresh(tv)
    return tv
