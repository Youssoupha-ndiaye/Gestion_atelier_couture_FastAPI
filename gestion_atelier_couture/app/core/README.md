# `app/core/` — Le cœur technique

Ce dossier ne contient **aucune règle métier** : c'est la « plomberie » utilisée
par toutes les autres couches.

| Fichier | Rôle |
|---|---|
| `config.py` | lit le `.env` (pydantic-settings) |
| `database.py` | moteur SQLAlchemy, sessions, `Base`, `get_db` |
| `constantes.py` | rôles, statuts, modes de paiement, les 18 mesures, les transitions |
| `security.py` | hachage Argon2 + création / décodage JWT |
| `deps.py` | `get_current_user`, `require_role` (les « badges ») |
| `exceptions.py` | exceptions métier + traduction des erreurs en français |

---

## 1. `config.py` — pydantic-settings

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "..."
    SECRET_KEY: str = "..."
```
Au démarrage, `Settings()` lit d'abord les **variables d'environnement**, puis le
fichier **`.env`**, puis les valeurs par défaut. Les types sont validés
(`ACCESS_TOKEN_EXPIRE_MINUTES: int` → "60" devient `60`). `extra="ignore"` évite
une erreur à cause des variables `POSTGRES_*` utilisées seulement par Docker.

➡ Aucun mot de passe dans le code ni dans Git : `.env` est dans `.gitignore`,
seul `.env.example` (valeurs factices) est versionné.

## 2. `database.py` — SQLAlchemy 2

- `engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)` :
  `pool_pre_ping` re-teste une connexion avant de la réutiliser (utile avec Docker).
- `SessionLocal = sessionmaker(...)` : fabrique de sessions.
- `class Base(DeclarativeBase)` : classe mère de tous les modèles.
- `get_db()` avec `yield` : une session **par requête HTTP**, `rollback` en cas
  d'erreur, toujours fermée à la fin. Le `commit` est fait par le routeur.

## 3. `security.py` — Argon2 et JWT

**Argon2 (RG21)** via `pwdlib` :
```python
_hasher = PasswordHash.recommended()     # = Argon2id
hash_password("secret123")  -> "$argon2id$v=19$m=65536,t=3,p=4$..."
verify_password("secret123", hash) -> True
```
On ne stocke jamais le mot de passe, seulement son empreinte. Même deux mots de
passe identiques donnent deux hash différents (sel aléatoire).

**JWT (RG22)** via `PyJWT` :
```python
payload = {"sub": "5", "iat": maintenant, "exp": maintenant + 60 min}
jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```
Le jeton = `en-tête.contenu.signature`. Si quelqu'un modifie le contenu, la
signature ne correspond plus → `decode_token` lève une erreur → 401.
`jwt.decode` vérifie aussi automatiquement `exp` (jeton expiré → 401).

## 4. `deps.py` — injection de dépendances (`Depends`)

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
```
C'est cette ligne qui fait apparaître le bouton **Authorize** dans Swagger.

`get_current_user` :
1. lit l'en-tête `Authorization: Bearer <jeton>` ;
2. décode le jeton (401 « Jeton invalide » / « Jeton expiré ») ;
3. charge l'utilisateur en base ;
4. **vérifie `actif`** → 401 « Compte désactivé » même si le jeton est encore
   valide (RG22). C'est pour ça qu'on relit la base à chaque requête au lieu de
   faire confiance au jeton seul.

`require_role(*roles)` fabrique une dépendance qui renvoie **403** si le rôle ne
convient pas. **L'admin passe toujours** :
```python
autorises = set(roles) | {"admin"}
```
Utilisation dans un routeur : `user = Depends(require_role("tailleur"))`.

## 5. `exceptions.py` — erreurs métier propres

Les services ne connaissent pas HTTP : ils lèvent des exceptions métier.

| Exception | Code HTTP | Exemple |
|---|---|---|
| `NotFoundError` | 404 | client introuvable |
| `ConflictError` | 409 | téléphone déjà utilisé, transition interdite |
| `RegleMetierError` | 422 | remise supérieure au total |
| `ForbiddenError` | 403 | tailleur qui annule une commande |
| `UnauthorizedError` | 401 | mauvais mot de passe |

`register_exception_handlers(app)` (appelé dans `main.py`) les transforme en
`{"detail": "message en français"}`.

Il traduit aussi les **erreurs de validation Pydantic** (en anglais par défaut)
en français :
```json
{"detail": [{"champ": "telephone", "message": "Champ obligatoire", "type": "missing"}]}
```

## 6. `constantes.py`

Une seule source de vérité pour les valeurs autorisées (`ROLES`,
`STATUTS_COMMANDE`, `MODES_PAIEMENT`...), la liste `CHAMPS_MESURES` (utilisée
dans le schéma, le service PATCH et les tests) et le dictionnaire `TRANSITIONS`
du workflow de production.
