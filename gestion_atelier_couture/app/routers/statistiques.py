from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.utilisateur import Utilisateur
from app.schemas.commande import CommandeListItem
from app.schemas.common import Page
from app.schemas.statistiques import ChiffreAffaires, StatTypeVetement, TableauDeBord, TopClient
from app.services import statistiques_service

# Toutes les statistiques sont réservées au patron (admin)
router = APIRouter(prefix="/statistiques", tags=["Statistiques"])
admin_requis = require_role("admin")


@router.get("/tableau-de-bord", response_model=TableauDeBord, summary="39 · Tableau de bord du mois courant")
def tableau_de_bord(db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    return statistiques_service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=ChiffreAffaires,
            summary="40 · Chiffre d'affaires et encaissements par jour ou par mois")
def chiffre_affaires(
    date_debut: date | None = Query(None, description="Défaut : 1er jour du mois courant"),
    date_fin: date | None = Query(None, description="Défaut : aujourd'hui"),
    granularite: Literal["jour", "mois"] = Query("jour"),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(admin_requis),
):
    return statistiques_service.chiffre_affaires(db, date_debut, date_fin, granularite)


@router.get("/types-vetement", response_model=list[StatTypeVetement],
            summary="41 · Ventes par prestation (hors annulées)")
def par_type_vetement(date_debut: date | None = Query(None), date_fin: date | None = Query(None),
                      db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    return statistiques_service.par_type_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient], summary="42 · Meilleurs clients")
def top_clients(limite: int = Query(10, ge=1, le=100), db: Session = Depends(get_db),
                _: Utilisateur = Depends(admin_requis)):
    return statistiques_service.top_clients(db, limite)


@router.get("/impayes", response_model=Page[CommandeListItem],
            summary="43 · Commandes avec un solde impayé (date prévue croissante)")
def impayes(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
            db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    items, total = statistiques_service.impayes(db, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
