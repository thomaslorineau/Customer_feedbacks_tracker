# Guide de Sauvegarde et Maintenance des Bases de Données

Ce guide explique comment utiliser le système de sauvegarde automatique et de vérification d'intégrité des bases de données DuckDB.

## Vue d'ensemble

Le système comprend :
- **Sauvegardes automatiques** avec rotation (garde les 30 dernières sauvegardes)
- **Vérification d'intégrité** avant les mises à jour
- **Réparation automatique** en cas de corruption détectée
- **Intégration dans `update.sh`** pour une protection automatique

## Scripts disponibles

### 1. Sauvegarde automatique (`backend/scripts/backup_db.py`)

Crée une sauvegarde horodatée des bases de données avec vérification d'intégrité.

**Usage :**
```bash
# Sauvegarder la base de production
python backend/scripts/backup_db.py production

# Sauvegarder la base de staging
python backend/scripts/backup_db.py staging

# Sauvegarder les deux
python backend/scripts/backup_db.py both

# Spécifier le nombre de sauvegardes à garder (défaut: 30)
python backend/scripts/backup_db.py both --keep=50
```

**Via scripts shell :**
```bash
# Linux/Mac
./scripts/backup_db.sh both

# Windows PowerShell
.\scripts\backup_db.ps1 both
```

**Fonctionnalités :**
- ✅ Vérifie l'intégrité avant la sauvegarde
- ✅ Crée des sauvegardes horodatées dans `backend/backups/`
- ✅ Rotation automatique (garde seulement les N dernières)
- ✅ Validation de la sauvegarde après création

### 2. Vérification d'intégrité (`backend/scripts/check_db_integrity.py`)

Vérifie l'intégrité complète des bases de données.

**Usage :**
```bash
# Vérifier la base de production
python backend/scripts/check_db_integrity.py production

# Vérifier la base de staging
python backend/scripts/check_db_integrity.py staging

# Vérifier les deux
python backend/scripts/check_db_integrity.py both
```

**Vérifications effectuées :**
- ✅ Existence du fichier
- ✅ Connexion à la base de données
- ✅ Présence des tables requises
- ✅ Intégrité des données (pas de NULL dans les clés primaires)
- ✅ Présence des séquences nécessaires
- ✅ Comptage des lignes par table

### 3. Réparation (`backend/repair_db.py`)

Répare ou recrée une base de données corrompue.

**Usage :**
```bash
# Réparer la base de production
ENVIRONMENT=production python backend/repair_db.py

# Réparer la base de staging
ENVIRONMENT=staging python backend/repair_db.py
```

**Fonctionnalités :**
- ✅ Crée un backup avant réparation
- ✅ Supprime le fichier corrompu
- ✅ Recrée une base de données vide avec toutes les tables
- ✅ Initialise les tables avec les structures correctes

## Configuration de sauvegardes automatiques

### Linux/Mac (Cron)

Ajoutez cette ligne dans votre crontab pour une sauvegarde quotidienne à 2h du matin :

```bash
crontab -e
```

```cron
# Sauvegarde quotidienne à 2h du matin
0 2 * * * /path/to/scripts/backup_db.sh both >> /path/to/backups/backup.log 2>&1
```

### Windows (Task Scheduler)

1. Ouvrez le **Planificateur de tâches** (Task Scheduler)
2. Créez une nouvelle tâche
3. Configurez :
   - **Déclencheur** : Quotidien à 2h00
   - **Action** : Exécuter un programme
   - **Programme** : `powershell.exe`
   - **Arguments** : `-ExecutionPolicy Bypass -File "C:\path\to\scripts\backup_db.ps1" both`
   - **Répertoire** : `C:\path\to\`

## Intégration dans `update.sh`

Le script `update.sh` intègre maintenant automatiquement :

1. **Vérification d'intégrité** avant la mise à jour
2. **Sauvegarde automatique** si les bases sont valides
3. **Réparation automatique** si corruption détectée
4. **Revérification** après réparation

Vous n'avez rien à faire de spécial, ces vérifications sont automatiques lors de chaque `./update.sh`.

## Structure des sauvegardes

Les sauvegardes sont stockées dans `backend/backups/` avec le format :
```
production_data_YYYYMMDD_HHMMSS.duckdb
staging_data_YYYYMMDD_HHMMSS.duckdb
```

Exemple :
```
backend/backups/
├── production_data_20240115_020000.duckdb
├── production_data_20240116_020000.duckdb
├── staging_data_20240115_020000.duckdb
└── staging_data_20240116_020000.duckdb
```

## Restauration d'une sauvegarde

Pour restaurer une sauvegarde :

```bash
# 1. Arrêter l'application
./stop.sh

# 2. Sauvegarder la base actuelle (au cas où)
cp backend/data.duckdb backend/data.duckdb.old

# 3. Restaurer la sauvegarde souhaitée
cp backend/backups/production_data_20240115_020000.duckdb backend/data.duckdb

# 4. Vérifier l'intégrité
python backend/scripts/check_db_integrity.py production

# 5. Redémarrer l'application
./start.sh
```

## Bonnes pratiques

1. **Sauvegardes régulières** : Configurez des sauvegardes automatiques quotidiennes
2. **Vérification avant mise à jour** : Le script `update.sh` le fait automatiquement
3. **Surveillance** : Vérifiez régulièrement les logs de sauvegarde
4. **Espace disque** : Surveillez l'espace disque dans `backend/backups/`
5. **Sauvegardes externes** : Considérez copier les sauvegardes vers un stockage externe

## Dépannage

### Erreur : "Base de données corrompue"

Si vous voyez cette erreur :
1. Le script tentera automatiquement de réparer
2. Si la réparation échoue, la base sera recréée vide
3. Vous pouvez restaurer depuis une sauvegarde si disponible

### Erreur : "Script introuvable"

Assurez-vous d'être dans le bon répertoire :
```bash
cd /path/to/VibeCoding/backend
python scripts/backup_db.py both
```

### Erreur : "Permission denied" (Linux/Mac)

Rendez les scripts exécutables :
```bash
chmod +x scripts/backup_db.sh
chmod +x backend/scripts/backup_db.py
chmod +x backend/scripts/check_db_integrity.py
```

## Résumé

✅ **Sauvegardes automatiques** : Configurées via cron/Task Scheduler  
✅ **Vérification d'intégrité** : Automatique dans `update.sh`  
✅ **Réparation automatique** : En cas de corruption détectée  
✅ **Rotation des sauvegardes** : Garde les 30 dernières par défaut  
✅ **Validation** : Vérifie l'intégrité avant et après sauvegarde  

Ces améliorations garantissent que vos données sont protégées contre les corruptions et les pertes de données.

