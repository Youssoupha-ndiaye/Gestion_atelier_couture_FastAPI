"""Importe TOUS les modèles.

Indispensable pour Alembic : en important `app.models`, toutes les tables sont
enregistrées dans Base.metadata et --autogenerate peut les comparer à la base.
"""
from app.models.catalogue import TypeVetement
from app.models.client import Client
from app.models.commande import Commande, HistoriqueStatut, LigneCommande
from app.models.livraison import Livraison
from app.models.mesure import Mesure
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur

__all__ = [
    "Utilisateur", "Client", "Mesure", "TypeVetement", "Commande",
    "LigneCommande", "HistoriqueStatut", "Paiement", "Livraison",
]
