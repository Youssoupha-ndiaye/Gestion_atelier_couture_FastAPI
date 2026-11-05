# `app/models/` — Les tables (SQLAlchemy 2)


## Comment je l'ai fait

### 1. Le style moderne SQLAlchemy 2 (imposé par l'énoncé)

```python
class Client(Base):                      # Base vient de app/core/database.py
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    telephone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255))   # "| None" => colonne NULL autorisée
```

- `Mapped[int]` + `mapped_column(...)` : colonne typée (et PAS l'ancien `Column(...)`).
- `Mapped[str | None]` : la colonne accepte NULL ; `Mapped[str]` : NOT NULL.
- `server_default=func.now()` : c'est PostgreSQL qui remplit la date.
- `onupdate=func.now()` : `updated_at` se met à jour à chaque modification.

### 2. Les fichiers

| Fichier | Tables | Remarques |
|---|---|---|
| `utilisateur.py` | `utilisateurs` | `mot_de_passe_hash` (Argon2), `role`, `actif` |
| `client.py` | `clients` | `telephone` UNIQUE (RG1) |
| `mesure.py` | `mesures` | 18 colonnes Float nullable, FK client `ON DELETE CASCADE` |
| `catalogue.py` | `types_vetement` | `nom` UNIQUE, `prix_base` / `delai_jours` en Integer |
| `commande.py` | `commandes`, `lignes_commande`, `historique_statuts` | le cœur du métier |
| `paiement.py` | `paiements` | `montant` Integer FCFA |
| `livraison.py` | `livraisons` | `commande_id` UNIQUE → 0 ou 1 livraison par commande |
| `__init__.py` | — | importe TOUT (indispensable pour Alembic) |

### 3. Les relations


`relationship(back_populates=...)` permet de naviguer dans les deux sens :
`client.commandes` et `commande.client`.

### 4. Les choix importants

- **Montants = `Integer`** (FCFA), jamais `Float` (erreurs d'arrondi).
- **Statuts = `String`** + validation `Literal` côté Pydantic (plus simple avec
  Alembic que les Enum natives PostgreSQL). Les valeurs autorisées sont dans
  `app/core/constantes.py`.
- **Champs calculés = `@property`** et non des colonnes :
  - `Commande.solde` = `montant_total - montant_paye` (RG7)
  - `Commande.en_retard` = date prévue dépassée et statut ∉ {livree, annulee} (RG11)
  - `LigneCommande.sous_total` = `quantite × prix_unitaire`
  - `LigneCommande.nom_prestation`, `Commande.client_nom`

  Pydantic (avec `from_attributes=True`) lit ces propriétés comme des attributs
  normaux : ils apparaissent donc dans le JSON sans être stockés.
- **`prix_unitaire` est COPIÉ** dans la ligne : si le patron change le prix du
  catalogue, les anciennes commandes ne bougent pas.
- **`Commande.numero` est nullable** en base car il est fixé juste après le
  `db.flush()` qui donne l'id (RG5) ; en pratique il est toujours rempli.

## Règle d'or
Un modèle n'est **jamais renvoyé tel quel** par une route : on passe toujours par
un schéma Pydantic `XxxRead` (voir `app/schemas/README.md`), sinon on risquerait
de renvoyer `mot_de_passe_hash`.
