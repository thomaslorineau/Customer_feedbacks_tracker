# Archive DuckDB - Migration vers PostgreSQL

Ce dossier contient les fichiers DuckDB archivés après la migration complète vers PostgreSQL.

## Migration effectuée

- **Date de migration** : 25 janvier 2026
- **Nombre de posts migrés** : 591
- **Base de données cible** : PostgreSQL (vibe_tracker)

## Fichiers archivés

Les fichiers DuckDB suivants ont été migrés et peuvent être archivés :

- `backend/data.duckdb` (98M) - Base de données principale
- `backend/data_backup_20260124_235251.duckdb` - Sauvegarde de sécurité
- `backend/backups/production_data_hourly_*.duckdb` - Backups horaires

## Script de migration

Le script de migration est conservé pour référence :
- `backend/scripts/migrate_to_postgres.py`

## Code supprimé

Les fichiers suivants ont été supprimés car obsolètes :

- `backend/app/db.py` - Implémentation DuckDB (remplacée par `db_postgres.py`)
- `backend/scripts/start_staging_duckdb.*` - Scripts de staging DuckDB
- `backend/scripts/check_duckdb_staging.py` - Vérification staging
- `backend/scripts/test_duckdb_*.py` - Tests spécifiques DuckDB
- `backend/scripts/fix_duckdb_sequences.py` - Fix séquences DuckDB

## Scripts archivés (dans `backend/archives/scripts/`)

Les scripts suivants ont été archivés car spécifiques à DuckDB :

- `backend/scripts/backup_db.py` - Script de backup DuckDB (remplacé par backup PostgreSQL dans `worker.py`)
- `backend/scripts/check_db_integrity.py` - Vérification d'intégrité DuckDB
- `backend/scripts/check_db_status.py` - Vérification du statut DuckDB
- `backend/scripts/restore_from_backup.py` - Restauration depuis backup DuckDB

## Scripts utilitaires archivés (dans `scripts/archives/`)

- `scripts/utils/install-duckdb.sh` - Script d'installation DuckDB
- `scripts/utils/check-duckdb.sh` - Script de vérification DuckDB

## Note

Les fichiers DuckDB peuvent être supprimés après vérification que :
1. La migration PostgreSQL est complète et fonctionnelle
2. Les données sont accessibles via l'API
3. Les backups PostgreSQL sont configurés

**⚠️ Ne supprimez les fichiers DuckDB qu'après avoir vérifié que tout fonctionne correctement avec PostgreSQL.**
