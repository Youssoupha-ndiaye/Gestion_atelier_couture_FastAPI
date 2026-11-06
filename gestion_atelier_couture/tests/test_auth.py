"""Palier 1 — Authentification et utilisateurs (RG21 à RG24)."""
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password

from tests.conftest import entete


def test_login_ok_et_me(client):
    r = client.post("/api/v1/auth/login", data={"username": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    assert r.status_code == 200
    corps = r.json()
    assert corps["token_type"] == "bearer"
    assert corps["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    me = client.get("/api/v1/auth/me", headers=entete(corps["access_token"]))
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert "mot_de_passe_hash" not in me.json()


def test_rg23_meme_message_email_inconnu_ou_mauvais_mdp(client):
    r1 = client.post("/api/v1/auth/login", data={"username": "inconnu@atelier.sn", "password": "nimportequoi"})
    r2 = client.post("/api/v1/auth/login", data={"username": settings.ADMIN_EMAIL, "password": "mauvais_mdp"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"] == "Email ou mot de passe incorrect"


def test_login_json_refuse(client):
    """Le login attend un FORMULAIRE OAuth2, pas du JSON."""
    r = client.post("/api/v1/auth/login", json={"username": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    assert r.status_code == 422


def test_rg21_hash_argon2():
    h = hash_password("motdepasse1")
    assert h.startswith("$argon2")
    assert verify_password("motdepasse1", h)
    assert not verify_password("autre", h)


def test_rg21_mot_de_passe_trop_court(client, h_admin):
    r = client.post("/api/v1/utilisateurs", headers=h_admin,
                    json={"email": "x@atelier.sn", "nom_complet": "X", "mot_de_passe": "court", "role": "accueil"})
    assert r.status_code == 422
    assert r.json()["detail"][0]["champ"] == "mot_de_passe"


def test_creer_utilisateur_et_email_doublon(client, h_admin):
    data = {"email": "Modou@Atelier.sn", "nom_complet": "Modou Diop", "mot_de_passe": "secret123", "role": "tailleur"}
    r = client.post("/api/v1/utilisateurs", headers=h_admin, json=data)
    assert r.status_code == 201
    assert r.json()["email"] == "modou@atelier.sn"
    assert "mot_de_passe_hash" not in r.json() and "mot_de_passe" not in r.json()
    r2 = client.post("/api/v1/utilisateurs", headers=h_admin, json=data)
    assert r2.status_code == 409


def test_lister_utilisateurs_trie_par_nom(client, h_admin):
    r = client.get("/api/v1/utilisateurs", headers=h_admin)
    assert r.status_code == 200
    noms = [u["nom_complet"] for u in r.json()["items"]]
    assert noms == sorted(noms)
    assert r.json()["total"] == 3


def test_rg22_compte_desactive_refuse_meme_avec_jeton_valide(client, h_admin, token_accueil):
    assert client.get("/api/v1/auth/me", headers=entete(token_accueil)).status_code == 200
    accueil = next(u for u in client.get("/api/v1/utilisateurs", headers=h_admin).json()["items"]
                   if u["role"] == "accueil")
    r = client.patch(f"/api/v1/utilisateurs/{accueil['id']}", headers=h_admin, json={"actif": False})
    assert r.status_code == 200 and r.json()["actif"] is False
    r = client.get("/api/v1/auth/me", headers=entete(token_accueil))
    assert r.status_code == 401
    assert r.json()["detail"] == "Compte désactivé"


def test_rg22_jeton_expire_ou_falsifie(client):
    expire = create_access_token(1, expires_minutes=-1)
    assert client.get("/api/v1/auth/me", headers=entete(expire)).status_code == 401
    assert client.get("/api/v1/auth/me", headers=entete("abc.def.ghi")).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_rg24_admin_ne_peut_pas_se_desactiver_ni_se_retrograder(client, h_admin):
    moi = client.get("/api/v1/auth/me", headers=h_admin).json()
    r1 = client.patch(f"/api/v1/utilisateurs/{moi['id']}", headers=h_admin, json={"actif": False})
    r2 = client.patch(f"/api/v1/utilisateurs/{moi['id']}", headers=h_admin, json={"role": "accueil"})
    assert r1.status_code == r2.status_code == 409


def test_utilisateurs_reserve_admin(client, h_accueil, h_tailleur):
    assert client.get("/api/v1/utilisateurs", headers=h_accueil).status_code == 403
    assert client.get("/api/v1/utilisateurs", headers=h_tailleur).status_code == 403
