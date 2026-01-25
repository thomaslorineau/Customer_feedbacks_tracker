# Protection contre la perte de données par Git

Ce document décrit toutes les mesures mises en place pour empêcher Git de causer des pertes de données dans les bases de données PostgreSQL (anciennement DuckDB).

## 🛡️ Protections mises en place

### 1. `.gitignore` renforcé

Tous les fichiers de base de données sont explicitement exclus de Git :

```
*.db
*.duckdb
*.duckdb.wal
*.duckdb.backup
# (Fichiers DuckDB archivés - migration terminée)

# PostgreSQL backups (optionnel selon configuration)
*.sql.backup
backend/backups/
```

### 2. Hook Git `pre-commit`

Un hook Git empêche l'ajout accidentel de fichiers de base de données lors des commits :

- **Emplacement** : `.git/hooks/pre-commit`
- **Fonction** : Bloque tout commit contenant des fichiers `.db`, `.duckdb`, `.duckdb.wal`, ou `.duckdb.backup`
- **Message d'erreur** : Affiche un message clair expliquant pourquoi le commit est bloqué

### 3. Script `update.sh` amélioré

Le script de mise à jour (`scripts/install/update.sh`) inclut maintenant :

#### Avant le pull Git :
- ✅ Vérification de l'intégrité des bases de données
- ✅ Sauvegarde automatique avec rotation (30 dernières)
- ✅ Tentative de réparation si corruption détectée

#### Protection pendant le pull :
- ✅ Exclusion explicite de tous les fichiers DB des opérations Git
- ✅ Suppression des fichiers DB de l'index Git s'ils y sont (ne devrait jamais arriver)
- ✅ Résolution automatique des conflits en conservant la version locale

#### Après le pull Git :
- ✅ Vérification de l'intégrité des bases de données
- ✅ Détection automatique des pertes de données
- ✅ Restauration automatique depuis les backups si données perdues
- ✅ Comptage des posts avant/après pour détecter les pertes

### 4. Script `repair_db.py` amélioré

Le script de réparation (`backend/repair_db.py`) :

- ✅ Compte les posts AVANT toute opération
- ✅ Tente de restaurer depuis les backups automatiques avant de recréer une base vide
- ✅ Vérifie que le backup contient des données avant restauration
- ✅ Crée toujours un backup avant toute modification

## 🔄 Flux de protection lors d'une mise à jour

```
1. Vérification intégrité DB → Si OK, continue
2. Sauvegarde automatique → Création backup avec rotation
3. Exclusion fichiers DB de Git → Protection pendant pull
4. Pull Git → Mise à jour du code uniquement
5. Vérification intégrité DB → Détection problèmes
6. Si données perdues → Restauration automatique depuis backup
7. Vérification finale → Confirmation que tout est OK
```

## 📋 Commandes utiles

### Vérifier l'intégrité des bases de données

```bash
# Production
python backend/scripts/check_db_integrity.py production

# Staging
python backend/scripts/check_db_integrity.py staging

# Les deux
python backend/scripts/check_db_integrity.py both
```

### Créer une sauvegarde manuelle

```bash
# Production
python backend/scripts/backup_db.py production

# Staging
python backend/scripts/backup_db.py staging

# Les deux
python backend/scripts/backup_db.py both --keep=30
```

### Réparer une base de données corrompue

```bash
# Production
python backend/repair_db.py production

# Staging
python backend/repair_db.py staging
```

## ⚠️ Que faire en cas de perte de données ?

1. **Ne pas paniquer** - Les backups automatiques sont créés avant chaque mise à jour
2. **Vérifier les backups** - Liste des backups disponibles :
   ```bash
   ls -lt backend/backups/
   ```
3. **Restaurer depuis un backup** :
   ```bash
   cp backend/backups/production_YYYYMMDD_HHMMSS.duckdb backend/data.duckdb
   ```
4. **Vérifier l'intégrité** :
   ```bash
   python backend/scripts/check_db_integrity.py production
   ```

## 🔍 Vérifications régulières recommandées

- ✅ Vérifier que les backups sont créés régulièrement
- ✅ Vérifier l'intégrité des bases de données après chaque mise à jour
- ✅ S'assurer que `.gitignore` est à jour
- ✅ Vérifier que le hook `pre-commit` est actif

## 📝 Notes importantes

- **Les fichiers de base de données ne doivent JAMAIS être versionnés dans Git**
- **Les backups automatiques sont créés avant chaque mise à jour**
- **Le script `update.sh` détecte et restaure automatiquement les pertes de données**
- **En cas de doute, toujours vérifier l'intégrité avant et après les opérations Git**

