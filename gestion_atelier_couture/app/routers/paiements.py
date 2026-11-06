from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.utilisateur import Utilisateur
from app.schemas.paiement import PaiementCreate, PaiementRead
from app.services import paiement_service

router = APIRouter(tags=["Paiements"])
accueil_requis = require_role("accueil")


@router.post("/commandes/{commande_id}/paiements", response_model=PaiementRead,
             status_code=status.HTTP_201_CREATED, summary="32 · Encaisser un acompte / un solde (RG16)")
def encaisser(commande_id: int, data: PaiementCreate, db: Session = Depends(get_db),
              user: Utilisateur = Depends(accueil_requis)):
    paiement = paiement_service.encaisser(db, commande_id, data, user)
    db.commit()
    db.refresh(paiement)
    return paiement


@router.get("/commandes/{commande_id}/paiements", response_model=list[PaiementRead],
            summary="33 · Paiements d'une commande (ordre de saisie)")
def lister_paiements(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(accueil_requis)):
    return paiement_service.lister(db, commande_id)


@router.delete("/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="34 · Supprimer un paiement (admin, RG17)")
def supprimer_paiement(paiement_id: int, db: Session = Depends(get_db),
                       _: Utilisateur = Depends(require_role("admin"))):
    paiement_service.supprimer(db, paiement_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
