# Docker — Livrer l'API en conteneurs

Fichiers concernés (à la racine) : `Dockerfile`, `entrypoint.sh`,
`docker-compose.yml`, `.dockerignore`, et ici `docker/initdb/`.

## Lancer

```bash
cp .env.example .env            # puis changer SECRET_KEY et les mots de passe
docker compose up --build       # 1er lancement (construit l'image)
# -> http://localhost:8000/docs
docker compose up -d            # lancements suivants, en arrière-plan
docker compose logs -f api      # voir les logs de l'API
docker compose exec api pytest -v   # lancer les tests DANS le conteneur
docker compose down             # arrêter
docker compose down -v          # arrêter ET effacer la base (volume)
```

## Comment je l'ai fait

### 1. `docker-compose.yml` : 2 services

| Service | Image | Rôle |
|---|---|---|
| `db` | `postgres:17` | la base ; données dans le volume `db_data` (survivent aux redémarrages) |
| `api` | construite par le `Dockerfile` | l'API FastAPI sur le port 8000 |

Points clés :
- **`healthcheck` avec `pg_isready`** sur `db` + **`depends_on: condition: service_healthy`**
  sur `api` : l'API ne démarre que lorsque PostgreSQL accepte les connexions.
- **`env_file: .env`** : l'API reçoit SECRET_KEY, ADMIN_EMAIL... depuis le `.env`.
- **Le piège de l'hôte** : dans le `.env`, `DATABASE_URL` pointe sur `localhost`
  (pour lancer l'API en local). Mais dans un conteneur, `localhost` = le conteneur
  lui-même ! La base s'appelle `db` (nom du service). La section `environment:`
  **remplace** donc `DATABASE_URL` par une URL avec `@db:5432` — on n'a rien à
  modifier à la main en passant du local à Docker.
- `docker/initdb/01-base-de-test.sql` est monté dans `/docker-entrypoint-initdb.d` :
  l'image postgres l'exécute au premier démarrage et crée `atelier_test`, ce qui
  permet `docker compose exec api pytest`.

### 2. `Dockerfile`
```dockerfile
FROM python:3.12-slim                  # image légère, version Python de référence
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # couche mise en cache
COPY app/ alembic/ alembic.ini ... ./                # puis le code
CMD ["./entrypoint.sh"]
```
On copie `requirements.txt` **avant** le code : tant qu'il ne change pas, Docker
réutilise la couche des dépendances et le rebuild prend quelques secondes.
Le `sed 's/\r$//'` protège contre les fins de ligne Windows (sinon erreur
« /bin/sh^M: not found » quand le projet est cloné sous Windows).

### 3. `entrypoint.sh` : la séquence de démarrage
1. **attendre la base** (boucle de 30 essais × 2 s avec SQLAlchemy) ;
2. **`alembic upgrade head`** → crée / met à jour les tables (jamais `create_all`) ;
3. **`python -m app.seed`** → admin + comptes démo + catalogue (idempotent : relançable) ;
4. **`exec uvicorn app.main:app --host 0.0.0.0 --port 8000`**
   (`0.0.0.0` sinon l'API n'est pas joignable depuis l'extérieur du conteneur ;
   `exec` pour qu'uvicorn reçoive proprement le signal d'arrêt).

### 4. `.dockerignore`
Exclut `.venv`, `.git`, `.env`, caches : image plus petite et **le `.env` n'est
jamais copié dans l'image** (il est fourni au démarrage par `env_file`).

## Vérification effectuée
La séquence de `entrypoint.sh` a été exécutée sur une base PostgreSQL vide :
migration appliquée, seed créé (admin, accueil, tailleur, 7 prestations),
`GET /health` → `{"status":"ok"}`, login admin → jeton JWT.
Le fichier compose est validé par `docker compose config`.

## Différence avec mon premier essai
Le premier `Dockerfile` lançait `uvicorn src.main:app` et copiait seulement
`app/` : il manquait Alembic, le seed et l'attente de la base, et l'URL de la
base utilisait le driver par défaut. Tout est maintenant géré par `entrypoint.sh`.
