# `app/schemas/` — Validation des données avec Pydantic v2

Pydantic **valide et convertit** les données qui entrent et qui sortent de l'API.
On écrit une classe avec des types ; si le JSON reçu ne correspond pas, FastAPI
renvoie automatiquement **422** avec le champ fautif (traduit en français par
`app/core/exceptions.py`) — la route n'est même pas exécutée.

> Analogie du restaurant : Pydantic est celui qui vérifie que la commande du
> client est lisible et complète **avant** de l'envoyer en cuisine (les services).

---

## 1. Les 3 schémas par ressource (exigés par l'énoncé)

| Schéma | Sens | Règle |
|---|---|---|
| `XxxCreate` | entrée (POST) | champs obligatoires sans valeur par défaut |
| `XxxUpdate` | entrée (PATCH) | **tous** les champs `\| None = None` |
| `XxxRead` | sortie | contient `id`, `created_at`... **jamais** de hash |

Exemple réel (`client.py`) :
```python
class ClientCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)     # obligatoire, non vide
    telephone: str                                     # obligatoire
    email: EmailStr | None = None                      # facultatif, format email vérifié
    genre: Genre | None = None                         # Literal["homme","femme","enfant"]

class ClientUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1)   # facultatif en PATCH

class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)       # lit un objet SQLAlchemy
    id: int
    created_at: datetime
```

## 2. Les outils Pydantic utilisés, un par un

### `Field(...)` — contraintes sur un champ
| Où | Contrainte | Règle |
|---|---|---|
| `mesure.py` | `Field(gt=0, le=300)` sur les 18 mesures | RG2 |
| `utilisateur.py` | `mot_de_passe: str = Field(min_length=8)` | RG21 |
| `catalogue.py` | `prix_base: int = Field(ge=0)` | montant ≥ 0 |
| `commande.py` | `lignes: list[LigneCreate] = Field(min_length=1)` | au moins une ligne |
| `commande.py` | `quantite: int = Field(default=1, ge=1)` | |
| `paiement.py` | `montant: int = Field(gt=0)` | RG16 |

`gt` = strictement supérieur, `ge` = supérieur ou égal, `le` = inférieur ou égal.

### `@field_validator` — nettoyer / vérifier UN champ
RG1, normalisation du téléphone (`client.py`) :
```python
@field_validator("telephone")
@classmethod
def _tel(cls, v: str) -> str:
    v = re.sub(r"[\s.\-()]", "", v)                  # "77 123 45 67" -> "771234567"
    if not re.fullmatch(r"\+?\d{6,20}", v):
        raise ValueError("Numéro invalide : 6 à 20 chiffres, '+' initial facultatif")
    return v                                         # la valeur RETOURNÉE remplace l'originale
```
Comme la valeur est normalisée **avant** d'arriver au service, la vérification
d'unicité en base compare toujours des numéros au même format : « 77 123 45 67 »
et « 77.123.45.67 » sont bien détectés comme doublons (409).

Autres `field_validator` : email mis en minuscules (`utilisateur.py`), date de
paiement pas dans le futur (`paiement.py`, RG16).

### `@model_validator(mode="after")` — règle sur PLUSIEURS champs
RG2, au moins une mesure (`mesure.py`) :
```python
@model_validator(mode="after")
def au_moins_une_mesure(self):
    if all(getattr(self, c) is None for c in CHAMPS_MESURES):
        raise ValueError("Au moins une mesure doit être renseignée")
    return self
```
`mode="after"` = exécuté une fois tous les champs validés individuellement.

