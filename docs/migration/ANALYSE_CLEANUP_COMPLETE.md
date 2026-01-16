# 🧹 Analyse Complète des Fichiers Inutiles

**Date:** 2026-01-16  
**Analyse:** Projet complet (staging + production)

---

## ✅ Fichiers Déjà Supprimés

1. ✅ `backend/ovh_posts.db` - Fichier vide (0 bytes)
2. ✅ `backend/test_db_api.py` - Script obsolète

---

## 📋 Fichiers Identifiés pour Suppression

### 1. `backend/diagnostic.py`
- **Type:** Script Python
- **Utilité:** Diagnostic de l'application (BDD, API, config)
- **Problème:** 
  - Utilise SQLite directement (pas DuckDB)
  - Non utilisé dans le code (aucun import)
  - Remplacé par les nouveaux scripts de test
- **Recommandation:** ❌ **SUPPRIMER**

### 2. `backend/alembic/versions/7ca5f34a1cb9_initial_migration_from_sqlite.py`
- **Type:** Migration Alembic
- **Utilité:** Migration initiale SQLite → PostgreSQL (ancien plan)
- **Problème:**
  - Migration vide (fonctions `upgrade()` et `downgrade()` vides)
  - Créée pour PostgreSQL, pas utilisée pour DuckDB
  - Non référencée dans le code
- **Recommandation:** ❌ **SUPPRIMER** (ou garder si prévu migration future PostgreSQL)

### 3. Fichiers de Logs
- **Type:** Fichiers `.log`
- **Fichiers trouvés:**
  - `backend/backend.log`
  - `backend.log` (à la racine ?)
- **Utilité:** Logs de l'application
- **Recommandation:** 
  - 🔄 **GARDER** mais peut être vidé/archivé périodiquement
  - Les logs sont utiles pour le debugging

### 4. Fichiers `__pycache__`
- **Type:** Cache Python
- **Utilité:** Cache des bytecodes Python
- **Recommandation:**
  - 🔄 **GARDER** (générés automatiquement)
  - Peut être ajouté à `.gitignore` si pas déjà fait

---

## 📊 Analyse des Scripts

### Scripts de Migration (à garder)
- ✅ `migrate_sqlite_to_duckdb.py` - Migration principale
- ✅ `verify_duckdb_migration.py` - Vérification
- ✅ `compare_staging_prod_db.py` - Comparaison
- ✅ `fix_duckdb_sequences.py` - Correction séquences

### Scripts de Test (à garder)
- ✅ `test_duckdb_staging.py` - Tests staging
- ✅ `test_duckdb_production.py` - Tests production
- ✅ `check_duckdb_staging.py` - Vérification staging

### Scripts de Démarrage (à garder)
- ✅ `start_staging_duckdb.ps1` - Démarrage staging (PowerShell)
- ✅ `start_staging_duckdb.bat` - Démarrage staging (Batch)

### Scripts E2E (à garder)
- ✅ `e2e_full_test.py` - Tests end-to-end
- ✅ `e2e_test_real_server.py` - Tests serveur réel
- ✅ `ci_test_endpoints.py` - Tests CI
- ✅ `ci_test_job_persistence.py` - Tests persistance jobs

### Scripts Utilitaires (à garder)
- ✅ `migrate_github_sources.py` - Migration sources GitHub
- ✅ `test_contract.py` - Tests de contrat

---

## 🗂️ Fichiers de Base de Données

### Production
- ✅ `backend/data.duckdb` - **GARDER** (base DuckDB production)
- ✅ `backend/data.db` - **GARDER** (base SQLite production, pour rollback)
- ✅ `backend/data.db.backup` - **GARDER** (backup production)

### Staging
- ✅ `backend/data_staging.duckdb` - **GARDER** (base DuckDB staging)
- ✅ `backend/data_staging.db` - **GARDER** (base SQLite staging, pour rollback)

**Recommandation:** Tous les fichiers de base de données sont nécessaires (actifs + backups)

---

## 📝 Recommandations Finales

### À Supprimer

1. ❌ `backend/diagnostic.py` - Obsolète, non utilisé
2. ❌ `backend/alembic/versions/7ca5f34a1cb9_initial_migration_from_sqlite.py` - Migration vide, non utilisée

### À Garder

- ✅ Tous les scripts de migration/test
- ✅ Tous les fichiers de base de données
- ✅ Les fichiers de logs (utiles pour debugging)
- ✅ Les `__pycache__` (générés automatiquement)

---

## 🎯 Actions Proposées

1. Supprimer `diagnostic.py`
2. Supprimer la migration Alembic vide (ou la garder si migration PostgreSQL prévue)
3. Vérifier `.gitignore` pour exclure `__pycache__` et `.log` si nécessaire

---

**Analyse complétée le:** 2026-01-16


