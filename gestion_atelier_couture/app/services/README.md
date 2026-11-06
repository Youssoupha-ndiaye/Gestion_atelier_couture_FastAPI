# `app/services/` — Les règles de gestion

C'est **le cœur de la note** : TOUTE la logique métier est ici, jamais dans les
routeurs. Un service reçoit une session `db`, des données déjà validées par
Pydantic et l'utilisateur connecté ; il applique les règles, modifie les objets
SQLAlchemy et **lève des exceptions métier** (`NotFoundError`, `ConflictError`,
`RegleMetierError`, `ForbiddenError`) au lieu de renvoyer des codes HTTP.

> Analogie : le service est le **cuisinier** qui applique les recettes.

Conséquences :
- les services sont **testables sans HTTP** (voir `test_service_transitions_sans_http`) ;
- un service fait `db.flush()` (envoie le SQL, obtient les id) mais **jamais
  `db.commit()`** : c'est le routeur qui valide quand tout s'est bien passé. Si
  une règle échoue au milieu, rien n'est enregistré.

## Fichier par fichier

### `auth_service.py`
- `authentifier()` : **RG23** — même message « Email ou mot de passe incorrect »
  que l'email soit inconnu ou le mot de passe faux (on ne révèle pas quels emails existent).
- `connexion()` : renvoie `access_token`, `token_type`, `expires_in` (secondes).

### `utilisateur_service.py`
- email unique → 409 ; mot de passe haché Argon2 (**RG21**).
- **RG24** : si l'admin se modifie lui-même, interdiction de `actif=False` ou d'un rôle ≠ admin (409).

### `client_service.py`
- **RG1** : `_verifier_telephone_libre(db, tel, exclure_id)` ; en PATCH on exclut
  le client lui-même, donc garder son propre numéro n'est pas un doublon.
- recherche : `ilike` (insensible à la casse) sur nom / prénom / téléphone, filtre
  genre, tri nom puis prénom, `total` calculé avant `limit/offset`.
- **RG4** : client avec au moins une commande → 409 ; sinon suppression (mesures en cascade).

### `catalogue_service.py`
- nom unique (insensible à la casse) → 409 ; `actifs_seulement=True` par défaut.

### `mesure_service.py`
- `creer` : `date_prise` = aujourd'hui par défaut, `prise_par_id` = tailleur connecté.
- **RG3** : `ORDER BY date_prise DESC, id DESC` ; `derniere()` → 404 si aucune.
- `modifier` : **RG2 après fusion** — on calcule l'état final
  `{champ: nouvelle valeur ou valeur actuelle}` et on refuse s'il ne reste aucune mesure.
- **RG4** : mesure référencée par une commande → 409.

### `commande_service.py` (le plus gros)

**`recalculer_montants(commande)` — RG7**, appelée après CHAQUE modification :
```python
somme = Σ quantite × prix_unitaire
remise > somme            -> 422
total = somme - remise
paye  = Σ paiements
total < paye              -> 409   (ex. remise ou suppression de ligne après un acompte)
```

**`creer()`** dans l'ordre du guide :
1. le client existe (404) ;
2. **RG9** `_resoudre_mesure` : mesure donnée → doit être du même client (422) ;
   absente → dernières mesures du client, ou `None` ;
3. **RG6** `_construire_ligne` : prestation active (422 sinon), `prix_unitaire`
   par défaut = `prix_base`, **copié** dans la ligne ;
4. **RG8** date prévue = aujourd'hui + `max(delai_jours)` ; jamais avant la date de commande ;
5. statut `en_attente`, `recalculer_montants` ;
6. `db.flush()` → l'id existe → **RG5** `numero = f"CMD-{annee}-{id:05d}"` ;
7. **RG15** historique initial `NULL → en_attente`.

**`changer_statut()`** — section 5.1, l'**ordre** des contrôles donne le bon code :
1. **RG12** statut actuel livree/annulee → 409 ;
2. **RG13** même statut → 409 ; « livree » demandé → 409 (passe par la confirmation) ;
3. transition absente de `TRANSITIONS` → 409 **avec la liste des statuts possibles** ;
4. **RG14** annulation : tailleur → 403 ; acompte versé sans commentaire → 422 ;
5. **RG15** ligne d'historique puis changement de statut.

L'accueil n'est pas bloqué en 403 avant le contrôle de transition : il reçoit
409 « Statuts possibles : ... » (étape 4 de l'Annexe A).

**`condition_en_retard()` — RG11** en SQL (pour le filtre `en_retard=true` et le
tableau de bord) ; la même règle existe en Python dans `Commande.en_retard`.

**`ajouter_ligne` / `supprimer_ligne` — RG10** : seulement en `en_attente`, il
doit toujours rester au moins une ligne, puis `recalculer_montants`.

`fcfa(25000)` → « 25 000 FCFA » pour des messages lisibles.

### `paiement_service.py`
- **RG16** : commande annulée → 409 ; montant > solde → 409 « Montant supérieur au
  solde restant (25 000 FCFA) » ; (montant > 0 et date non future sont vérifiés
  par le schéma → 422).
- Le paiement reste possible sur une commande **livrée avec solde impayé** (sinon
  on ne pourrait jamais récupérer cet argent).
- **RG17** : suppression (admin) puis `recalculer_montants`.

### `livraison_service.py`
- `planifier()` = **upsert** (crée ou modifie l'unique livraison), **RG18** met
  `commande.date_livraison_prevue = date_prevue` ; refus sur commande livrée/annulée.
- `confirmer()` : **RG19** statut `terminee` sinon 409 ; solde > 0 sans
  `autoriser_solde_impaye` → 409 « Solde impayé : 25 000 FCFA » ; si forcé →
  mention dans l'historique. **RG20** : statut `livree`, `date_livraison_reelle`
  et `date_effective` = aujourd'hui ; sans planification, une livraison
  `retrait_atelier` est créée.

### `statistiques_service.py`
- CA = Σ `montant_total` des commandes **non annulées** par `date_commande` ;
  encaissé = Σ paiements par `date_paiement` ; reste = Σ (total − payé) non annulées.
- **8 statuts même à 0** : `{s: 0 for s in STATUTS_COMMANDE}` puis remplissage par `GROUP BY`.
- granularité mois : `func.date_trunc("month", ...)` (PostgreSQL) ; toutes les
  périodes de l'intervalle sont renvoyées (même vides) pour un graphique continu.
- `func.sum`, `func.count`, `group_by`, `func.coalesce(..., 0)` (sinon `NULL` quand il n'y a rien).
