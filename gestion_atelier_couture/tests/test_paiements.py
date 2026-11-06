"""Palier 2 — Paiements (RG16, RG17) et annulation avec acompte (RG14)."""
from datetime import date, timedelta


def payer(client, h, cid, montant, mode="especes", **extra):
    return client.post(f"/api/v1/commandes/{cid}/paiements", headers=h, json={"montant": montant, "mode": mode, **extra})


def test_acompte_puis_solde(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    r = payer(client, h_accueil, cid, 20000, "wave", reference="WAVE-123")
    assert r.status_code == 201 and r.json()["date_paiement"] == date.today().isoformat()
    payer(client, h_accueil, cid, 15000, "orange_money")
    c = client.get(f"/api/v1/commandes/{cid}", headers=h_accueil).json()
    assert c["montant_paye"] == 35000 and c["solde"] == 25000 and len(c["paiements"]) == 2
    liste = client.get(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil).json()
    assert [p["montant"] for p in liste] == [20000, 15000]  # ordre de saisie


def test_rg16_montant_superieur_au_solde(client, commande_exemple, h_accueil):
    r = payer(client, h_accueil, commande_exemple["id"], 60001)
    assert r.status_code == 409 and "60 000 FCFA" in r.json()["detail"]
    assert payer(client, h_accueil, commande_exemple["id"], 60000).status_code == 201
    assert payer(client, h_accueil, commande_exemple["id"], 1).status_code == 409


def test_rg16_montant_nul_mode_invalide_date_future(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    assert payer(client, h_accueil, cid, 0).status_code == 422
    assert payer(client, h_accueil, cid, 1000, "bitcoin").status_code == 422
    demain = (date.today() + timedelta(days=1)).isoformat()
    r = payer(client, h_accueil, cid, 1000, date_paiement=demain)
    assert r.status_code == 422 and "futur" in r.json()["detail"][0]["message"]


def test_rg16_commande_annulee(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_accueil, json={"statut": "annulee"})
    assert payer(client, h_accueil, cid, 1000).status_code == 409


def test_rg17_supprimer_paiement_admin_et_recalcul(client, commande_exemple, h_accueil, h_admin):
    cid = commande_exemple["id"]
    pid = payer(client, h_accueil, cid, 20000).json()["id"]
    assert client.delete(f"/api/v1/paiements/{pid}", headers=h_accueil).status_code == 403
    assert client.delete(f"/api/v1/paiements/{pid}", headers=h_admin).status_code == 204
    c = client.get(f"/api/v1/commandes/{cid}", headers=h_admin).json()
    assert c["montant_paye"] == 0 and c["solde"] == 60000


def test_rg7_nouveau_total_inferieur_au_paye(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    payer(client, h_accueil, cid, 50000)
    r = client.patch(f"/api/v1/commandes/{cid}", headers=h_accueil, json={"remise": 15000})
    assert r.status_code == 409
    ligne_robe = commande_exemple["lignes"][1]["id"]
    assert client.delete(f"/api/v1/commandes/{cid}/lignes/{ligne_robe}", headers=h_accueil).status_code == 409
    # rien n'a été modifié
    assert client.get(f"/api/v1/commandes/{cid}", headers=h_accueil).json()["montant_total"] == 60000


def test_tailleur_ne_peut_pas_encaisser(client, commande_exemple, h_tailleur):
    assert payer(client, h_tailleur, commande_exemple["id"], 1000).status_code == 403


def test_rg14_annulation_avec_acompte_exige_commentaire(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    client.post(f"/api/v1/commandes/{cid}/paiements", headers=h_accueil, json={"montant": 20000, "mode": "wave"})
    r = client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_accueil, json={"statut": "annulee"})
    assert r.status_code == 422 and "acompte" in r.json()["detail"]
    r = client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_accueil,
                     json={"statut": "annulee", "commentaire": "Acompte remboursé en espèces"})
    assert r.status_code == 200 and r.json()["statut"] == "annulee"


