"""Service utilisateurs (gestion du personnel, réservé à l'admin)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate


def _verifier_email_libre(db: Session, email: str, exclure_id: int | None = None) -> None:
    stmt = select(Utilisateur.id).where(Utilisateur.email == email)
    if exclure_id is not None:
        stmt = stmt.where(Utilisateur.id != exclure_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"Un utilisateur avec l'email {email} existe déjà")


def creer(db: Session, data: UtilisateurCreate) -> Utilisateur:
    _verifier_email_libre(db, data.email)
    user = Utilisateur(
        email=data.email,
        nom_complet=data.nom_complet,
        mot_de_passe_hash=hash_password(data.mot_de_passe),  # RG21
        role=data.role,
        actif=True,
    )
    db.add(user)
    db.flush()
    return user


def lister(db: Session, limit: int, offset: int) -> tuple[list[Utilisateur], int]:
    total = db.scalar(select(func.count()).select_from(Utilisateur))
    stmt = select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id).limit(limit).offset(offset)
    return list(db.scalars(stmt).all()), total


def obtenir(db: Session, user_id: int) -> Utilisateur:
    user = db.get(Utilisateur, user_id)
    if user is None:
        raise NotFoundError(f"Utilisateur {user_id} introuvable")
    return user


def modifier(db: Session, user_id: int, data: UtilisateurUpdate, acteur: Utilisateur) -> Utilisateur:
    user = obtenir(db, user_id)
    changements = data.model_dump(exclude_unset=True)  # uniquement les champs envoyés

    # RG24 : l'admin connecté ne peut ni se désactiver ni retirer son propre rôle admin
    if user.id == acteur.id:
        if changements.get("actif") is False:
            raise ConflictError("Vous ne pouvez pas désactiver votre propre compte")
        if "role" in changements and changements["role"] != "admin":
            raise ConflictError("Vous ne pouvez pas retirer votre propre rôle admin")

    if "email" in changements:
        _verifier_email_libre(db, changements["email"], exclure_id=user.id)
    if "mot_de_passe" in changements:
        user.mot_de_passe_hash = hash_password(changements.pop("mot_de_passe"))

    for champ, valeur in changements.items():
        setattr(user, champ, valeur)
    db.flush()
    return user
