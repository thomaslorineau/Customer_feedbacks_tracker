# Migration vers PostgreSQL - Guide Complet

## ✅ Migration Terminée

DuckDB a été complètement supprimé et remplacé par PostgreSQL. L'application utilise maintenant **uniquement PostgreSQL**.

## 🚀 Démarrage Rapide

### Option 1 : PostgreSQL Local (sans Docker)

1. **Installer PostgreSQL portable** (sans droits admin) :
   - Télécharger depuis : https://github.com/garethflowers/postgresql-portable/releases
   - Extraire dans `C:\Users\VOTRE_USER\postgresql-portable`

2. **Setup initial** :
   ```powershell
   .\scripts\setup-postgres-local.ps1
   .\scripts\start-postgres-local.ps1
   .\scripts\init-db-local.ps1
   ```

3. **Lancer l'application** :
   ```powershell
   cd backend
   $env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
   uvicorn app.main:app --reload
   ```

### Option 2 : Service Cloud Gratuit

1. **Créer un compte** sur :
   - Supabase : https://supabase.com (recommandé)
   - Neon : https://neon.tech
   - ElephantSQL : https://www.elephantsql.com

2. **Récupérer la connection string** depuis le dashboard

3. **Configurer** :
   ```powershell
   $env:DATABASE_URL = "postgresql://user:password@host:5432/database"
   ```

4. **Initialiser la base** :
   ```powershell
   python scripts/init-db-python.py
   ```

### Option 3 : Docker (si disponible)

```powershell
docker compose -f docker-compose.dev.yml up -d
cd backend
$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
uvicorn app.main:app --reload
```

## 📋 Configuration Requise

### Variables d'environnement

**OBLIGATOIRE** :
```env
DATABASE_URL=postgresql://user:password@host:port/database
```

**Optionnel** :
```env
USE_POSTGRES=true  # Déjà activé par défaut
```

### Installation des dépendances

```bash
pip install -r backend/requirements.txt
```

Le package `psycopg2-binary` est maintenant requis (remplace `duckdb`).

## 🔧 Scripts Disponibles

- `scripts/setup-postgres-local.ps1` - Configuration initiale PostgreSQL portable
- `scripts/start-postgres-local.ps1` - Démarrer PostgreSQL
- `scripts/stop-postgres-local.ps1` - Arrêter PostgreSQL
- `scripts/init-db-local.ps1` - Initialiser la base de données (via psql)
- `scripts/init-db-python.py` - Initialiser la base de données (via Python)

## 🗑️ Fichiers Supprimés

- `backend/app/db.py` - Module DuckDB (supprimé)
- Toutes les références à DuckDB dans le code

## ✨ Améliorations

1. **Meilleure concurrence** : PostgreSQL gère mieux les accès simultanés
2. **Pool de connexions** : Gestion automatique des connexions
3. **Production-ready** : PostgreSQL est plus adapté pour la production
4. **Simplification** : Un seul système de base de données à maintenir

## ⚠️ Notes Importantes

- **DATABASE_URL est maintenant obligatoire** : L'application ne démarre pas sans cette variable
- **Migration des données** : Si vous aviez des données DuckDB, utilisez `scripts/migrate_to_postgres.py`
- **Backups** : Les backups utilisent maintenant `pg_dump` au lieu de copies de fichiers

## 🐛 Dépannage

### Erreur : "DATABASE_URL environment variable is required"

**Solution** : Définir la variable d'environnement :
```powershell
$env:DATABASE_URL = "postgresql://user:password@host:port/database"
```

### Erreur : "psycopg2 not installed"

**Solution** :
```bash
pip install psycopg2-binary
```

### PostgreSQL ne démarre pas

**Vérifier** :
1. PostgreSQL est bien installé dans le chemin attendu
2. Le port 5432 n'est pas déjà utilisé
3. Les logs dans `%USERPROFILE%\postgresql-data\postgres.log`

## 📚 Documentation

- Schéma SQL : `backend/scripts/init_postgres.sql`
- Configuration Docker : `docker-compose.dev.yml`
