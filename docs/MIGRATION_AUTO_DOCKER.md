# Migration Automatique au Démarrage Docker

## Fonctionnement

Le conteneur API vérifie automatiquement au démarrage si une migration DuckDB -> PostgreSQL est nécessaire.

## Conditions de Migration Automatique

La migration se lance automatiquement si :
1. ✅ Le fichier `/tmp/data.duckdb` existe dans le conteneur (monté depuis `backend/data.duckdb`)
2. ✅ PostgreSQL est accessible et prêt
3. ✅ Aucune donnée n'existe encore dans PostgreSQL (ou très peu)
4. ✅ La migration n'a pas déjà été effectuée (fichier `.migration_done`)

## Configuration

### Option 1 : Migration Automatique (Recommandé pour première migration)

Dans `docker-compose.yml`, le volume est déjà configuré :

```yaml
volumes:
  - ./backend/data.duckdb:/tmp/data.duckdb:ro
```

**Important** : Si le fichier `backend/data.duckdb` n'existe pas, Docker créera un répertoire vide. Pour éviter cela :

1. **Créer un fichier vide** si vous n'avez pas de DuckDB à migrer :
   ```bash
   touch backend/data.duckdb
   ```

2. **OU** retirer le volume du docker-compose.yml si vous n'avez pas besoin de migration

### Option 2 : Migration Manuelle (Recommandé pour production)

Si vous préférez contrôler manuellement la migration :

1. **Retirer le volume** de `docker-compose.yml` :
   ```yaml
   volumes:
     - ./frontend:/app/frontend:ro
     - ./backend/backups:/app/backups
     # - ./backend/data.duckdb:/tmp/data.duckdb:ro  # Commenté
   ```

2. **Utiliser les scripts manuels** :
   ```bash
   ./scripts/migrate-docker.sh backend/data.duckdb
   ```

## Comportement au Démarrage

### Premier Démarrage (avec DuckDB)

```
==========================================
Docker Entrypoint - VibeCoding API
==========================================

==========================================
Migration automatique DuckDB -> PostgreSQL
==========================================

Fichier DuckDB détecté: /tmp/data.duckdb
Vérification de PostgreSQL...
Attente de PostgreSQL sur postgres:5432...
  Tentative 1/30...
✓ PostgreSQL est prêt
Vérification des données existantes...
Aucune donnée dans PostgreSQL, lancement de la migration...

[Logs de migration...]

✓ Migration réussie!

Initialisation de la base de données...
✓ Base de données initialisée

==========================================
Démarrage de l'API...
==========================================
```

### Démarrages Suivants

```
==========================================
Docker Entrypoint - VibeCoding API
==========================================

Initialisation de la base de données...
✓ Base de données initialisée

==========================================
Démarrage de l'API...
==========================================
```

La migration ne se relance pas car :
- Le fichier `.migration_done` existe
- OU des données existent déjà dans PostgreSQL

## Forcer une Nouvelle Migration

Si vous devez forcer une nouvelle migration :

```bash
# Supprimer le flag de migration
docker-compose exec api rm /app/.migration_done

# Redémarrer le conteneur
docker-compose restart api
```

**Attention** : Cela peut créer des doublons si des données existent déjà. Utilisez `--dry-run` d'abord.

## Désactiver la Migration Automatique

### Méthode 1 : Retirer le volume

Dans `docker-compose.yml`, commentez ou supprimez :
```yaml
- ./backend/data.duckdb:/tmp/data.duckdb:ro
```

### Méthode 2 : Variable d'environnement (à implémenter)

Ajouter dans `docker-compose.yml` :
```yaml
environment:
  - AUTO_MIGRATE=false
```

## Logs de Migration

Les logs de migration apparaissent dans les logs du conteneur :

```bash
# Voir les logs
docker-compose logs api

# Suivre en temps réel
docker-compose logs -f api
```

## Sécurité

- ✅ La migration ne modifie jamais les données existantes (utilise `ON CONFLICT DO NOTHING`)
- ✅ La migration vérifie que PostgreSQL est prêt avant de commencer
- ✅ La migration ne se relance pas automatiquement si déjà effectuée
- ✅ Le fichier DuckDB est monté en lecture seule (`:ro`)

## Dépannage

### Migration ne se lance pas

1. **Vérifier que le fichier existe** :
   ```bash
   docker-compose exec api ls -lh /tmp/data.duckdb
   ```

2. **Vérifier que PostgreSQL est prêt** :
   ```bash
   docker-compose exec postgres pg_isready -U vibe_user -d vibe_tracker
   ```

3. **Vérifier les logs** :
   ```bash
   docker-compose logs api | grep -i migration
   ```

### Migration échoue

1. **Vérifier les logs complets** :
   ```bash
   docker-compose logs api
   ```

2. **Exécuter manuellement pour plus de détails** :
   ```bash
   docker-compose exec api python scripts/migrate_to_postgres.py \
     --duckdb /tmp/data.duckdb \
     --postgres "$DATABASE_URL" \
     --dry-run
   ```

### PostgreSQL n'est pas prêt

Le script attend jusqu'à 60 secondes (30 tentatives × 2 secondes). Si PostgreSQL prend plus de temps :

1. Vérifier les logs PostgreSQL :
   ```bash
   docker-compose logs postgres
   ```

2. Vérifier la santé du conteneur :
   ```bash
   docker-compose ps postgres
   ```

## Recommandations Production

Pour la production, nous recommandons :

1. **Migration manuelle** avant le premier déploiement
2. **Vérification** que tout fonctionne
3. **Suppression** du volume DuckDB de docker-compose.yml
4. **Sauvegarde** de PostgreSQL après migration

Cela évite :
- Les migrations automatiques non désirées
- Les problèmes de timing au démarrage
- Les risques de corruption si le fichier DuckDB change
