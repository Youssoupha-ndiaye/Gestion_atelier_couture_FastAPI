"""Scénario complet de démonstration (déroulé type de l'Annexe A), de bout en bout.

C'est exactement ce que l'on montrera dans Swagger devant le patron / l'enseignant.
"""
from tests.conftest import entete


def test_scenario_complet(client, h_admin):
    api = "/api/v1"

    # 0. L'admin crée les comptes du personnel
    for email, nom, role in [("khady@atelier.sn", "Khady Ndiaye", "accueil"), ("ousmane@atelier.sn", "Ousmane Ba", "tailleur")]:
        assert client.post(f"{api}/utilisateurs", headers=h_admin,
                           json={"email": email, "nom_complet": nom, "mot_de_passe": "motdepasse1", "role": role}).status_code == 201
    acc = entete(client.post(f"{api}/auth/login", data={"username": "khady@atelier.sn", "password": "motdepasse1"}).json()["access_token"])
    tai = entete(client.post(f"{api}/auth/login", data={"username": "ousmane@atelier.sn", "password": "motdepasse1"}).json()["access_token"])

    # 1. L'accueil crée la cliente Fatou Diop ; un doublon de téléphone est refusé
    fatou = client.post(f"{api}/clients", headers=acc,
                        json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"}).json()
    assert client.post(f"{api}/clients", headers=acc,
                       json={"nom": "X", "prenom": "Y", "telephone": "771234567"}).status_code == 409

    # 2. Le tailleur prend les mesures ; l'accueil ne peut pas (403)
    assert client.post(f"{api}/clients/{fatou['id']}/mesures", headers=tai,
                       json={"tour_poitrine": 92, "tour_taille": 74, "longueur_robe": 140}).status_code == 201
    assert client.post(f"{api}/clients/{fatou['id']}/mesures", headers=acc, json={"tour_cou": 1}).status_code == 403

    # 3. L'accueil crée la commande (numéro, total, date prévue calculés)
    cat = {t["nom"]: t["id"] for t in client.get(f"{api}/catalogue", headers=acc).json()}
    cmd = client.post(f"{api}/commandes", headers=acc, json={
        "client_id": fatou["id"], "remise": 5000,
        "lignes": [{"type_vetement_id": cat["Boubou femme"], "description": "bazin bleu, broderie dorée"},
                   {"type_vetement_id": cat["Robe"], "quantite": 2, "prix_unitaire": 15000}]}).json()
    cid = cmd["id"]
    assert cmd["montant_total"] == 55000 and cmd["numero"].startswith("CMD-")

    # 4. L'accueil tente « terminee » -> 409 avec les statuts possibles
    r = client.patch(f"{api}/commandes/{cid}/statut", headers=acc, json={"statut": "terminee"})
    assert r.status_code == 409 and "Statuts possibles" in r.json()["detail"]

    # 5. Le tailleur fait avancer la production
    for s in ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]:
        assert client.patch(f"{api}/commandes/{cid}/statut", headers=tai, json={"statut": s}).status_code == 200

    # 6. Paiements : acompte Wave puis tentative de trop-perçu
    assert client.post(f"{api}/commandes/{cid}/paiements", headers=acc,
                       json={"montant": 30000, "mode": "wave", "reference": "WAVE-001"}).status_code == 201
    assert client.post(f"{api}/commandes/{cid}/paiements", headers=acc,
                       json={"montant": 30000, "mode": "especes"}).status_code == 409

    # 7. Planification à domicile puis confirmation refusée (solde impayé)
    assert client.put(f"{api}/commandes/{cid}/livraison", headers=acc,
                      json={"mode": "domicile", "adresse": "Parcelles Assainies U15", "date_prevue": cmd["date_livraison_prevue"]}).status_code == 201
    r = client.post(f"{api}/commandes/{cid}/livraison/confirmer", headers=acc)
    assert r.status_code == 409 and r.json()["detail"].startswith("Solde impayé : 25 000 FCFA")

    # 8. Encaissement du solde puis livraison
    client.post(f"{api}/commandes/{cid}/paiements", headers=acc, json={"montant": 25000, "mode": "orange_money"})
    fin = client.post(f"{api}/commandes/{cid}/livraison/confirmer", headers=acc).json()
    assert fin["statut"] == "livree" and fin["solde"] == 0

    # 9. Statistiques du patron ; refusées à l'accueil
    tdb = client.get(f"{api}/statistiques/tableau-de-bord", headers=h_admin).json()
    assert tdb["chiffre_affaires_mois"] == 55000 and tdb["encaisse_mois"] == 55000
    assert tdb["commandes_par_statut"]["livree"] == 1
    assert client.get(f"{api}/statistiques/tableau-de-bord", headers=acc).status_code == 403

    # 10. Désactivation d'un compte : son jeton est immédiatement refusé
    acc_id = client.get(f"{api}/auth/me", headers=acc).json()["id"]
    client.patch(f"{api}/utilisateurs/{acc_id}", headers=h_admin, json={"actif": False})
    assert client.get(f"{api}/auth/me", headers=acc).status_code == 401
