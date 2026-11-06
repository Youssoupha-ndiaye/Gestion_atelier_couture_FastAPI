"""Palier 3 — Livraisons (RG18 à RG20)."""
from datetime import date, timedelta

from tests.conftest import avancer

DEMAIN = (date.today() + timedelta(days=1)).isoformat()


def test_rg18_domicile_exige_adresse(client, commande_exemple, h_accueil):
    r = client.put(f"/api/v1/commandes/{commande_exemple['id']}/livraison", headers=h_accueil,
                   json={"mode": "domicile", "date_prevue": DEMAIN})
    assert r.status_code == 422 and "adresse" in r.json()["detail"][0]["message"]


def test_rg18_upsert_et_mise_a_jour_date_prevue(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    r = client.put(f"/api/v1/commandes/{cid}/livraison", headers=h_accueil,
                   json={"mode": "domicile", "adresse": "Sicap Liberté 6, villa 12", "livreur": "Modou", "date_prevue": DEMAIN})
    assert r.status_code == 201 and r.json()["statut"] == "planifiee"
    lid = r.json()["id"]
    dans_3j = (date.today() + timedelta(days=3)).isoformat()
    r = client.put(f"/api/v1/commandes/{cid}/livraison", headers=h_accueil,
                   json={"mode": "retrait_atelier", "date_prevue": dans_3j})
    assert r.status_code == 200 and r.json()["id"] == lid and r.json()["mode"] == "retrait_atelier"
    c = client.get(f"/api/v1/commandes/{cid}", headers=h_accueil).json()
    assert c["date_livraison_prevue"] == dans_3j and c["livraison"]["id"] == lid


def test_rg19_commande_non_terminee(client, commande_exemple, h_accueil):
    r = client.post(f"/api/v1/commandes/{commande_exemple['id']}/livraison/confirmer", headers=h_accueil)
    assert r.status_code == 409 and "terminee" in r.json()["detail"]


def test_rg19_solde_impaye_message_avec_montant(client, commande_exemple, h_accueil, h_tailleur):
    cid = commande_exemple["id"]
    avancer(client, h_tailleur, cid, "en_coupe", "en_couture", "terminee")
    client.post(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil, json={"montant": 35000, "mode": "wave"})
    r = client.post(f"/api/v1/commandes/{cid}/livraison/confirmer", headers=h_accueil)
    assert r.status_code == 409 and "Solde impayé : 25 000 FCFA" in r.json()["detail"]


def test_rg19_livraison_forcee_avec_mention_historique(client, commande_exemple, h_accueil, h_tailleur):
    cid = commande_exemple["id"]
    avancer(client, h_tailleur, cid, "en_coupe", "en_couture", "terminee")
    r = client.post(f"/api/v1/commandes/{cid}/livraison/confirmer", headers=h_accueil,
                    params={"autoriser_solde_impaye": True, "commentaire": "Client de confiance"})
    assert r.status_code == 200 and r.json()["statut"] == "livree"
    h = client.get(f"/api/v1/commandes/{cid}/historique", headers=h_accueil).json()
    assert "solde impayé de 60 000 FCFA" in h[-1]["commentaire"]
    # on peut encore encaisser le solde après livraison
    assert client.post(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil,
                       json={"montant": 60000, "mode": "especes"}).status_code == 201


def test_rg20_confirmation_sans_planification(client, commande_exemple, h_accueil, h_tailleur):
    cid = commande_exemple["id"]
    avancer(client, h_tailleur, cid, "en_coupe", "en_couture", "terminee")
    client.post(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil, json={"montant": 60000, "mode": "especes"})
    r = client.post(f"/api/v1/commandes/{cid}/livraison/confirmer", headers=h_accueil)
    assert r.status_code == 200
    c = r.json()
    aujourd_hui = date.today().isoformat()
    assert c["statut"] == "livree" and c["date_livraison_reelle"] == aujourd_hui
    assert c["livraison"]["mode"] == "retrait_atelier" and c["livraison"]["statut"] == "livree"
    assert c["livraison"]["date_effective"] == aujourd_hui
    # RG12 : plus rien n'est modifiable
    assert client.put(f"/api/v1/commandes/{cid}/livraison", headers=h_accueil,
                      json={"mode": "retrait_atelier", "date_prevue": DEMAIN}).status_code == 409
    assert client.post(f"/api/v1/commandes/{cid}/livraison/confirmer", headers=h_accueil).status_code == 409


def test_liste_de_tournee(client, commande_exemple, h_accueil, h_tailleur):
    cid = commande_exemple["id"]
    aujourd_hui = date.today().isoformat()
    client.put(f"/api/v1/commandes/{cid}/livraison", headers=h_accueil,
               json={"mode": "domicile", "adresse": "Médina", "date_prevue": aujourd_hui})
    r = client.get("/api/v1/livraisons", headers=h_accueil, params={"date_prevue": aujourd_hui}).json()
    assert r["total"] == 1
    item = r["items"][0]
    assert item["numero_commande"] == commande_exemple["numero"]
    assert item["client_nom"] == "Fatou Diop" and item["client_telephone"] == "771234567"
    assert item["solde_commande"] == 60000
    assert client.get("/api/v1/livraisons", headers=h_tailleur).status_code == 403