Autre usage : **interdire de vider** un champ obligatoire en PATCH
(`ClientUpdate`, `UtilisateurUpdate`, `CommandeUpdate`...) :
```python
for champ in ("nom", "prenom", "telephone"):
    if champ in self.model_fields_set and getattr(self, champ) is None:
        raise ValueError(f"Le champ {champ} est obligatoire et ne peut pas être vidé")
```
`model_fields_set` = l'ensemble des champs **réellement envoyés** dans le JSON.
Ça permet de distinguer « champ absent » (on ne touche pas) de « champ envoyé à
null » (refusé pour nom/prénom/téléphone, autorisé pour une mesure qu'on efface).

### `Literal[...]` — limiter les valeurs possibles
Défini une seule fois dans `app/core/constantes.py` :
```python
Role = Literal["admin", "tailleur", "accueil"]
StatutCommande = Literal["en_attente", "en_coupe", ..., "annulee"]
ModePaiement = Literal["especes", "wave", "orange_money", "virement", "cheque"]
```
Swagger affiche alors une liste déroulante, et toute autre valeur → 422
« Valeur non autorisée. Valeurs possibles : ... ».

### `EmailStr` — format email (nécessite `email-validator`)

### `ConfigDict(str_strip_whitespace=True)`
Supprime les espaces autour des chaînes : `"  Diop "` devient `"Diop"`, et
`"   "` devient `""` → refusé par `min_length=1`.

### `ConfigDict(from_attributes=True)` — construire un Read depuis SQLAlchemy
Sans ce réglage, Pydantic ne sait lire que des dictionnaires. Avec, il lit les
**attributs** d'un objet : `ClientRead.model_validate(client_sqlalchemy)`.
FastAPI le fait tout seul grâce à `response_model=ClientRead`.

Bonus : les **propriétés Python** du modèle sont lues comme des colonnes. C'est
ainsi que `solde`, `en_retard`, `client_nom`, `sous_total`, `nom_prestation`
apparaissent dans le JSON sans exister en base (voir `app/models/README.md`).

### `model_dump(exclude_unset=True)` — le PATCH partiel
Dans les services :
```python
changements = data.model_dump(exclude_unset=True)   # SEULEMENT les champs envoyés
for champ, valeur in changements.items():
    setattr(client, champ, valeur)
```
Sans `exclude_unset=True`, un PATCH `{"adresse": "Médina"}` remettrait `nom`,
`prenom`... à `None` ! (piège n°6 de la checklist du guide).

### Héritage de schémas
- `_ChampsMesures` contient les 18 mesures ; `MesureCreate`, `MesureUpdate` et
  `MesureRead` en héritent (pas de copier-coller de 18 lignes × 3).
- `CommandeDetail(CommandeListItem)` : le détail = la version liste + lignes,
  paiements, livraison.

### Génériques : `Page[T]` (`common.py`)
```python
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```
`response_model=Page[ClientRead]` → Swagger documente exactement la forme
`{"items": [ClientRead...], "total": ..., "limit": ..., "offset": ...}`.

## 3. Fichiers

| Fichier | Schémas |
|---|---|
| `common.py` | `Page[T]`, `Message` |
| `auth.py` | `Token` (`access_token`, `token_type`, `expires_in` en secondes) |
| `utilisateur.py` | `UtilisateurCreate / Update / Read` (Read sans hash) |
| `client.py` | `ClientCreate / Update / Read`, `ClientResume`, `normaliser_telephone()` |
| `catalogue.py` | `TypeVetementCreate / Update / Read` |
| `mesure.py` | `MesureCreate / Update / Read` |
| `commande.py` | `LigneCreate / Read`, `CommandeCreate / Update`, `StatutUpdate`, `HistoriqueRead`, `CommandeListItem`, `CommandeDetail` |
| `paiement.py` | `PaiementCreate / Read` |
| `livraison.py` | `LivraisonUpsert / Read`, `LivraisonTournee` |
| `statistiques.py` | réponses des 5 routes de statistiques |

## 4. Où va quelle validation ?

- **Forme** de la donnée (type, bornes, format, champ obligatoire) → **schéma Pydantic**.
- Validation qui a besoin de **la base** (doublon, appartenance, solde...) → **service**.

Exemple RG1 : le format du téléphone est vérifié dans le schéma (422), l'unicité
dans `client_service` (409).

## 5. Forme d'une erreur 422

```json
{
  "detail": [
    {"champ": "telephone", "message": "Numéro invalide : 6 à 20 chiffres, '+' initial facultatif", "type": "value_error"}
  ]
}
```
