"""Statistiques pour le patron (section 5.2 du guide).

Définitions :
- Chiffre d'affaires : Σ montant_total des commandes NON annulées, par date_commande.
- Encaissé           : Σ montant des paiements, par date_paiement.
- Reste à encaisser  : Σ (total − payé) des commandes non annulées.
"""
from datetime import date, timedelta

from sqlalchemy import Date, cast, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.constantes import STATUTS_COMMANDE
from app.core.exceptions import RegleMetierError
from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, LigneCommande
from app.models.livraison import Livraison
from app.models.paiement import Paiement
from app.services.commande_service import condition_en_retard

NON_ANNULEE = Commande.statut != "annulee"


def _debut_du_mois(jour: date) -> date:
    return date(jour.year, jour.month, 1)


def _verifier_bornes(date_debut: date | None, date_fin: date | None) -> None:
    if date_debut and date_fin and date_debut > date_fin:
        raise RegleMetierError("date_debut doit être antérieure ou égale à date_fin")


def tableau_de_bord(db: Session) -> dict:
    aujourd_hui = date.today()
    debut = _debut_du_mois(aujourd_hui)

    ca, nb_mois = db.execute(
        select(func.coalesce(func.sum(Commande.montant_total), 0), func.count(Commande.id))
        .where(NON_ANNULEE, Commande.date_commande.between(debut, aujourd_hui))
    ).one()
    encaisse = db.scalar(select(func.coalesce(func.sum(Paiement.montant), 0))
                         .where(Paiement.date_paiement.between(debut, aujourd_hui)))
    reste = db.scalar(select(func.coalesce(func.sum(Commande.montant_total - Commande.montant_paye), 0))
                      .where(NON_ANNULEE))

    # Les 8 statuts, même à 0 : on initialise puis on remplit avec le GROUP BY
    par_statut = {s: 0 for s in STATUTS_COMMANDE}
    for statut, nb in db.execute(select(Commande.statut, func.count(Commande.id)).group_by(Commande.statut)):
        par_statut[statut] = nb

    return {
        "periode_debut": debut,
        "periode_fin": aujourd_hui,
        "chiffre_affaires_mois": ca,
        "encaisse_mois": encaisse,
        "nombre_commandes_mois": nb_mois,
        "reste_a_encaisser": reste,
        "commandes_par_statut": par_statut,
        "commandes_en_retard": db.scalar(select(func.count(Commande.id)).where(condition_en_retard())),
        "pretes_a_livrer": par_statut["terminee"],
        "livraisons_du_jour": db.scalar(select(func.count(Livraison.id)).where(
            Livraison.date_prevue == aujourd_hui, Livraison.statut == "planifiee")),
        "nombre_clients": db.scalar(select(func.count(Client.id))),
    }


def chiffre_affaires(db: Session, date_debut: date | None, date_fin: date | None, granularite: str) -> dict:
    aujourd_hui = date.today()
    date_debut = date_debut or _debut_du_mois(aujourd_hui)
    date_fin = date_fin or aujourd_hui
    _verifier_bornes(date_debut, date_fin)

    if granularite == "mois":
        # date_trunc('month', ...) est une fonction PostgreSQL : 2026-11-17 -> 2026-11-01
        p_cmd = cast(func.date_trunc("month", Commande.date_commande), Date)
        p_pay = cast(func.date_trunc("month", Paiement.date_paiement), Date)
        fmt = lambda d: d.strftime("%Y-%m")  # noqa: E731
    else:
        p_cmd, p_pay = Commande.date_commande, Paiement.date_paiement
        fmt = lambda d: d.isoformat()  # noqa: E731

    ca = dict(db.execute(
        select(p_cmd, func.sum(Commande.montant_total))
        .where(NON_ANNULEE, Commande.date_commande.between(date_debut, date_fin)).group_by(p_cmd)
    ).all())
    enc = dict(db.execute(
        select(p_pay, func.sum(Paiement.montant))
        .where(Paiement.date_paiement.between(date_debut, date_fin)).group_by(p_pay)
    ).all())

    # Toutes les périodes de l'intervalle (même vides) pour que le graphique soit continu
    periodes, courant = [], (_debut_du_mois(date_debut) if granularite == "mois" else date_debut)
    while courant <= date_fin:
        periodes.append({"periode": fmt(courant), "chiffre_affaires": int(ca.get(courant, 0) or 0),
                         "encaisse": int(enc.get(courant, 0) or 0)})
        if granularite == "mois":
            courant = date(courant.year + (courant.month == 12), courant.month % 12 + 1, 1)
        else:
            courant += timedelta(days=1)

    return {
        "date_debut": date_debut, "date_fin": date_fin, "granularite": granularite,
        "total_chiffre_affaires": sum(p["chiffre_affaires"] for p in periodes),
        "total_encaisse": sum(p["encaisse"] for p in periodes),
        "periodes": periodes,
    }


def par_type_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict]:
    _verifier_bornes(date_debut, date_fin)
    quantite = func.sum(LigneCommande.quantite)
    montant = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire)
    stmt = (select(TypeVetement.id, TypeVetement.nom, quantite, montant)
            .join(LigneCommande, LigneCommande.type_vetement_id == TypeVetement.id)
            .join(Commande, Commande.id == LigneCommande.commande_id)
            .where(NON_ANNULEE))
    if date_debut:
        stmt = stmt.where(Commande.date_commande >= date_debut)
    if date_fin:
        stmt = stmt.where(Commande.date_commande <= date_fin)
    stmt = stmt.group_by(TypeVetement.id, TypeVetement.nom).order_by(desc(montant), TypeVetement.nom)
    return [{"type_vetement_id": i, "nom": n, "quantite": q, "montant": m} for i, n, q, m in db.execute(stmt)]


def top_clients(db: Session, limite: int) -> list[dict]:
    total = func.sum(Commande.montant_total)
    paye = func.sum(Commande.montant_paye)
    stmt = (select(Client.id, Client.nom, Client.prenom, Client.telephone, func.count(Commande.id), total, paye)
            .join(Commande, Commande.client_id == Client.id)
            .where(NON_ANNULEE)
            .group_by(Client.id)
            .order_by(desc(total), Client.nom).limit(limite))
    return [{"client_id": i, "nom": n, "prenom": p, "telephone": t, "nombre_commandes": nb,
             "montant_total": mt, "montant_paye": mp, "solde": mt - mp}
            for i, n, p, t, nb, mt, mp in db.execute(stmt)]


def impayes(db: Session, limit: int, offset: int) -> tuple[list[Commande], int]:
    """Commandes non annulées avec un solde > 0, les plus urgentes d'abord (date prévue croissante)."""
    cond = (NON_ANNULEE, Commande.montant_total > Commande.montant_paye)
    total = db.scalar(select(func.count(Commande.id)).where(*cond))
    stmt = (select(Commande).where(*cond).options(selectinload(Commande.client))
            .order_by(Commande.date_livraison_prevue, Commande.id).limit(limit).offset(offset))
    return list(db.scalars(stmt).all()), total
