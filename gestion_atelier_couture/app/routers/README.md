# `app/routers/` — Les routes HTTP (FastAPI)

Un routeur = un `APIRouter` par domaine, assemblé dans `app/main.py` avec
`app.include_router(router, prefix="/api/v1")`.

> Analogie : le routeur est le **serveur** du restaurant. Il prend la commande,
> vérifie le badge, la transmet au cuisinier (service) et rapporte l'assiette.
> Il ne cuisine jamais : **aucune règle de gestion ici.**

## Le modèle d'une route (toujours le même)

```python
@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED,
             summary="7 · Créer un client (RG1)")
def creer_client(data: ClientCreate,                         # 1. corps validé par Pydantic (422 sinon)
                 db: Session = Depends(get_db),              # 2. session de base
                 _: Utilisateur = Depends(get_current_user)):# 3. badge : 401 si pas connecté
    client = client_service.creer(db, data)                  # 4. le service applique les RG
    db.commit()                                              # 5. on valide
    db.refresh(client)
    return client                                            # 6. filtré par response_model
```

- **`response_model`** filtre la sortie : c'est ce qui garantit qu'aucun
  `mot_de_passe_hash` ne sort jamais.
- **`status_code`** : 201 pour les créations, 204 pour les suppressions.
- **`tags=[...]`** : regroupe les routes par section dans Swagger.
- **`summary="N° · ..."`** : chaque route porte son numéro (1 à 44) pour la démo.
- **Droits** : `Depends(get_current_user)` = tout utilisateur connecté ;
  `Depends(require_role("accueil"))` = accueil + admin (l'admin passe toujours).
- **Paramètres de requête** avec bornes : `limit: int = Query(20, ge=1, le=100)`,
  `q: str | None = Query(None, min_length=2)`.

## Les 44 routes

| N° | Méthode | Route (préfixe `/api/v1`) | Rôle | Fichier |
|---|---|---|---|---|
| 1 | POST | `/auth/login` (formulaire) | public | `auth.py` |
| 2 | GET | `/auth/me` | connecté | `auth.py` |
| 3-6 | POST, GET, GET, PATCH | `/utilisateurs`, `/utilisateurs/{id}` | admin | `utilisateurs.py` |
| 7-10 | POST, GET, GET, PATCH | `/clients`, `/clients/{id}` | tous | `clients.py` |
| 11 | DELETE | `/clients/{id}` | admin | `clients.py` |
| 12 | GET | `/clients/{id}/commandes` | tous | `clients.py` |
| 13 | GET | `/clients/{id}/resume` | tous | `clients.py` |
| 14, 17 | POST, PATCH | `/catalogue`, `/catalogue/{id}` | admin | `catalogue.py` |
| 15, 16 | GET | `/catalogue`, `/catalogue/{id}` | tous | `catalogue.py` |
| 18 | POST | `/clients/{id}/mesures` | tailleur | `mesures.py` |
| 19, 20 | GET | `/clients/{id}/mesures`, `/clients/{id}/mesures/derniere` | tous | `mesures.py` |
| 21 | GET | `/mesures/{id}` | tous | `mesures.py` |
| 22, 23 | PATCH, DELETE | `/mesures/{id}` | tailleur | `mesures.py` |
| 24, 27 | POST, PATCH | `/commandes`, `/commandes/{id}` | accueil | `commandes.py` |
| 25, 26 | GET | `/commandes`, `/commandes/{id}` | tous | `commandes.py` |
| 28 | PATCH | `/commandes/{id}/statut` | tous (tailleur ne peut pas annuler) | `commandes.py` |
| 29 | GET | `/commandes/{id}/historique` | tous | `commandes.py` |
| 30, 31 | POST, DELETE | `/commandes/{id}/lignes`, `/commandes/{id}/lignes/{ligne_id}` | accueil | `commandes.py` |
| 32, 33 | POST, GET | `/commandes/{id}/paiements` | accueil | `paiements.py` |
| 34 | DELETE | `/paiements/{id}` | admin | `paiements.py` |
| 35 | PUT | `/commandes/{id}/livraison` (upsert) | accueil | `livraisons.py` |
| 36 | GET | `/commandes/{id}/livraison` | accueil | `livraisons.py` |
| 37 | POST | `/commandes/{id}/livraison/confirmer` | accueil | `livraisons.py` |
| 38 | GET | `/livraisons` | accueil | `livraisons.py` |
| 39-43 | GET | `/statistiques/{tableau-de-bord, chiffre-affaires, types-vetement, top-clients, impayes}` | admin | `statistiques.py` |
| 44 | GET | `/health` (sans préfixe) | public | `main.py` |

## Détails qui comptent

- **Login = formulaire OAuth2** (`OAuth2PasswordRequestForm`), pas du JSON :
  c'est la condition pour que le bouton **Authorize** de Swagger fonctionne.
- **`/clients/{id}/mesures/derniere`** est déclarée avant toute route qui pourrait
  capturer « derniere » comme un identifiant.
- **PUT livraison** renvoie 201 à la création et 200 à la modification
  (paramètre `response: Response` pour changer le code dynamiquement).
- Les routes qui modifient une commande renvoient le **détail complet** recalculé
  (`commande_service.obtenir` après le commit) : on voit tout de suite le nouveau total / solde.
- **Pagination standard** `Page[T]` : `{"items", "total", "limit", "offset"}`.
