# Migration DuckDB -> PostgreSQL en Production (Docker)

Ce guide explique comment migrer les données de DuckDB vers PostgreSQL dans un environnement Docker en production.

## Prérequis

- Docker et Docker Compose installés
- Accès au fichier DuckDB (`backend/data.duckdb` ou backup)
- Les conteneurs PostgreSQL et API configurés dans `docker-compose.yml`

## Procédure de Migration

### Option 1 : Script Automatique (Recommandé)

#### Sur Linux/Mac :

```bash
chmod +x scripts/migrate-docker.sh
./scripts/migrate-docker.sh [chemin/vers/data.duckdb]
```

#### Sur Windows (PowerShell) :

```powershell
.\scripts\migrate-docker.ps1 [chemin\vers\data.duckdb]
```

Le script va :
1. Vérifier que PostgreSQL est démarré
2. Copier le fichier DuckDB dans le conteneur
3. Exécuter la migration
4. Vérifier les résultats

### Option 2 : Migration Manuelle

#### Étape 1 : Préparer l'environnement

```bash
# Démarrer les conteneurs nécessaires
docker-compose up -d postgres

# Attendre que PostgreSQL soit prêt
docker-compose exec postgres pg_isready -U vibe_user -d vibe_tracker
```

#### Étape 2 : Copier le fichier DuckDB

```bash
# Si le conteneur API est déjà démarré
docker cp backend/data.duckdb vibe_api:/tmp/data.duckdb

# OU utiliser un volume monté (ajouter dans docker-compose.yml)
# volumes:
#   - ./backend/data.duckdb:/tmp/data.duckdb:ro
```

#### Étape 3 : Exécuter la migration

```bash
# Obtenir DATABASE_URL depuis docker-compose
export POSTGRES_PASSWORD=$(docker-compose exec -T postgres printenv POSTGRES_PASSWORD)
export DATABASE_URL="postgresql://vibe_user:${POSTGRES_PASSWORD}@postgres:5432/vibe_tracker"

# Exécuter la migration dans le conteneur API
docker-compose exec -e DATABASE_URL="$DATABASE_URL" api \
    python scripts/migrate_to_postgres.py \
    --duckdb /tmp/data.duckdb \
    --postgres "$DATABASE_URL"
```

#### Étape 4 : Vérifier la migration

```bash
# Compter les posts dans PostgreSQL
docker-compose exec postgres psql -U vibe_user -d vibe_tracker \
    -c "SELECT COUNT(*) as total_posts FROM posts;"

# Vérifier par source
docker-compose exec postgres psql -U vibe_user -d vibe_tracker \
    -c "SELECT source, COUNT(*) as count FROM posts GROUP BY source ORDER BY count DESC;"
```

### Option 3 : Migration avec Conteneur Temporaire

Si le conteneur API n'est pas démarré, vous pouvez créer un conteneur temporaire :

```bash
# Obtenir DATABASE_URL
export POSTGRES_PASSWORD=$(docker-compose exec -T postgres printenv POSTGRES_PASSWORD)
export DATABASE_URL="postgresql://vibe_user:${POSTGRES_PASSWORD}@postgres:5432/vibe_tracker"

# Créer un conteneur temporaire avec le fichier monté
docker-compose run --rm \
    -v "$(pwd)/backend/data.duckdb:/tmp/data.duckdb:ro" \
    -e "DATABASE_URL=$DATABASE_URL" \
    api \
    python scripts/migrate_to_postgres.py \
    --duckdb /tmp/data.duckdb \
    --postgres "$DATABASE_URL"
```

## Vérification Post-Migration

### 1. Vérifier les données migrées

```bash
# Total de posts
docker-compose exec postgres psql -U vibe_user -d vibe_tracker \
    -c "SELECT COUNT(*) FROM posts;"

# Statistiques par source
docker-compose exec postgres psql -U vibe_user -d vibe_tracker \
    -c "SELECT source, COUNT(*) FROM posts GROUP BY source;"

# Statistiques par sentiment
docker-compose exec postgres psql -U vibe_user -d vibe_tracker \
    -c "SELECT sentiment_label, COUNT(*) FROM posts GROUP BY sentiment_label;"
```

### 2. Tester l'API

```bash
# Vérifier que l'API fonctionne
curl http://localhost:8000/posts?limit=5

# Vérifier les statistiques
curl http://localhost:8000/api/stats
```

### 3. Comparer avec DuckDB (optionnel)

```bash
# Si DuckDB est installé localement
python3 -c "
import duckdb
conn = duckdb.connect('backend/data.duckdb', read_only=True)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM posts')
print(f'DuckDB: {cur.fetchone()[0]} posts')
conn.close()
"
```

## Dry-Run (Test sans migration)

Pour voir ce qui serait migré sans faire de changements :

```bash
docker-compose exec api \
    python scripts/migrate_to_postgres.py \
    --duckdb /tmp/data.duckdb \
    --postgres "$DATABASE_URL" \
    --dry-run
```

## Gestion des Erreurs

### Erreur : "DuckDB file not found"

- Vérifier que le fichier existe : `ls -lh backend/data.duckdb`
- Vérifier le chemin dans le conteneur : `docker-compose exec api ls -lh /tmp/data.duckdb`

### Erreur : "Connection refused" (PostgreSQL)

- Vérifier que PostgreSQL est démarré : `docker-compose ps postgres`
- Vérifier les logs : `docker-compose logs postgres`
- Attendre que PostgreSQL soit prêt : `docker-compose exec postgres pg_isready`

### Erreur : "duplicate key value violates unique constraint"

- C'est normal si certains posts existent déjà
- Le script utilise `ON CONFLICT DO NOTHING` pour éviter les doublons
- Vérifier les logs pour voir combien de posts ont été ignorés

## Migration depuis un Backup

Si vous avez un backup DuckDB :

```bash
# Restaurer le backup localement (optionnel)
cp backend/data_backup_20260124_235251.duckdb backend/data.duckdb

# Puis suivre la procédure normale
./scripts/migrate-docker.sh backend/data.duckdb
```

## Après la Migration

### 1. Sauvegarder PostgreSQL

```bash
# Créer un backup PostgreSQL
docker-compose exec postgres pg_dump -U vibe_user vibe_tracker > backup_postgres_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Vérifier que tout fonctionne

- Tester l'API
- Vérifier les endpoints critiques
- Surveiller les logs pour les erreurs

### 3. (Optionnel) Supprimer DuckDB

**ATTENTION** : Ne supprimez DuckDB qu'après avoir vérifié que tout fonctionne correctement !

```bash
# Garder une copie de sécurité
cp backend/data.duckdb backend/data.duckdb.backup_migration

# Supprimer (seulement après vérification complète)
# rm backend/data.duckdb
```

## Rollback (en cas de problème)

Si vous devez revenir à DuckDB :

1. Arrêter les conteneurs PostgreSQL
2. Modifier `docker-compose.yml` pour utiliser DuckDB (si nécessaire)
3. Restaurer le fichier DuckDB depuis un backup
4. Redémarrer l'application

**Note** : Après migration vers PostgreSQL, il n'est généralement pas nécessaire de revenir à DuckDB.

## Support

En cas de problème :
1. Vérifier les logs : `docker-compose logs api`
2. Vérifier les logs PostgreSQL : `docker-compose logs postgres`
3. Vérifier la connexion : `docker-compose exec postgres psql -U vibe_user -d vibe_tracker -c "SELECT 1;"`
