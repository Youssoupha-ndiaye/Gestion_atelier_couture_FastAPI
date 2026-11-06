"""Service livraisons : RG18 (planifier), RG19 (conditions), RG20 (confirmation)."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, RegleMetierError
from app.models.commande import Commande
from app.models.livraison import Livraison
from app.models.utilisateur import Utilisateur
from app.schemas.livraison import LivraisonUpsert
from app.services import commande_service
from app.services.commande_service import ajouter_historique, fcfa


def planifier(db: Session, commande_id: int, data: LivraisonUpsert) -> tuple[Livraison, bool]:
    """PUT = upsert : crée la livraison si absente, sinon la modifie. Renvoie (livraison, creee)."""
    commande = commande_service.obtenir(db, commande_id)
    commande_service.verifier_modifiable(commande)  # RG12 : pas sur une commande livrée / annulée
    if data.date_prevue < commande.date_commande:
        raise RegleMetierError("La date de livraison ne peut pas être antérieure à la date de commande")

    valeurs = data.model_dump()
    if valeurs["mode"] == "retrait_atelier" and not valeurs.get("adresse"):
        valeurs["adresse"] = None

    creee = commande.livraison is None
    if creee:
        commande.livraison = Livraison(statut="planifiee", **valeurs)
    else:
        for champ, valeur in valeurs.items():
            setattr(commande.livraison, champ, valeur)

    commande.date_livraison_prevue = data.date_prevue  # RG18 : met à jour la date prévue de la commande
    db.flush()
    return commande.livraison, creee


def obtenir_pour_commande(db: Session, commande_id: int) -> Livraison:
    commande = commande_service.obtenir(db, commande_id)
    if commande.livraison is None:
        raise NotFoundError(f"Aucune livraison planifiée pour la commande {commande.numero}")
    return commande.livraison


def confirmer(db: Session, commande_id: int, autoriser_solde_impaye: bool, commentaire: str | None,
              user: Utilisateur) -> Commande:
    commande = commande_service.obtenir(db, commande_id)

    # RG19 : la commande doit être terminée...
    if commande.statut != "terminee":
        raise ConflictError(f"Seule une commande terminee peut être livrée (statut actuel : {commande.statut})")
    # ... et soldée, sauf autorisation explicite
    if commande.solde > 0 and not autoriser_solde_impaye:
        raise ConflictError(f"Solde impayé : {fcfa(commande.solde)}. "
                            f"Encaissez le solde ou utilisez autoriser_solde_impaye=true")

    aujourd_hui = date.today()
    # RG20 : sans planification -> livraison « retrait_atelier » créée automatiquement
    if commande.livraison is None:
        commande.livraison = Livraison(mode="retrait_atelier", date_prevue=aujourd_hui, statut="planifiee")

    commande.livraison.statut = "livree"
    commande.livraison.date_effective = aujourd_hui
    commande.date_livraison_reelle = aujourd_hui

    texte = commentaire.strip() if commentaire and commentaire.strip() else "Livraison confirmée"
    if commande.solde > 0:  # RG19 : mention dans l'historique
        texte += f" — livrée avec solde impayé de {fcfa(commande.solde)}"
    ajouter_historique(commande, commande.statut, "livree", texte, user)
    commande.statut = "livree"
    db.flush()
    return commande


def lister(db: Session, *, date_prevue: date | None, statut: str | None, mode: str | None,
           limit: int, offset: int) -> tuple[list[Livraison], int]:
    """Liste de tournée (triée par date prévue)."""
    stmt = select(Livraison)
    if date_prevue:
        stmt = stmt.where(Livraison.date_prevue == date_prevue)
    if statut:
        stmt = stmt.where(Livraison.statut == statut)
    if mode:
        stmt = stmt.where(Livraison.mode == mode)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = (stmt.options(selectinload(Livraison.commande).selectinload(Commande.client))
            .order_by(Livraison.date_prevue, Livraison.id).limit(limit).offset(offset))
    return list(db.scalars(stmt).all()), total
