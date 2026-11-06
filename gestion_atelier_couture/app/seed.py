"""Données de départ. Lancement : python -m app.seed

- crée l'administrateur décrit dans le .env (s'il n'existe pas déjà) ;
- crée 2 comptes de démonstration accueil + tailleur (si SEED_COMPTES_DEMO=true) ;
- crée les 7 prestations du catalogue (Annexe B).

Le script est IDEMPOTENT : on peut le relancer sans créer de doublons.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.catalogue import TypeVetement
from app.models.utilisateur import Utilisateur

# ⚠ Ajuster si l'Annexe B de l'énoncé donne d'autres noms / prix / délais.
PRESTATIONS = [
    {"nom": "Boubou homme", "description": "Grand boubou trois pièces", "prix_base": 25000, "delai_jours": 7},
    {"nom": "Boubou femme", "description": "Grand boubou brodé", "prix_base": 30000, "delai_jours": 10},
    {"nom": "Robe", "description": "Robe sur mesure", "prix_base": 20000, "delai_jours": 7},
    {"nom": "Ensemble taille basse", "description": "Haut + pagne taille basse", "prix_base": 18000, "delai_jours": 5},
    {"nom": "Chemise", "description": "Chemise homme sur mesure", "prix_base": 10000, "delai_jours": 3},
    {"nom": "Pantalon", "description": "Pantalon sur mesure", "prix_base": 8000, "delai_jours": 3},
    {"nom": "Retouche", "description": "Ourlet, ajustement, reprise", "prix_base": 2000, "delai_jours": 1},
]

COMPTES_DEMO = [
    {"email": "accueil@atelier.sn", "nom_complet": "Awa Sow", "mot_de_passe": "accueil123", "role": "accueil"},
    {"email": "tailleur@atelier.sn", "nom_complet": "Ibrahima Fall", "mot_de_passe": "tailleur123", "role": "tailleur"},
]


def _creer_utilisateur_si_absent(db: Session, email: str, nom: str, mot_de_passe: str, role: str) -> bool:
    email = email.lower()
    if db.scalar(select(Utilisateur).where(Utilisateur.email == email)):
        return False
    db.add(Utilisateur(email=email, nom_complet=nom, mot_de_passe_hash=hash_password(mot_de_passe),
                       role=role, actif=True))
    return True


def seed(db: Session, comptes_demo: bool | None = None) -> None:
    comptes_demo = settings.SEED_COMPTES_DEMO if comptes_demo is None else comptes_demo

    if _creer_utilisateur_si_absent(db, settings.ADMIN_EMAIL, settings.ADMIN_NOM, settings.ADMIN_PASSWORD, "admin"):
        print(f"✔ Admin créé : {settings.ADMIN_EMAIL}")
    else:
        print(f"• Admin déjà présent : {settings.ADMIN_EMAIL}")

    if comptes_demo:
        for c in COMPTES_DEMO:
            if _creer_utilisateur_si_absent(db, c["email"], c["nom_complet"], c["mot_de_passe"], c["role"]):
                print(f"✔ Compte {c['role']} créé : {c['email']}")

    for p in PRESTATIONS:
        if not db.scalar(select(TypeVetement).where(TypeVetement.nom == p["nom"])):
            db.add(TypeVetement(**p, actif=True))
            print(f"✔ Prestation créée : {p['nom']}")

    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("Seed terminé.")
