"""Service mesures : RG2 (au moins une), RG3 (historique / dernière), RG4 (suppression)."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constantes import CHAMPS_MESURES
from app.core.exceptions import ConflictError, NotFoundError, RegleMetierError
from app.models.commande import Commande
from app.models.mesure import Mesure
from app.models.utilisateur import Utilisateur
from app.schemas.mesure import MesureCreate, MesureUpdate
from app.services import client_service


def creer(db: Session, client_id: int, data: MesureCreate, user: Utilisateur) -> Mesure:
    client_service.obtenir(db, client_id)  # 404 si le client n'existe pas
    valeurs = data.model_dump()
    valeurs["date_prise"] = valeurs["date_prise"] or date.today()
    mesure = Mesure(client_id=client_id, prise_par_id=user.id, **valeurs)  # prise_par = tailleur connecté
    db.add(mesure)
    db.flush()
    return mesure


def lister(db: Session, client_id: int) -> list[Mesure]:
    """RG3 : toutes les prises sont gardées, la plus récente en premier."""
    client_service.obtenir(db, client_id)
    stmt = select(Mesure).where(Mesure.client_id == client_id).order_by(Mesure.date_prise.desc(), Mesure.id.desc())
    return list(db.scalars(stmt).all())


def derniere_ou_none(db: Session, client_id: int) -> Mesure | None:
    """RG3 : « dernière » = date_prise la plus récente, puis id le plus grand en cas d'égalité."""
    stmt = (select(Mesure).where(Mesure.client_id == client_id)
            .order_by(Mesure.date_prise.desc(), Mesure.id.desc()).limit(1))
    return db.scalar(stmt)


def derniere(db: Session, client_id: int) -> Mesure:
    client_service.obtenir(db, client_id)
    mesure = derniere_ou_none(db, client_id)
    if mesure is None:
        raise NotFoundError("Aucune mesure enregistrée pour ce client")
    return mesure


def obtenir(db: Session, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise NotFoundError(f"Mesure {mesure_id} introuvable")
    return mesure


def modifier(db: Session, mesure_id: int, data: MesureUpdate) -> Mesure:
    mesure = obtenir(db, mesure_id)
    changements = data.model_dump(exclude_unset=True)
    # RG2 après fusion : on simule le résultat final avant de l'appliquer
    apres = {c: changements.get(c, getattr(mesure, c)) for c in CHAMPS_MESURES}
    if all(v is None for v in apres.values()):
        raise RegleMetierError("Au moins une mesure doit rester renseignée")
    for champ, valeur in changements.items():
        setattr(mesure, champ, valeur)
    db.flush()
    return mesure


def supprimer(db: Session, mesure_id: int) -> None:
    mesure = obtenir(db, mesure_id)
    # RG4 : une mesure utilisée par une commande n'est pas supprimable
    nb = db.scalar(select(func.count()).select_from(Commande).where(Commande.mesure_id == mesure.id))
    if nb:
        raise ConflictError(f"Suppression impossible : cette mesure est utilisée par {nb} commande(s)")
    db.delete(mesure)
    db.flush()
