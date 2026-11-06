"""Palier 2 — Commandes (RG4 à RG12)."""
import re
from datetime import date, timedelta


def test_creation_complete(client, commande_exemple, mesure_fatou):
    c = commande_exemple
    # RG5 : numéro CMD-AAAA-NNNNN
    assert re.fullmatch(rf"CMD-{date.today().year}-\d{{5}}", c["numero"])
    assert c["numero"].endswith(f"{c['id']:05d}")
    assert c["statut"] == "en_attente"
    # RG6 : prix par défaut = prix_base ; prix négocié respecté
    assert [l["prix_unitaire"] for l in c["lignes"]] == [30000, 15000]
    assert [l["sous_total"] for l in c["lignes"]] == [30000, 30000]
    assert c["lignes"][0]["nom_prestation"] == "Boubou femme"
    # RG7
    assert c["montant_total"] == 60000 and c["montant_paye"] == 0 and c["solde"] == 60000
    # RG8 : date prévue = aujourd'hui + max(10, 7) jours
    assert c["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    # RG9 : mesure absente -> dernières mesures du client
    assert c["mesure_id"] == mesure_fatou["id"]
    assert c["en_retard"] is False and c["client_nom"] == "Fatou Diop"


def test_rg15_historique_initial(client, commande_exemple, h_accueil):
    h = client.get(f"/api/v1/commandes/{commande_exemple['id']}/historique", headers=h_accueil).json()
    assert len(h) == 1 and h[0]["ancien_statut"] is None and h[0]["nouveau_statut"] == "en_attente"


def test_rg6_prestation_inactive_refusee(client, client_fatou, catalogue, h_admin, h_accueil):
    client.patch(f"/api/v1/catalogue/{catalogue['Retouche']}", headers=h_admin, json={"actif": False})
    r = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Retouche"]}]})
    assert r.status_code == 422 and "inactive" in r.json()["detail"]


def test_rg6_prix_copie_independant_du_catalogue(client, commande_exemple, catalogue, h_admin, h_accueil):
    client.patch(f"/api/v1/catalogue/{catalogue['Boubou femme']}", headers=h_admin, json={"prix_base": 99999})
    c = client.get(f"/api/v1/commandes/{commande_exemple['id']}", headers=h_accueil).json()
    assert c["lignes"][0]["prix_unitaire"] == 30000


def test_rg7_remise(client, client_fatou, catalogue, h_accueil):
    base = {"client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]}
    r = client.post("/api/v1/commandes", headers=h_accueil, json={**base, "remise": 2000})
    assert r.status_code == 201 and r.json()["montant_total"] == 8000
    assert client.post("/api/v1/commandes", headers=h_accueil, json={**base, "remise": 10001}).status_code == 422
    assert client.post("/api/v1/commandes", headers=h_accueil, json={**base, "remise": -1}).status_code == 422


def test_rg8_date_prevue(client, client_fatou, catalogue, h_accueil):
    base = {"client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]}
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert client.post("/api/v1/commandes", headers=h_accueil,
                       json={**base, "date_livraison_prevue": hier}).status_code == 422
    dans_15j = (date.today() + timedelta(days=15)).isoformat()
    r = client.post("/api/v1/commandes", headers=h_accueil, json={**base, "date_livraison_prevue": dans_15j})
    assert r.json()["date_livraison_prevue"] == dans_15j


def test_rg9_mesure_dun_autre_client(client, mesure_fatou, catalogue, h_accueil):
    autre = client.post("/api/v1/clients", headers=h_accueil,
                        json={"nom": "Sarr", "prenom": "Moussa", "telephone": "780000001"}).json()
    r = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": autre["id"], "mesure_id": mesure_fatou["id"],
        "lignes": [{"type_vetement_id": catalogue["Chemise"]}]})
    assert r.status_code == 422
    # sans mesure et client sans mesures -> mesure_id null
    r = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": autre["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]})
    assert r.status_code == 201 and r.json()["mesure_id"] is None


def test_commande_sans_ligne_refusee(client, client_fatou, h_accueil):
    assert client.post("/api/v1/commandes", headers=h_accueil,
                       json={"client_id": client_fatou["id"], "lignes": []}).status_code == 422


