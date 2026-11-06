"""Contrôle d'accès transversal : 401 sans jeton, 403 selon le rôle, admin autorisé partout."""
import pytest

ROUTES_PROTEGEES = [
    ("get", "/api/v1/auth/me"), ("get", "/api/v1/utilisateurs"), ("get", "/api/v1/clients"),
    ("get", "/api/v1/catalogue"), ("get", "/api/v1/clients/1/mesures"), ("get", "/api/v1/commandes"),
    ("get", "/api/v1/livraisons"), ("get", "/api/v1/statistiques/tableau-de-bord"),
]


@pytest.mark.parametrize("methode,url", ROUTES_PROTEGEES)
def test_401_sans_jeton(client, methode, url):
    r = getattr(client, methode)(url)
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_routes_publiques(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_403_accueil_statistiques(client, h_accueil):
    assert client.get("/api/v1/statistiques/tableau-de-bord", headers=h_accueil).status_code == 403


def test_403_accueil_mesures(client, client_fatou, h_accueil):
    r = client.post(f"/api/v1/clients/{client_fatou['id']}/mesures", headers=h_accueil, json={"tour_cou": 38})
    assert r.status_code == 403
    assert "rôle requis" in r.json()["detail"]


def test_403_tailleur_annulation(client, commande_exemple, h_tailleur):
    r = client.patch(f"/api/v1/commandes/{commande_exemple['id']}/statut", headers=h_tailleur,
                     json={"statut": "annulee"})
    assert r.status_code == 403


def test_admin_autorise_partout(client, client_fatou, catalogue, h_admin):
    """« L'admin peut tout faire » : mesures (tailleur), commandes et paiements (accueil)."""
    assert client.post(f"/api/v1/clients/{client_fatou['id']}/mesures", headers=h_admin,
                       json={"tour_cou": 38}).status_code == 201
    c = client.post("/api/v1/commandes", headers=h_admin, json={
        "client_id": client_fatou["id"], "lignes": [{"type_vetement_id": catalogue["Chemise"]}]})
    assert c.status_code == 201
    assert client.post(f"/api/v1/commandes/{c.json()['id']}/paiements", headers=h_admin,
                       json={"montant": 1000, "mode": "cheque"}).status_code == 201


def test_aucune_fuite_du_hash(client, h_admin):
    for u in client.get("/api/v1/utilisateurs", headers=h_admin).json()["items"]:
        assert "mot_de_passe_hash" not in u


def test_messages_validation_en_francais(client, h_accueil):
    r = client.post("/api/v1/clients", headers=h_accueil, json={"nom": "Diop"})
    assert r.status_code == 422
    messages = {e["champ"]: e["message"] for e in r.json()["detail"]}
    assert messages["prenom"] == "Champ obligatoire" and messages["telephone"] == "Champ obligatoire"
