from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import Genre
from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.utilisateur import Utilisateur
from app.schemas.client import ClientCreate, ClientRead, ClientResume, ClientUpdate
from app.schemas.commande import CommandeListItem
from app.schemas.common import Page
from app.services import client_service, commande_service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED,
             summary="7 · Créer un client (RG1)")
def creer_client(data: ClientCreate, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    client = client_service.creer(db, data)
    db.commit()
    db.refresh(client)
    return client


@router.get("", response_model=Page[ClientRead], summary="8 · Rechercher / lister les clients")
def lister_clients(
    q: str | None = Query(None, min_length=2, description="Recherche sur nom, prénom ou téléphone (≥ 2 caractères)"),
    genre: Genre | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    items, total = client_service.lister(db, q, genre, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{client_id}", response_model=ClientRead, summary="9 · Détail d'un client")
def obtenir_client(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return client_service.obtenir(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead, summary="10 · Modifier un client")
def modifier_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db),
                    _: Utilisateur = Depends(get_current_user)):
    client = client_service.modifier(db, client_id, data)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="11 · Supprimer un client (admin, RG4)")
def supprimer_client(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(require_role("admin"))):
    client_service.supprimer(db, client_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/commandes", response_model=Page[CommandeListItem],
            summary="12 · Commandes d'un client")
def commandes_du_client(client_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                        db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    client_service.obtenir(db, client_id)  # 404 si inconnu
    items, total = commande_service.lister(db, client_id=client_id, limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{client_id}/resume", response_model=ClientResume,
            summary="13 · Résumé financier d'un client (hors commandes annulées)")
def resume_client(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return commande_service.resume_client(db, client_id)
