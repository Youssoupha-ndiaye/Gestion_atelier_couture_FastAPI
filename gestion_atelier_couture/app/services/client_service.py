"""Service clients : RG1 (téléphone unique) et RG4 (suppression)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.models.commande import Commande
from app.schemas.client import ClientCreate, ClientUpdate


def _verifier_telephone_libre(db: Session, telephone: str, exclure_id: int | None = None) -> None:
    """RG1 : unicité. En PATCH, on exclut le client lui-même (garder son numéro n'est pas un doublon)."""
    stmt = select(Client.id).where(Client.telephone == telephone)
    if exclure_id is not None:
        stmt = stmt.where(Client.id != exclure_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"Le numéro {telephone} est déjà utilisé par un autre client")


def creer(db: Session, data: ClientCreate) -> Client:
    _verifier_telephone_libre(db, data.telephone)  # déjà normalisé par le schéma
    client = Client(**data.model_dump())
    db.add(client)
    db.flush()
    return client


def lister(db: Session, q: str | None, genre: str | None, limit: int, offset: int) -> tuple[list[Client], int]:
    stmt = select(Client)
    if q:
        motif = f"%{q.strip()}%"
        stmt = stmt.where(or_(Client.nom.ilike(motif), Client.prenom.ilike(motif), Client.telephone.ilike(motif)))
    if genre:
        stmt = stmt.where(Client.genre == genre)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(Client.nom, Client.prenom, Client.id).limit(limit).offset(offset)
    return list(db.scalars(stmt).all()), total


def obtenir(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise NotFoundError(f"Client {client_id} introuvable")
    return client


def modifier(db: Session, client_id: int, data: ClientUpdate) -> Client:
    client = obtenir(db, client_id)
    changements = data.model_dump(exclude_unset=True)  # « Les PATCH ne changent que les champs envoyés »
    if "telephone" in changements:
        _verifier_telephone_libre(db, changements["telephone"], exclure_id=client.id)
    for champ, valeur in changements.items():
        setattr(client, champ, valeur)
    db.flush()
    return client


def supprimer(db: Session, client_id: int) -> None:
    client = obtenir(db, client_id)
    # RG4 : un client qui a des commandes (même annulées) n'est pas supprimable
    nb = db.scalar(select(func.count()).select_from(Commande).where(Commande.client_id == client.id))
    if nb:
        raise ConflictError(f"Suppression impossible : ce client a {nb} commande(s)")
    db.delete(client)  # ses mesures partent avec (cascade)
    db.flush()
