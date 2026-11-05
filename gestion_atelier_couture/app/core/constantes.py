"""Valeurs autorisées partagées par les modèles, les schémas et les services.

On stocke les statuts en String dans PostgreSQL (plus simple avec Alembic que les
Enum natives) et on limite les valeurs côté Pydantic avec Literal.
"""
from typing import Literal

# ---------- Utilisateurs ----------
ROLES = ("admin", "tailleur", "accueil")
Role = Literal["admin", "tailleur", "accueil"]

# ---------- Clients ----------
GENRES = ("homme", "femme", "enfant")
Genre = Literal["homme", "femme", "enfant"]

# ---------- Mesures (les 18 champs, en cm) ----------
CHAMPS_MESURES = [
    "taille_cm", "tour_cou", "carrure_dos", "longueur_epaule", "tour_poitrine",
    "tour_taille", "tour_bassin", "longueur_manche", "tour_bras", "tour_poignet",
    "longueur_dos", "longueur_haut", "longueur_pantalon", "tour_cuisse", "tour_genou",
    "bas_pantalon", "entrejambe", "longueur_robe",
]

# ---------- Commandes ----------
STATUTS_COMMANDE = (
    "en_attente", "en_coupe", "en_couture", "essayage",
    "retouches", "terminee", "livree", "annulee",
)
StatutCommande = Literal[
    "en_attente", "en_coupe", "en_couture", "essayage",
    "retouches", "terminee", "livree", "annulee",
]
STATUTS_FINAUX = ("livree", "annulee")  # RG12 : plus modifiable

# Workflow de production (section 5.1 du guide)
TRANSITIONS: dict[str, list[str]] = {
    "en_attente": ["en_coupe", "annulee"],
    "en_coupe": ["en_couture", "annulee"],
    "en_couture": ["essayage", "terminee", "annulee"],
    "essayage": ["retouches", "terminee", "annulee"],
    "retouches": ["essayage", "terminee", "annulee"],
    "terminee": ["livree"],  # uniquement via la confirmation de livraison
    "livree": [],
    "annulee": [],
}

# ---------- Paiements ----------
MODES_PAIEMENT = ("especes", "wave", "orange_money", "virement", "cheque")
ModePaiement = Literal["especes", "wave", "orange_money", "virement", "cheque"]

# ---------- Livraisons ----------
MODES_LIVRAISON = ("retrait_atelier", "domicile")
ModeLivraison = Literal["retrait_atelier", "domicile"]
StatutLivraison = Literal["planifiee", "livree"]
