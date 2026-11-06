from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.constantes import StatutCommande
from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.utilisateur import Utilisateur
from app.schemas.commande import (CommandeCreate, CommandeDetail, CommandeListItem, CommandeUpdate,
                                  HistoriqueRead, LigneCreate, StatutUpdate)
from app.schemas.common import Page
from app.services import commande_service

router = APIRouter(prefix="/commandes", tags=["Commandes"])
accueil_requis = require_role("accueil")  # écriture : accueil (et admin)


@router.post("", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED,
             summary="24 · Créer une commande (RG5 à RG9, RG15)")
def creer_commande(data: CommandeCreate, db: Session = Depends(get_db), user: Utilisateur = Depends(accueil_requis)):
    commande = commande_service.creer(db, data, user)
    db.commit()
    return commande_service.obtenir(db, commande.id)


@router.get("", response_model=Page[CommandeListItem], summary="25 · Lister / filtrer les commandes")
def lister_commandes(
    statut: StatutCommande | None = Query(None),
    client_id: int | None = Query(None),
    en_retard: bool | None = Query(None, description="true : uniquement les commandes en retard (RG11)"),
    date_min: date | None = Query(None, description="date_commande ≥"),
    date_max: date | None = Query(None, description="date_commande ≤"),
    numero: str | None = Query(None, description="Recherche partielle, ex. CMD-2026"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Utilisateur = Depends(get_current_user),
):
    items, total = commande_service.lister(db, statut=statut, client_id=client_id, en_retard=en_retard,
                                           date_min=date_min, date_max=date_max, numero=numero,
                                           limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{commande_id}", response_model=CommandeDetail, summary="26 · Détail d'une commande")
def obtenir_commande(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return commande_service.obtenir(db, commande_id)


@router.patch("/{commande_id}", response_model=CommandeDetail,
              summary="27 · Modifier remise / date prévue / mesure / notes (RG7, RG8, RG9, RG12)")
def modifier_commande(commande_id: int, data: CommandeUpdate, db: Session = Depends(get_db),
                      _: Utilisateur = Depends(accueil_requis)):
    commande_service.modifier(db, commande_id, data)
    db.commit()
    return commande_service.obtenir(db, commande_id)


@router.patch("/{commande_id}/statut", response_model=CommandeDetail,
              summary="28 · Faire avancer la production / annuler (RG12 à RG15)")
def changer_statut(commande_id: int, data: StatutUpdate, db: Session = Depends(get_db),
                   user: Utilisateur = Depends(get_current_user)):
    """Ouvert à tous les rôles ; le service refuse le tailleur qui annule (403)."""
    commande_service.changer_statut(db, commande_id, data.statut, data.commentaire, user)
    db.commit()
    return commande_service.obtenir(db, commande_id)


@router.get("/{commande_id}/historique", response_model=list[HistoriqueRead],
            summary="29 · Historique des statuts")
def historique_commande(commande_id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(get_current_user)):
    return commande_service.historique(db, commande_id)


@router.post("/{commande_id}/lignes", response_model=CommandeDetail, status_code=status.HTTP_201_CREATED,
             summary="30 · Ajouter une ligne (en_attente seulement, RG10)")
def ajouter_ligne(commande_id: int, data: LigneCreate, db: Session = Depends(get_db),
                  _: Utilisateur = Depends(accueil_requis)):
    commande_service.ajouter_ligne(db, commande_id, data)
    db.commit()
    return commande_service.obtenir(db, commande_id)


@router.delete("/{commande_id}/lignes/{ligne_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="31 · Supprimer une ligne (en_attente, ≥ 1 ligne restante, RG10)")
def supprimer_ligne(commande_id: int, ligne_id: int, db: Session = Depends(get_db),
                    _: Utilisateur = Depends(accueil_requis)):
    commande_service.supprimer_ligne(db, commande_id, ligne_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
