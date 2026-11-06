from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import ModeLivraison, StatutLivraison
from app.core.database import get_db
from app.core.deps import require_role
from app.models.utilisateur import Utilisateur
from app.schemas.commande import CommandeDetail
from app.schemas.common import Page
from app.schemas.livraison import LivraisonRead, LivraisonTournee, LivraisonUpsert
from app.services import commande_service, livraison_service

router = APIRouter(tags=["Livraisons"])
accueil_requis = require_role("accueil")


@router.put("/commandes/{commande_id}/livraison", response_model=LivraisonRead,
            summary="35 · Planifier / replanifier la livraison (upsert, RG18)")
def planifier_livraison(commande_id: int, data: LivraisonUpsert, response: Response,
                        db: Session = Depends(get_db), _: Utilisateur = Depends(accueil_requis)):
    """201 si la livraison vient d'être créée, 200 si elle a été modifiée."""
    livraison, creee = livraison_service.planifier(db, commande_id, data)
    db.commit()
    db.refresh(livraison)
    response.status_code = status.HTTP_201_CREATED if creee else status.HTTP_200_OK
    return livraison


@router.get("/commandes/{commande_id}/livraison", response_model=LivraisonRead,
            summary="36 · Livraison d'une commande")
def obtenir_livraison(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(accueil_requis)):
    return livraison_service.obtenir_pour_commande(db, commande_id)


@router.post("/commandes/{commande_id}/livraison/confirmer", response_model=CommandeDetail,
             summary="37 · Confirmer la remise au client (RG19, RG20)")
def confirmer_livraison(
    commande_id: int,
    autoriser_solde_impaye: bool = Query(False, description="Livrer malgré un solde > 0 (mention dans l'historique)"),
    commentaire: str | None = Query(None),
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(accueil_requis),
):
    livraison_service.confirmer(db, commande_id, autoriser_solde_impaye, commentaire, user)
    db.commit()
    return commande_service.obtenir(db, commande_id)


@router.get("/livraisons", response_model=Page[LivraisonTournee], summary="38 · Liste de tournée")
def lister_livraisons(
    date_prevue: date | None = Query(None, description="ex. aujourd'hui pour la tournée du jour"),
    statut: StatutLivraison | None = Query(None),
    mode: ModeLivraison | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(accueil_requis),
):
    items, total = livraison_service.lister(db, date_prevue=date_prevue, statut=statut, mode=mode,
                                            limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
