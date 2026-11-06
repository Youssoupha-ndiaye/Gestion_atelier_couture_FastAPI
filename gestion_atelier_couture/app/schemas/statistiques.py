from datetime import date

from pydantic import BaseModel


class TableauDeBord(BaseModel):
    periode_debut: date            # 1er jour du mois courant
    periode_fin: date              # aujourd'hui
    chiffre_affaires_mois: int     # Σ montant_total des commandes non annulées du mois (date_commande)
    encaisse_mois: int             # Σ paiements du mois (date_paiement)
    nombre_commandes_mois: int
    reste_a_encaisser: int         # Σ solde de toutes les commandes non annulées
    commandes_par_statut: dict[str, int]  # les 8 statuts, même à 0
    commandes_en_retard: int
    pretes_a_livrer: int           # statut terminee
    livraisons_du_jour: int        # date_prevue = aujourd'hui et statut planifiee
    nombre_clients: int


class PeriodeCA(BaseModel):
    periode: str                   # "2026-11-04" (jour) ou "2026-11" (mois)
    chiffre_affaires: int
    encaisse: int


class ChiffreAffaires(BaseModel):
    date_debut: date
    date_fin: date
    granularite: str
    total_chiffre_affaires: int
    total_encaisse: int
    periodes: list[PeriodeCA]


class StatTypeVetement(BaseModel):
    type_vetement_id: int
    nom: str
    quantite: int
    montant: int                   # Σ quantite × prix_unitaire


class TopClient(BaseModel):
    client_id: int
    nom: str
    prenom: str
    telephone: str
    nombre_commandes: int
    montant_total: int
    montant_paye: int
    solde: int
