# `tests/` — Tests automatisés (pytest + TestClient)

**91 tests**, tous verts, sur une **vraie base PostgreSQL de test**.

```bash
pytest -v                              # tout
pytest tests/test_paiements.py -v      # un seul fichier
pytest -k rg19 -v                      # les tests dont le nom contient « rg19 »
```

> Prérequis : une base `atelier_test` vide et accessible via `TEST_DATABASE_URL`
> (voir le README principal). ⚠ Elle est **vidée avant chaque test** : ne jamais
> pointer `TEST_DATABASE_URL` vers la vraie base.

## Comment je l'ai fait

### `conftest.py` : les fixtures partagées
Une **fixture** est une fonction qui prépare un contexte réutilisable ; pytest
l'injecte dans un test simplement parce que le test la nomme en paramètre.

| Fixture | Rôle |
|---|---|
| `schema_de_test` (session, auto) | **une fois** : `alembic upgrade head` sur la base de test (jamais `create_all`) |
| `base_propre` (auto) | **avant chaque test** : `TRUNCATE ... RESTART IDENTITY CASCADE` puis seed (admin, accueil, tailleur, 7 prestations) → chaque test part d'une base identique et indépendante |
| `client` | `TestClient(app)` + `app.dependency_overrides[get_db] = override` (la vraie base est remplacée par la base de test) |
| `token_admin`, `token_accueil`, `token_tailleur` | se connectent via `POST /auth/login` (formulaire) |
| `h_admin`, `h_accueil`, `h_tailleur` | en-têtes `{"Authorization": "Bearer ..."}` prêts à l'emploi |
| `catalogue` | `{"Robe": 3, ...}` : id de chaque prestation |
| `client_fatou`, `mesure_fatou`, `commande_exemple` | données métier de base (commande de 60 000 FCFA) |
| `avancer(...)` | aide : enchaîne plusieurs changements de statut |

Astuce de vitesse : Argon2 est volontairement lent ; comme le seed est rejoué
avant chaque test, le hash des mots de passe du seed est mis en cache (`lru_cache`).

### `TestClient`
Simule des requêtes HTTP **sans lancer de serveur** :
```python
r = client.post("/api/v1/clients", json={...}, headers=h_accueil)
assert r.status_code == 201
```

## Couverture des règles de gestion

| Fichier | Ce qui est testé |
|---|---|
| `test_auth.py` | login formulaire, `/me`, **RG21** (Argon2, ≥ 8 car.), **RG22** (compte désactivé, jeton expiré/falsifié), **RG23** (même message), **RG24**, email doublon 409 |
| `test_clients.py` | **RG1** (normalisation, doublon écrit autrement, PATCH avec son propre numéro), recherche `q`, filtre genre, tri, pagination, catalogue |
| `test_mesures.py` | **RG2** (au moins une, bornes 0 / 300), **RG3** (historique, dernière), PATCH après fusion, cascade client → mesures |
| `test_commandes.py` | **RG4**, **RG5**, **RG6**, **RG7**, **RG8**, **RG9**, **RG10**, **RG11**, filtres, résumé client |
| `test_statuts.py` | workflow complet, **RG12**, **RG13**, **RG14** (tailleur 403), **RG15**, test unitaire du service sans HTTP |
| `test_paiements.py` | **RG16** (solde, date future, annulée), **RG17**, **RG7** (total < payé → 409), **RG14** (acompte + commentaire) |
| `test_livraisons.py` | **RG18** (adresse, upsert, date prévue), **RG19** (terminee, « Solde impayé : 25 000 FCFA », forçage), **RG20** |
| `test_statistiques.py` | tableau de bord (8 statuts à 0), CA jour/mois, 422 bornes, types, top clients, impayés |
| `test_droits.py` | 401 sans jeton sur 8 routes, 403 accueil → stats / mesures, 403 tailleur → annulation, admin partout, pas de fuite du hash, messages 422 en français |
| `test_scenario_demo.py` | le scénario de démo complet, étape par étape (Annexe A) |