def test_tailleur_ne_cree_pas_de_commande(client, client_fatou, catalogue, h_tailleur):
    r = client.post("/api/v1/commandes", headers=h_tailleur, json={
        "client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]})
    assert r.status_code == 403


def test_rg10_lignes(client, commande_exemple, catalogue, h_accueil, h_tailleur):
    cid = commande_exemple["id"]
    r = client.post(f"/api/v1/commandes/{cid}/lignes", headers=h_accueil,
                    json={"type_vetement_id": catalogue["Pantalon"]})
    assert r.status_code == 201 and r.json()["montant_total"] == 68000
    l1, l2, l3 = (l["id"] for l in r.json()["lignes"])
    assert client.delete(f"/api/v1/commandes/{cid}/lignes/{l3}", headers=h_accueil).status_code == 204
    assert client.delete(f"/api/v1/commandes/{cid}/lignes/{l2}", headers=h_accueil).status_code == 204
    # toujours au moins une ligne
    assert client.delete(f"/api/v1/commandes/{cid}/lignes/{l1}", headers=h_accueil).status_code == 409
    c = client.get(f"/api/v1/commandes/{cid}", headers=h_accueil).json()
    assert c["montant_total"] == 30000
    # hors en_attente -> 409
    client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_tailleur, json={"statut": "en_coupe"})
    assert client.post(f"/api/v1/commandes/{cid}/lignes", headers=h_accueil,
                       json={"type_vetement_id": catalogue["Pantalon"]}).status_code == 409


def test_patch_commande(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    r = client.patch(f"/api/v1/commandes/{cid}", headers=h_accueil, json={"remise": 5000, "notes": "client fidèle"})
    assert r.status_code == 200 and r.json()["montant_total"] == 55000 and r.json()["notes"] == "client fidèle"
    assert client.patch(f"/api/v1/commandes/{cid}", headers=h_accueil, json={"remise": 70000}).status_code == 422
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert client.patch(f"/api/v1/commandes/{cid}", headers=h_accueil,
                        json={"date_livraison_prevue": hier}).status_code == 422


def test_filtres_liste(client, commande_exemple, client_fatou, h_accueil):
    assert client.get("/api/v1/commandes", headers=h_accueil, params={"statut": "en_attente"}).json()["total"] == 1
    assert client.get("/api/v1/commandes", headers=h_accueil, params={"statut": "terminee"}).json()["total"] == 0
    assert client.get("/api/v1/commandes", headers=h_accueil,
                      params={"numero": commande_exemple["numero"][-5:]}).json()["total"] == 1
    assert client.get("/api/v1/commandes", headers=h_accueil, params={"en_retard": True}).json()["total"] == 0
    assert client.get(f"/api/v1/clients/{client_fatou['id']}/commandes", headers=h_accueil).json()["total"] == 1


def test_rg11_en_retard(client, commande_exemple, db, h_accueil):
    from app.models.commande import Commande
    c = db.get(Commande, commande_exemple["id"])
    c.date_livraison_prevue = date.today() - timedelta(days=3)
    db.commit()
    r = client.get("/api/v1/commandes", headers=h_accueil, params={"en_retard": True}).json()
    assert r["total"] == 1 and r["items"][0]["en_retard"] is True


def test_rg4_client_avec_commande_non_supprimable(client, commande_exemple, client_fatou, mesure_fatou,
                                                 h_admin, h_tailleur):
    assert client.delete(f"/api/v1/clients/{client_fatou['id']}", headers=h_admin).status_code == 409
    # mesure utilisée par la commande
    assert client.delete(f"/api/v1/mesures/{mesure_fatou['id']}", headers=h_tailleur).status_code == 409


def test_resume_client_hors_annulees(client, commande_exemple, client_fatou, catalogue, h_accueil):
    autre = client.post("/api/v1/commandes", headers=h_accueil, json={
        "client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]}).json()
    client.patch(f"/api/v1/commandes/{autre['id']}/statut", headers=h_accueil, json={"statut": "annulee"})
    r = client.get(f"/api/v1/clients/{client_fatou['id']}/resume", headers=h_accueil).json()
    assert r["nombre_commandes"] == 1 and r["montant_total"] == 60000 and r["solde"] == 60000
    assert r["client"]["prenom"] == "Fatou"
