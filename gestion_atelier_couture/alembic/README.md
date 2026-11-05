# `alembic/` — Les migrations du schéma

Une **migration** est un script versionné qui fait évoluer la base (créer une
table, ajouter une colonne...). Alembic garde dans la base une table
`alembic_version` qui dit « où on en est ».

> L'énoncé **interdit `Base.metadata.create_all`** : les tables sont créées
> UNIQUEMENT par `alembic upgrade head`. (Il n'y a aucun `create_all` dans le projet,
> même pas dans les tests.)

## Comment je l'ai fait

```bash
alembic init alembic                                   # 1 seule fois : crée alembic/ + alembic.ini
alembic revision --autogenerate -m "schema initial"    # compare les modèles à la base vide
# -> relire le fichier généré dans alembic/versions/ !
alembic upgrade head                                   # crée les 9 tables
```

### Les 2 réglages indispensables dans `env.py`

```python
from app.core.database import Base
import app.models                     # importe TOUS les modèles -> Base.metadata les connaît
target_metadata = Base.metadata       # sinon --autogenerate ne voit aucune table

config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", settings.DATABASE_URL))
```

L'URL (avec le mot de passe) vient donc du `.env` et **n'est pas écrite dans
`alembic.ini`**. J'ai aussi activé `compare_type=True` pour qu'Alembic détecte
les changements de type de colonne lors des futures migrations.

### Ce que j'ai vérifié en relisant la migration générée
- les 9 tables sont présentes (`utilisateurs`, `clients`, `mesures`, `types_vetement`,
  `commandes`, `lignes_commande`, `historique_statuts`, `paiements`, `livraisons`) ;
- les contraintes UNIQUE (email, telephone, numero, nom du catalogue, `livraisons.commande_id`) ;
- les `ON DELETE` : `CASCADE` (mesures, lignes, historique, paiements, livraison) et
  `RESTRICT` (commande → client, commande → mesure : RG4) ;
- les `server_default` (`now()`, `CURRENT_DATE`, `'true'`, `'0'`) ;
- pas d'Enum PostgreSQL (statuts en `String`) → pas de piège d'Enum à la migration.

Une seule migration initiale **complète** (même les tables des paliers 2 et 3),
comme demandé par le guide.

## Commandes utiles

| Commande | Effet |
|---|---|
| `alembic upgrade head` | applique toutes les migrations |
| `alembic downgrade -1` | annule la dernière migration |
| `alembic downgrade base` | supprime tout (retour à zéro) |
| `alembic current` | version actuelle de la base |
| `alembic history` | historique des migrations |
| `alembic upgrade head --sql` | affiche le SQL sans l'exécuter |

Contrôle effectué : `\dt` dans psql affiche les 9 tables + `alembic_version`,
et `downgrade base` puis `upgrade head` fonctionnent sans erreur.
