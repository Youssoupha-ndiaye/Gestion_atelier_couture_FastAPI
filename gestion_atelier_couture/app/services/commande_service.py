"""Service commandes : le cœur du métier (RG5 à RG15).

Ordre de lecture conseillé :
1. recalculer_montants   (RG7)
2. creer                 (RG5, RG6, RG8, RG9, RG15)
3. obtenir / lister      (RG11)
4. modifier              (RG7, RG8, RG9, RG12)
5. changer_statut        (RG12 à RG15, section 5.1 du guide)
6. ajouter / supprimer une ligne (RG10)
"""
from datetime import date, timedelta

from sqlalchemy import and_, func, not_, select
from sqlalchemy.orm import Session, selectinload

from app.core.constantes import STATUTS_FINAUX, TRANSITIONS
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, RegleMetierError
from app.models.catalogue import TypeVetement
from app.models.commande import Commande, HistoriqueStatut, LigneCommande
from app.models.mesure import Mesure
from app.models.utilisateur import Utilisateur
from app.schemas.commande import CommandeCreate, CommandeUpdate, LigneCreate
from app.services import client_service, mesure_service


def fcfa(montant: int) -> str:
    """25000 -> « 25 000 FCFA »."""
    return f"{montant:,}".replace(",", " ") + " FCFA"


# ======================================================================
# Outils internes
# ======================================================================
def condition_en_retard():
    """RG11 en SQL : date prévue < aujourd'hui ET statut ∉ {livree, annulee}."""
    return and_(Commande.date_livraison_prevue < date.today(), Commande.statut.not_in(STATUTS_FINAUX))


def verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable."""
    if commande.statut in STATUTS_FINAUX:
        raise ConflictError(f"Commande {commande.numero} {commande.statut} : elle n'est plus modifiable")


def ajouter_historique(commande: Commande, ancien: str | None, nouveau: str,
                       commentaire: str | None, user: Utilisateur | None) -> None:
    """RG15 : chaque changement de statut laisse une trace."""
    commande.historique.append(HistoriqueStatut(
        ancien_statut=ancien, nouveau_statut=nouveau, commentaire=commentaire,
        utilisateur_id=user.id if user else None,
    ))


def recalculer_montants(commande: Commande) -> None:
    """RG7 : total = Σ(qté × pu) − remise ; payé = Σ paiements. À appeler après CHAQUE modification."""
    somme_lignes = sum(l.quantite * l.prix_unitaire for l in commande.lignes)
    remise = commande.remise or 0
    if remise > somme_lignes:
        raise RegleMetierError(
            f"La remise ({fcfa(remise)}) dépasse le montant des lignes ({fcfa(somme_lignes)})")
    total = somme_lignes - remise
    paye = sum(p.montant for p in commande.paiements)
    if total < paye:
        raise ConflictError(
            f"Le nouveau total ({fcfa(total)}) serait inférieur au montant déjà payé ({fcfa(paye)})")
    commande.montant_total = total
    commande.montant_paye = paye


def _resoudre_mesure(db: Session, client_id: int, mesure_id: int | None) -> int | None:
    """RG9 : la mesure doit appartenir au client ; absente -> dernières mesures du client (ou rien)."""
    if mesure_id is None:
        derniere = mesure_service.derniere_ou_none(db, client_id)
        return derniere.id if derniere else None
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise NotFoundError(f"Mesure {mesure_id} introuvable")
    if mesure.client_id != client_id:
        raise RegleMetierError(f"La mesure {mesure_id} n'appartient pas à ce client")
    return mesure.id


def _construire_ligne(db: Session, data: LigneCreate) -> tuple[LigneCommande, TypeVetement]:
    """RG6 : prestation active obligatoire ; prix_unitaire par défaut = prix_base (copié)."""
    tv = db.get(TypeVetement, data.type_vetement_id)
    if tv is None:
        raise NotFoundError(f"Prestation {data.type_vetement_id} introuvable")
    if not tv.actif:
        raise RegleMetierError(f"La prestation « {tv.nom} » est inactive : elle ne peut plus être commandée")
    prix = data.prix_unitaire if data.prix_unitaire is not None else tv.prix_base
    ligne = LigneCommande(type_vetement_id=tv.id, description=data.description,
                          quantite=data.quantite, prix_unitaire=prix)
    ligne.type_vetement = tv
    return ligne, tv


# ======================================================================
# Création
# ======================================================================
def creer(db: Session, data: CommandeCreate, user: Utilisateur) -> Commande:
    client = client_service.obtenir(db, data.client_id)
    mesure_id = _resoudre_mesure(db, client.id, data.mesure_id)

    lignes, types = [], []
    for l in data.lignes:
        ligne, tv = _construire_ligne(db, l)
        lignes.append(ligne)
        types.append(tv)

    aujourd_hui = date.today()
    # RG8 : défaut = date_commande + plus grand délai ; jamais avant la date de commande
    date_prevue = data.date_livraison_prevue or aujourd_hui + timedelta(days=max(t.delai_jours for t in types))
    if date_prevue < aujourd_hui:
        raise RegleMetierError("La date de livraison prévue ne peut pas être antérieure à la date de commande")

    commande = Commande(
        client=client, mesure_id=mesure_id, statut="en_attente",
        date_commande=aujourd_hui, date_livraison_prevue=date_prevue,
        remise=data.remise, notes=data.notes, cree_par_id=user.id,
    )
    commande.lignes = lignes
    commande.paiements = []
    recalculer_montants(commande)  # RG7 (remise > Σ lignes -> 422)

    db.add(commande)
    db.flush()  # envoie l'INSERT sans valider : on obtient l'id
    commande.numero = f"CMD-{aujourd_hui.year}-{commande.id:05d}"  # RG5
    ajouter_historique(commande, None, "en_attente", "Création de la commande", user)  # RG15
    db.flush()
    return commande


# ======================================================================
# Lecture
# ======================================================================
def _options_detail():
    return (
        selectinload(Commande.client),
        selectinload(Commande.lignes).selectinload(LigneCommande.type_vetement),
        selectinload(Commande.paiements),
        selectinload(Commande.livraison),
    )


def obtenir(db: Session, commande_id: int) -> Commande:
    stmt = select(Commande).where(Commande.id == commande_id).options(*_options_detail())
    commande = db.scalar(stmt)
    if commande is None:
        raise NotFoundError(f"Commande {commande_id} introuvable")
    return commande


def lister(db: Session, *, statut: str | None = None, client_id: int | None = None,
           en_retard: bool | None = None, date_min: date | None = None, date_max: date | None = None,
           numero: str | None = None, limit: int = 20, offset: int = 0) -> tuple[list[Commande], int]:
    stmt = select(Commande)
    if statut:
        stmt = stmt.where(Commande.statut == statut)
    if client_id is not None:
        stmt = stmt.where(Commande.client_id == client_id)
    if en_retard is True:
        stmt = stmt.where(condition_en_retard())
    elif en_retard is False:
        stmt = stmt.where(not_(condition_en_retard()))
    if date_min:
        stmt = stmt.where(Commande.date_commande >= date_min)
    if date_max:
        stmt = stmt.where(Commande.date_commande <= date_max)
    if numero:
        stmt = stmt.where(Commande.numero.ilike(f"%{numero.strip()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = (stmt.options(selectinload(Commande.client))
            .order_by(Commande.date_commande.desc(), Commande.id.desc()).limit(limit).offset(offset))
    return list(db.scalars(stmt).all()), total


def historique(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    obtenir(db, commande_id)
    stmt = (select(HistoriqueStatut).where(HistoriqueStatut.commande_id == commande_id)
            .options(selectinload(HistoriqueStatut.utilisateur))
            .order_by(HistoriqueStatut.date_changement, HistoriqueStatut.id))
    return list(db.scalars(stmt).all())


# ======================================================================
# Modification
# ======================================================================
def modifier(db: Session, commande_id: int, data: CommandeUpdate) -> Commande:
    commande = obtenir(db, commande_id)
    verifier_modifiable(commande)  # RG12
    changements = data.model_dump(exclude_unset=True)

    if "mesure_id" in changements:
        mid = changements["mesure_id"]
        commande.mesure_id = _resoudre_mesure(db, commande.client_id, mid) if mid is not None else None
    if "date_livraison_prevue" in changements:
        if changements["date_livraison_prevue"] < commande.date_commande:  # RG8
            raise RegleMetierError("La date de livraison prévue ne peut pas être antérieure à la date de commande")
        commande.date_livraison_prevue = changements["date_livraison_prevue"]
    if "remise" in changements:
        commande.remise = changements["remise"]
    if "notes" in changements:
        commande.notes = changements["notes"]

    recalculer_montants(commande)  # RG7
    db.flush()
    return commande


def changer_statut(db: Session, commande_id: int, nouveau: str, commentaire: str | None,
                   user: Utilisateur) -> Commande:
    """Workflow de production. L'ORDRE des contrôles donne le bon code HTTP."""
    commande = obtenir(db, commande_id)
    actuel = commande.statut

    if actuel in STATUTS_FINAUX:  # RG12
        raise ConflictError(f"Commande {actuel} : elle n'est plus modifiable")
    if nouveau == actuel:  # RG13
        raise ConflictError(f"La commande est déjà au statut {nouveau}")
    if nouveau == "livree":  # RG13
        raise ConflictError("Le statut livree résulte de la confirmation de livraison "
                            "(POST /commandes/{id}/livraison/confirmer)")
    possibles = [s for s in TRANSITIONS[actuel] if s != "livree"]
    if nouveau not in possibles:
        raise ConflictError(f"Transition interdite : {actuel} → {nouveau}. "
                            f"Statuts possibles : {', '.join(sorted(possibles))}")
    if nouveau == "annulee":  # RG14
        if user.role == "tailleur":
            raise ForbiddenError("Le tailleur ne peut pas annuler une commande")
        if commande.montant_paye > 0 and not (commentaire and commentaire.strip()):
            raise RegleMetierError(
                f"Commentaire obligatoire : précisez le sort de l'acompte de {fcfa(commande.montant_paye)}")

    ajouter_historique(commande, actuel, nouveau, commentaire, user)  # RG15
    commande.statut = nouveau
    db.flush()
    return commande


