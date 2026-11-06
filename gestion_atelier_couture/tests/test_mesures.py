"""Palier 2 — Mesures (RG2, RG3, RG4) et droits du tailleur."""
from datetime import date, timedelta

import pytest


@pytest.fixture
def fatou_id(client, h_accueil):
    return client.post("/api/v1/clients", headers=h_accueil,
                       json={"nom": "Diop", "prenom": "Fatou", "telephone": "771234567"}).json()["id"]


def test_tailleur_prend_les_mesures_accueil_403(client, fatou_id, h_tailleur, h_accueil):
    data = {"tour_poitrine": 92, "tour_taille": 74, "longueur_robe": 140}
    r = client.post(f"/api/v1/clients/{fatou_id}/mesures", json=data, headers=h_tailleur)
    assert r.status_code == 201
    assert r.json()["date_prise"] == date.today().isoformat()
    assert r.json()["prise_par_id"] is not None
    assert client.post(f"/api/v1/clients/{fatou_id}/mesures", json=data, headers=h_accueil).status_code == 403
    # mais l'accueil peut LIRE
    assert client.get(f"/api/v1/clients/{fatou_id}/mesures", headers=h_accueil).status_code == 200


def test_rg2_au_moins_une_mesure(client, fatou_id, h_tailleur):
    r = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"notes": "rien"}, headers=h_tailleur)
    assert r.status_code == 422
    assert "Au moins une mesure" in r.json()["detail"][0]["message"]


@pytest.mark.parametrize("valeur", [0, -3, 300.5])
def test_rg2_bornes(client, fatou_id, h_tailleur, valeur):
    r = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_cou": valeur}, headers=h_tailleur)
    assert r.status_code == 422


def test_rg2_borne_300_acceptee(client, fatou_id, h_tailleur):
    assert client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"taille_cm": 300},
                       headers=h_tailleur).status_code == 201


def test_rg3_historique_et_derniere(client, fatou_id, h_tailleur):
    hier = (date.today() - timedelta(days=10)).isoformat()
    client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_taille": 70, "date_prise": hier}, headers=h_tailleur)
    m2 = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_taille": 72}, headers=h_tailleur).json()
    m3 = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_taille": 74}, headers=h_tailleur).json()
    hist = client.get(f"/api/v1/clients/{fatou_id}/mesures", headers=h_tailleur).json()
    assert len(hist) == 3 and hist[0]["id"] == m3["id"]
    # même date -> id le plus grand
    der = client.get(f"/api/v1/clients/{fatou_id}/mesures/derniere", headers=h_tailleur).json()
    assert der["id"] == m3["id"] and der["id"] > m2["id"]


def test_derniere_404_si_aucune(client, fatou_id, h_tailleur):
    r = client.get(f"/api/v1/clients/{fatou_id}/mesures/derniere", headers=h_tailleur)
    assert r.status_code == 404


def test_patch_reste_au_moins_une_mesure(client, fatou_id, h_tailleur):
    m = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_cou": 38, "tour_bras": 30},
                    headers=h_tailleur).json()
    r = client.patch(f"/api/v1/mesures/{m['id']}", json={"tour_cou": None}, headers=h_tailleur)
    assert r.status_code == 200 and r.json()["tour_cou"] is None and r.json()["tour_bras"] == 30
    r = client.patch(f"/api/v1/mesures/{m['id']}", json={"tour_bras": None}, headers=h_tailleur)
    assert r.status_code == 422


def test_supprimer_mesure_et_cascade_client(client, fatou_id, h_tailleur, h_admin):
    m = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_cou": 38}, headers=h_tailleur).json()
    m2 = client.post(f"/api/v1/clients/{fatou_id}/mesures", json={"tour_cou": 39}, headers=h_tailleur).json()
    assert client.delete(f"/api/v1/mesures/{m['id']}", headers=h_tailleur).status_code == 204
    # supprimer le client supprime ses mesures
    assert client.delete(f"/api/v1/clients/{fatou_id}", headers=h_admin).status_code == 204
    assert client.get(f"/api/v1/mesures/{m2['id']}", headers=h_admin).status_code == 404
