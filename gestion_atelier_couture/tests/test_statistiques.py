"""Palier 3 — Statistiques (section 5.2 du guide)."""
from datetime import date, timedelta

import pytest

from app.core.constantes import STATUTS_COMMANDE


@pytest.fixture
def jeu_de_donnees(client, commande_exemple, client_fatou, catalogue, h_accueil):
    """Fatou : commande 60 000 (35 000 payés) + commande annulée 10 000.
       Moussa : commande 8 000 (payée)."""
    cid = commande_exemple["id"]
    client.post(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil, json={"montant": 35000, "mode": "wave"})
    annulee = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]}).json()
    client.patch(f"/api/v1/commandes/{annulee['id']}/statut", headers=h_accueil, json={"statut": "annulee"})
    moussa = client.post("/api/v1/clients", headers=h_accueil,
                         json={"nom": "Sarr", "prenom": "Moussa", "telephone": "780000001"}).json()
    c2 = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": moussa["id"], "lignes": [{"type_vetement_id": catalogue["Pantalon"]}]}).json()
    client.post(f"/api/v1/commandes/{c2['id']}/paiements", headers=h_accueil, json={"montant": 8000, "mode": "especes"})
    return {"fatou": client_fatou, "moussa": moussa}


def test_tableau_de_bord(client, jeu_de_donnees, h_admin):
    r = client.get("/api/v1/statistiques/tableau-de-bord", headers=h_admin)
    assert r.status_code == 200
    t = r.json()
    assert t["chiffre_affaires_mois"] == 68000  # annulée exclue
    assert t["encaisse_mois"] == 43000
    assert t["reste_a_encaisser"] == 25000
    assert set(t["commandes_par_statut"]) == set(STATUTS_COMMANDE)  # les 8 statuts, même à 0
    assert t["commandes_par_statut"]["en_attente"] == 2 and t["commandes_par_statut"]["annulee"] == 1
    assert t["commandes_par_statut"]["essayage"] == 0
    assert t["periode_debut"] == date.today().replace(day=1).isoformat()
    assert t["nombre_clients"] == 2


def test_chiffre_affaires_jour_et_mois(client, jeu_de_donnees, h_admin):
    aujourd_hui = date.today()
    r = client.get("/api/v1/statistiques/chiffre-affaires", headers=h_admin,
                   params={"date_debut": (aujourd_hui - timedelta(days=2)).isoformat(),
                           "date_fin": aujourd_hui.isoformat(), "granularite": "jour"}).json()
    assert len(r["periodes"]) == 3 and r["periodes"][-1]["chiffre_affaires"] == 68000
    assert r["total_chiffre_affaires"] == 68000 and r["total_encaisse"] == 43000
    r = client.get("/api/v1/statistiques/chiffre-affaires", headers=h_admin,
                   params={"granularite": "mois"}).json()
    assert r["periodes"] == [{"periode": aujourd_hui.strftime("%Y-%m"), "chiffre_affaires": 68000, "encaisse": 43000}]


def test_chiffre_affaires_bornes_inversees_422(client, h_admin):
    r = client.get("/api/v1/statistiques/chiffre-affaires", headers=h_admin,
                   params={"date_debut": "2026-12-01", "date_fin": "2026-11-01"})
    assert r.status_code == 422
    assert client.get("/api/v1/statistiques/chiffre-affaires", headers=h_admin,
                      params={"granularite": "semaine"}).status_code == 422


def test_types_vetement(client, jeu_de_donnees, h_admin):
    r = client.get("/api/v1/statistiques/types-vetement", headers=h_admin).json()
    assert [(x["nom"], x["quantite"], x["montant"]) for x in r] == [
        ("Boubou femme", 1, 30000), ("Robe", 2, 30000), ("Pantalon", 1, 8000)]  # Chemise annulée exclue


def test_top_clients(client, jeu_de_donnees, h_admin):
    r = client.get("/api/v1/statistiques/top-clients", headers=h_admin, params={"limite": 1}).json()
    assert len(r) == 1 and r[0]["prenom"] == "Fatou" and r[0]["montant_total"] == 60000 and r[0]["solde"] == 25000


def test_impayes(client, jeu_de_donnees, h_admin):
    r = client.get("/api/v1/statistiques/impayes", headers=h_admin).json()
    assert r["total"] == 1 and r["items"][0]["solde"] == 25000


def test_statistiques_reservees_admin(client, h_accueil, h_tailleur):
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=h_accueil).status_code == 403
    assert client.get("/api/v1/statistiques/impayes", headers=h_tailleur).status_code == 403