def _verifier_lignes_modifiables(commande: Commande) -> None:
    verifier_modifiable(commande)  # RG12
    if commande.statut != "en_attente":  # RG10
        raise ConflictError(f"Les lignes ne sont modifiables qu'au statut en_attente "
                            f"(statut actuel : {commande.statut})")


def ajouter_ligne(db: Session, commande_id: int, data: LigneCreate) -> Commande:
    commande = obtenir(db, commande_id)
    _verifier_lignes_modifiables(commande)
    ligne, _ = _construire_ligne(db, data)
    commande.lignes.append(ligne)
    recalculer_montants(commande)
    db.flush()
    return commande


def supprimer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    commande = obtenir(db, commande_id)
    _verifier_lignes_modifiables(commande)
    ligne = next((l for l in commande.lignes if l.id == ligne_id), None)
    if ligne is None:
        raise NotFoundError(f"Ligne {ligne_id} introuvable dans la commande {commande.numero}")
    if len(commande.lignes) == 1:  # RG10 : toujours au moins une ligne
        raise ConflictError("Une commande doit garder au moins une ligne")
    commande.lignes.remove(ligne)  # delete-orphan -> DELETE en base
    recalculer_montants(commande)  # peut lever 409 si total < payé (rien n'est alors enregistré)
    db.flush()
    return commande


# ======================================================================
# Pour les clients (routes 12 et 13)
# ======================================================================
def resume_client(db: Session, client_id: int) -> dict:
    client = client_service.obtenir(db, client_id)
    non_annulees = and_(Commande.client_id == client_id, Commande.statut != "annulee")
    nb, total, paye, derniere = db.execute(
        select(func.count(Commande.id), func.coalesce(func.sum(Commande.montant_total), 0),
               func.coalesce(func.sum(Commande.montant_paye), 0), func.max(Commande.date_commande))
        .where(non_annulees)
    ).one()
    en_cours = db.scalar(select(func.count(Commande.id)).where(non_annulees, Commande.statut != "livree"))
    derniere_mesure = db.scalar(select(func.max(Mesure.date_prise)).where(Mesure.client_id == client_id))
    return {
        "client": client, "nombre_commandes": nb, "commandes_en_cours": en_cours,
        "montant_total": total, "montant_paye": paye, "solde": total - paye,
        "derniere_commande": derniere, "derniere_mesure": derniere_mesure,
    }
