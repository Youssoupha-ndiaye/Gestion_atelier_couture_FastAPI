"""Palier 1 — Clients (RG1, RG4) et catalogue."""

FATOU = {"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"}


def test_creer_client_normalise_telephone(client, h_accueil):
    r = client.post("/api/v1/clients", json=FATOU, headers=h_accueil)
    assert r.status_code == 201
    assert r.json()["telephone"] == "771234567"


def test_rg1_doublon_telephone_meme_ecrit_autrement(client, h_accueil):
    assert client.post("/api/v1/clients", json=FATOU, headers=h_accueil).status_code == 201
    r = client.post("/api/v1/clients", json={"nom": "X", "prenom": "Y", "telephone": "77.123.45.67"}, headers=h_accueil)
    assert r.status_code == 409


def test_rg1_telephone_invalide(client, h_accueil):
    r = client.post("/api/v1/clients", json={**FATOU, "telephone": "77abc"}, headers=h_accueil)
    assert r.status_code == 422
    assert "Numéro invalide" in r.json()["detail"][0]["message"]


def test_rg1_patch_garder_son_numero_nest_pas_un_doublon(client, h_accueil):
    cid = client.post("/api/v1/clients", json=FATOU, headers=h_accueil).json()["id"]
    r = client.patch(f"/api/v1/clients/{cid}", json={"telephone": "771234567", "adresse": "Médina"}, headers=h_accueil)
    assert r.status_code == 200
    assert r.json()["adresse"] == "Médina"
    assert r.json()["nom"] == "Diop"  # non envoyé -> inchangé


def test_rg1_patch_numero_dun_autre_client(client, h_accueil):
    client.post("/api/v1/clients", json=FATOU, headers=h_accueil)
    cid = client.post("/api/v1/clients", json={"nom": "Ba", "prenom": "Ali", "telephone": "780000000"},
                      headers=h_accueil).json()["id"]
    assert client.patch(f"/api/v1/clients/{cid}", json={"telephone": "77 123 45 67"}, headers=h_accueil).status_code == 409


def test_patch_nom_vide_refuse(client, h_accueil):
    cid = client.post("/api/v1/clients", json=FATOU, headers=h_accueil).json()["id"]
    assert client.patch(f"/api/v1/clients/{cid}", json={"nom": ""}, headers=h_accueil).status_code == 422
    assert client.patch(f"/api/v1/clients/{cid}", json={"nom": None}, headers=h_accueil).status_code == 422


def test_recherche_filtre_tri_pagination(client, h_accueil):
    for nom, prenom, tel, genre in [("Sarr", "Moussa", "770000001", "homme"), ("Diop", "Fatou", "770000002", "femme"),
                                    ("Diop", "Awa", "770000003", "femme"), ("Ndiaye", "Bébé", "770000004", "enfant")]:
        client.post("/api/v1/clients", json={"nom": nom, "prenom": prenom, "telephone": tel, "genre": genre},
                    headers=h_accueil)
    r = client.get("/api/v1/clients", params={"q": "dio"}, headers=h_accueil).json()
    assert r["total"] == 2 and [c["prenom"] for c in r["items"]] == ["Awa", "Fatou"]  # tri nom puis prénom
    assert client.get("/api/v1/clients", params={"genre": "enfant"}, headers=h_accueil).json()["total"] == 1
    page = client.get("/api/v1/clients", params={"limit": 2, "offset": 2}, headers=h_accueil).json()
    assert page["total"] == 4 and len(page["items"]) == 2 and page["limit"] == 2 and page["offset"] == 2
    assert client.get("/api/v1/clients", params={"q": "d"}, headers=h_accueil).status_code == 422


def test_supprimer_client_admin_seulement(client, h_accueil, h_admin):
    cid = client.post("/api/v1/clients", json=FATOU, headers=h_accueil).json()["id"]
    assert client.delete(f"/api/v1/clients/{cid}", headers=h_accueil).status_code == 403
    assert client.delete(f"/api/v1/clients/{cid}", headers=h_admin).status_code == 204
    assert client.get(f"/api/v1/clients/{cid}", headers=h_admin).status_code == 404


def test_catalogue(client, h_admin, h_accueil):
    assert len(client.get("/api/v1/catalogue", headers=h_accueil).json()) == 7
    r = client.post("/api/v1/catalogue", headers=h_admin,
                    json={"nom": "Caftan", "prix_base": 35000, "delai_jours": 12})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post("/api/v1/catalogue", headers=h_admin,
                       json={"nom": "caftan", "prix_base": 1, "delai_jours": 1}).status_code == 409
    assert client.post("/api/v1/catalogue", headers=h_accueil,
                       json={"nom": "Autre", "prix_base": 1, "delai_jours": 1}).status_code == 403
    assert client.post("/api/v1/catalogue", headers=h_admin,
                       json={"nom": "Neg", "prix_base": -5, "delai_jours": 1}).status_code == 422
    client.patch(f"/api/v1/catalogue/{tid}", headers=h_admin, json={"actif": False})
    assert len(client.get("/api/v1/catalogue", headers=h_accueil).json()) == 7
    assert len(client.get("/api/v1/catalogue", params={"actifs_seulement": False}, headers=h_accueil).json()) == 8
