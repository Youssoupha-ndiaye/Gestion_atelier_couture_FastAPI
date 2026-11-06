"""Palier 2 — Workflow des statuts (RG12 à RG15)."""
from tests.conftest import avancer


def test_workflow_complet_et_historique(client, commande_exemple, h_tailleur):
    cid = commande_exemple["id"]
    c = avancer(client, h_tailleur, cid, "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee")
    assert c["statut"] == "terminee"
    h = client.get(f"/api/v1/commandes/{cid}/historique", headers=h_tailleur).json()
    assert [x["nouveau_statut"] for x in h] == ["en_attente", "en_coupe", "en_couture", "essayage",
                                                "retouches", "essayage", "terminee"]
    assert h[1]["ancien_statut"] == "en_attente" and h[1]["utilisateur_nom"] == "Ibrahima Fall"


def test_rg13_meme_statut(client, commande_exemple, h_tailleur):
    r = client.patch(f"/api/v1/commandes/{commande_exemple['id']}/statut", headers=h_tailleur,
                     json={"statut": "en_attente"})
    assert r.status_code == 409 and "déjà" in r.json()["detail"]


def test_rg13_livree_interdit_via_statut(client, commande_exemple, h_admin):
    cid = commande_exemple["id"]
    avancer(client, h_admin, cid, "en_coupe", "en_couture", "terminee")
    r = client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_admin, json={"statut": "livree"})
    assert r.status_code == 409 and "confirmation" in r.json()["detail"]


def test_transition_interdite_donne_les_statuts_possibles(client, commande_exemple, h_accueil):
    """Annexe A étape 4 : l'accueil tente « terminee » depuis en_attente -> 409 (pas 403)."""
    r = client.patch(f"/api/v1/commandes/{commande_exemple['id']}/statut", headers=h_accueil,
                     json={"statut": "terminee"})
    assert r.status_code == 409
    assert "Statuts possibles : annulee, en_coupe" in r.json()["detail"]


def test_statut_inconnu_422(client, commande_exemple, h_admin):
    r = client.patch(f"/api/v1/commandes/{commande_exemple['id']}/statut", headers=h_admin, json={"statut": "perdue"})
    assert r.status_code == 422


def test_rg14_tailleur_ne_peut_pas_annuler(client, commande_exemple, h_tailleur):
    r = client.patch(f"/api/v1/commandes/{commande_exemple['id']}/statut", headers=h_tailleur,
                     json={"statut": "annulee"})
    assert r.status_code == 403


def test_rg12_commande_annulee_plus_modifiable(client, commande_exemple, h_accueil):
    cid = commande_exemple["id"]
    avancer(client, h_accueil, cid, "annulee")
    assert client.patch(f"/api/v1/commandes/{cid}/statut", headers=h_accueil,
                        json={"statut": "en_coupe"}).status_code == 409
    assert client.patch(f"/api/v1/commandes/{cid}", headers=h_accueil, json={"notes": "x"}).status_code == 409


def test_service_transitions_sans_http(db, commande_exemple):
    """Test unitaire du service (sans passer par HTTP)."""
    import pytest

    from app.core.exceptions import ConflictError
    from app.models.utilisateur import Utilisateur
    from app.services import commande_service

    admin = db.query(Utilisateur).filter_by(role="admin").one()
    with pytest.raises(ConflictError):
        commande_service.changer_statut(db, commande_exemple["id"], "essayage", None, admin)
    c = commande_service.changer_statut(db, commande_exemple["id"], "en_coupe", None, admin)
    assert c.statut == "en_coupe"
    db.rollback()
