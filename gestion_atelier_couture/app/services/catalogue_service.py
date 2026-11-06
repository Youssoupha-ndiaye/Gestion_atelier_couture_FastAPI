"""Service catalogue (prestations / types de vêtement)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalogue import TypeVetement
from app.schemas.catalogue import TypeVetementCreate, TypeVetementUpdate


def _verifier_nom_libre(db: Session, nom: str, exclure_id: int | None = None) -> None:
    stmt = select(TypeVetement.id).where(func.lower(TypeVetement.nom) == nom.lower())
    if exclure_id is not None:
        stmt = stmt.where(TypeVetement.id != exclure_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"La prestation « {nom} » existe déjà dans le catalogue")


def creer(db: Session, data: TypeVetementCreate) -> TypeVetement:
    _verifier_nom_libre(db, data.nom)
    tv = TypeVetement(**data.model_dump())
    db.add(tv)
    db.flush()
    return tv


def lister(db: Session, actifs_seulement: bool = True) -> list[TypeVetement]:
    stmt = select(TypeVetement)
    if actifs_seulement:
        stmt = stmt.where(TypeVetement.actif.is_(True))
    return list(db.scalars(stmt.order_by(TypeVetement.nom)).all())


def obtenir(db: Session, tv_id: int) -> TypeVetement:
    tv = db.get(TypeVetement, tv_id)
    if tv is None:
        raise NotFoundError(f"Prestation {tv_id} introuvable")
    return tv


def modifier(db: Session, tv_id: int, data: TypeVetementUpdate) -> TypeVetement:
    tv = obtenir(db, tv_id)
    changements = data.model_dump(exclude_unset=True)
    if "nom" in changements:
        _verifier_nom_libre(db, changements["nom"], exclure_id=tv.id)
    for champ, valeur in changements.items():
        setattr(tv, champ, valeur)
    db.flush()
    return tv
