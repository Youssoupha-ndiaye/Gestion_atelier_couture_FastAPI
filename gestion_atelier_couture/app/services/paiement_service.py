"""Service paiements : RG16 (encaissement) et RG17 (suppression)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur
from app.schemas.paiement import PaiementCreate
from app.services import commande_service
from app.services.commande_service import fcfa


def encaisser(db: Session, commande_id: int, data: PaiementCreate, user: Utilisateur) -> Paiement:
    commande = commande_service.obtenir(db, commande_id)
    if commande.statut == "annulee":  # RG16
        raise ConflictError("Impossible d'encaisser un paiement sur une commande annulée")
    if commande.solde <= 0:
        raise ConflictError(f"La commande {commande.numero} est déjà entièrement payée")
    if data.montant > commande.solde:  # RG16 : jamais plus que ce qui reste dû
        raise ConflictError(f"Montant supérieur au solde restant ({fcfa(commande.solde)})")

    paiement = Paiement(
        montant=data.montant, mode=data.mode, reference=data.reference,
        date_paiement=data.date_paiement or date.today(), enregistre_par_id=user.id,
    )
    commande.paiements.append(paiement)
    commande_service.recalculer_montants(commande)  # montant_paye = Σ paiements
    db.flush()
    return paiement


def lister(db: Session, commande_id: int) -> list[Paiement]:
    commande_service.obtenir(db, commande_id)
    stmt = (select(Paiement).where(Paiement.commande_id == commande_id)
            .order_by(Paiement.created_at, Paiement.id))  # ordre de saisie
    return list(db.scalars(stmt).all())


def supprimer(db: Session, paiement_id: int) -> None:
    """RG17 : supprimer un paiement (erreur de saisie) puis recalculer montant_paye."""
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise NotFoundError(f"Paiement {paiement_id} introuvable")
    commande = commande_service.obtenir(db, paiement.commande_id)
    commande.paiements.remove(paiement)  # delete-orphan -> DELETE
    commande_service.recalculer_montants(commande)
    db.flush()
