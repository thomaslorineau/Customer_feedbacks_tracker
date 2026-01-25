# Migration DuckDB -> PostgreSQL en Docker

## Procédure Rapide

### 1. Préparer le fichier DuckDB

Assurez-vous d'avoir le fichier DuckDB à migrer :
- `backend/data.duckdb` (production)
- Ou un backup : `backend/data_backup_*.duckdb`

### 2. Démarrer PostgreSQL

```bash
docker-compose up -d postgres
```

### 3. Exécuter la migration

**Linux/Mac :**
```bash
chmod +x scripts/migrate-docker.sh
./scripts/migrate-docker.sh backend/data.duckdb
```

**Windows :**
```powershell
.\scripts\migrate-docker.ps1 backend\data.duckdb
```

### 4. Vérifier

```bash
# Vérifier le nombre de posts
docker-compose exec postgres psql -U vibe_user -d vibe_tracker -c "SELECT COUNT(*) FROM posts;"

# Tester l'API
curl http://localhost:8000/posts?limit=5
```

## Documentation Complète

Voir [docs/MIGRATION_DOCKER.md](docs/MIGRATION_DOCKER.md) pour la documentation détaillée.
