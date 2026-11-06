from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.utilisateur import Utilisateur
from app.schemas.mesure import MesureCreate, MesureRead, MesureUpdate
from app.services import mesure_service

router = APIRouter(tags=["Mesures"])
tailleur_requis = require_role("tailleur")  # écriture : tailleur (et admin)


@router.post("/clients/{client_id}/mesures", response_model=MesureRead, status_code=status.HTTP_201_CREATED,
             summary="18 · Prendre les mesures d'un client (tailleur)")
def creer_mesure(client_id: int, data: MesureCreate, db: Session = Depends(get_db),
                 user: Utilisateur = Depends(tailleur_requis)):
    mesure = mesure_service.creer(db, client_id, data, user)
    db.commit()
    db.refresh(mesure)
    return mesure


@router.get("/clients/{client_id}/mesures", response_model=list[MesureRead],
            summary="19 · Historique des mesures d'un client")
def historique_mesures(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return mesure_service.lister(db, client_id)


# ⚠ Déclarée AVANT toute route du type /clients/{id}/mesures/{mesure_id}
#   pour que « derniere » ne soit jamais pris pour un identifiant.
@router.get("/clients/{client_id}/mesures/derniere", response_model=MesureRead,
            summary="20 · Dernières mesures d'un client (RG3)")
def derniere_mesure(client_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return mesure_service.derniere(db, client_id)


@router.get("/mesures/{mesure_id}", response_model=MesureRead, summary="21 · Détail d'une prise de mesures")
def obtenir_mesure(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return mesure_service.obtenir(db, mesure_id)


@router.patch("/mesures/{mesure_id}", response_model=MesureRead, summary="22 · Corriger des mesures (tailleur)")
def modifier_mesure(mesure_id: int, data: MesureUpdate, db: Session = Depends(get_db),
                    _: Utilisateur = Depends(tailleur_requis)):
    mesure = mesure_service.modifier(db, mesure_id, data)
    db.commit()
    db.refresh(mesure)
    return mesure


@router.delete("/mesures/{mesure_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="23 · Supprimer une prise de mesures (tailleur, RG4)")
def supprimer_mesure(mesure_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(tailleur_requis)):
    mesure_service.supprimer(db, mesure_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
