#!/bin/bash
# Script de mise à jour de l'application via git
# Usage: ./update.sh

# Obtenir le répertoire du script (scripts/install/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Remonter à la racine du projet (2 niveaux: scripts/install -> scripts -> racine)
# Mais aussi vérifier si on est déjà à la racine ou dans scripts/
if [ -f "$SCRIPT_DIR/../../.git/config" ] || [ -d "$SCRIPT_DIR/../../.git" ]; then
    # On est dans scripts/install/, remonter de 2 niveaux
    APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
elif [ -f "$SCRIPT_DIR/../.git/config" ] || [ -d "$SCRIPT_DIR/../.git" ]; then
    # On est dans scripts/, remonter d'1 niveau
    APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/.git/config" ] || [ -d "$SCRIPT_DIR/.git" ]; then
    # On est déjà à la racine
    APP_DIR="$SCRIPT_DIR"
else
    # Par défaut, essayer de remonter de 2 niveaux
    APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# S'assurer qu'on est dans le bon répertoire
cd "$APP_DIR" || {
    echo "Erreur: Impossible de se déplacer dans le répertoire: $APP_DIR" >&2
    echo "SCRIPT_DIR: $SCRIPT_DIR" >&2
    exit 1
}

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

debug() {
    # Fonction debug (peut être désactivée en production)
    if [ "${DEBUG:-0}" = "1" ]; then
        echo -e "${BLUE}🔍 DEBUG: $1${NC}"
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Mise à jour de l'application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier que c'est un dépôt git
if [ ! -d ".git" ]; then
    error "Ce répertoire n'est pas un dépôt git"
    echo "   Utilisez install.sh pour installer l'application"
    exit 1
fi

# 1. Arrêter l'application si elle tourne
info "Arrêt de l'application..."
if [ -f "backend/server.pid" ]; then
    PID=$(cat backend/server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        if [ -f "scripts/app/stop.sh" ]; then
            bash scripts/app/stop.sh > /dev/null 2>&1
        elif [ -f "stop.sh" ]; then
            ./stop.sh > /dev/null 2>&1
        else
            kill $PID 2>/dev/null || true
        fi
        sleep 2
        success "Application arrêtée"
    else
        rm -f backend/server.pid
        info "Application déjà arrêtée"
    fi
else
    info "Application non démarrée"
fi
echo ""

# 2. Vérifier l'intégrité des bases de données AVANT la mise à jour
info "Vérification de l'intégrité des bases de données..."
cd "$APP_DIR/backend" || {
    error "Impossible de se déplacer dans le répertoire backend"
    exit 1
}

# Activer l'environnement virtuel si disponible
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Vérifier l'intégrité des bases de données
DB_INTEGRITY_OK=true
if [ -f "scripts/check_db_integrity.py" ]; then
    if python scripts/check_db_integrity.py both > /dev/null 2>&1; then
        success "Intégrité des bases de données vérifiée"
    else
        warning "⚠️  Corruption détectée dans au moins une base de données"
        DB_INTEGRITY_OK=false
        
        # Essayer de réparer automatiquement
        info "Tentative de réparation automatique..."
        if [ -f "repair_db.py" ]; then
            # Réparer la base de production
            if [ -f "data.duckdb" ]; then
                info "Réparation de la base de données de production..."
                ENVIRONMENT=production python repair_db.py
            fi
            # Réparer la base de staging
            if [ -f "data_staging.duckdb" ]; then
                info "Réparation de la base de données de staging..."
                ENVIRONMENT=staging python repair_db.py
            fi
            
            # Revérifier après réparation
            if python scripts/check_db_integrity.py both > /dev/null 2>&1; then
                success "Bases de données réparées avec succès"
                DB_INTEGRITY_OK=true
            else
                error "❌ Impossible de réparer les bases de données"
                warning "   Les bases de données seront recréées vides lors du redémarrage"
            fi
        else
            warning "Script repair_db.py introuvable, réparation impossible"
        fi
    fi
else
    warning "Script check_db_integrity.py introuvable, vérification ignorée"
fi

cd "$APP_DIR" || {
    error "Impossible de revenir au répertoire racine"
    exit 1
}
echo ""

# 2b. Sauvegarde automatique des bases de données (avec rotation)
info "Sauvegarde automatique des bases de données..."
cd "$APP_DIR/backend" || {
    error "Impossible de se déplacer dans le répertoire backend"
    exit 1
}

# Activer l'environnement virtuel si disponible (au cas où)
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Vérifier l'intégrité AVANT la sauvegarde
if [ -f "scripts/check_db_integrity.py" ]; then
    info "Vérification de l'intégrité des bases de données avant mise à jour..."
    if python scripts/check_db_integrity.py both > /dev/null 2>&1; then
        success "Intégrité des bases de données vérifiée"
    else
        warning "⚠️  Problème d'intégrité détecté, tentative de réparation..."
        python scripts/repair_db.py production > /dev/null 2>&1 || true
        python scripts/repair_db.py staging > /dev/null 2>&1 || true
    fi
fi

if [ -f "scripts/backup_db.py" ]; then
    if python scripts/backup_db.py both --keep=30 > /dev/null 2>&1; then
        success "Sauvegarde automatique créée avec succès"
    else
        warning "⚠️  Échec de la sauvegarde automatique (continuation de la mise à jour)"
    fi
else
    warning "Script backup_db.py introuvable, sauvegarde automatique ignorée"
fi

cd "$APP_DIR" || {
    error "Impossible de revenir au répertoire racine"
    exit 1
}
echo ""

# 2c. Sauvegarder la configuration
info "Sauvegarde de la configuration..."
BACKUP_DIR="$APP_DIR/.update_backup"
mkdir -p "$BACKUP_DIR"

# Sauvegarder les fichiers de configuration
if [ -f "backend/.env" ]; then
    cp backend/.env "$BACKUP_DIR/.env.backup"
    success "Configuration .env sauvegardée"
fi

if [ -f "backend/.app_config" ]; then
    cp backend/.app_config "$BACKUP_DIR/.app_config.backup"
    success "Configuration .app_config sauvegardée"
fi

if [ -f ".host_alias" ]; then
    cp .host_alias "$BACKUP_DIR/.host_alias.backup"
    success "Configuration alias sauvegardée"
fi

# Sauvegarder les scripts locaux qui peuvent être modifiés
if [ -f "backup.sh" ]; then
    cp backup.sh "$BACKUP_DIR/backup.sh.backup"
    cp backup.sh "$BACKUP_DIR/backup.sh.local"
    success "Script backup.sh sauvegardé"
fi

if [ -f "configure_cors.sh" ]; then
    cp configure_cors.sh "$BACKUP_DIR/configure_cors.sh.backup"
    cp configure_cors.sh "$BACKUP_DIR/configure_cors.sh.local"
    success "Script configure_cors.sh sauvegardé"
fi

if [ -f "update.sh" ]; then
    cp update.sh "$BACKUP_DIR/update.sh.local"
    success "Script update.sh sauvegardé"
fi

# Sauvegarder aussi scripts/install/update.sh (le script lui-même)
if [ -f "scripts/install/update.sh" ]; then
    cp scripts/install/update.sh "$BACKUP_DIR/update.sh.install.local"
    success "Script scripts/install/update.sh sauvegardé"
fi

# Sauvegarder aussi les bases de données (juste pour sécurité, on ne la restaure pas)
if [ -f "backend/data.db" ]; then
    cp backend/data.db "$BACKUP_DIR/data.db.backup"
    info "Base de données SQLite sauvegardée (sécurité)"
fi
if [ -f "backend/data.duckdb" ]; then
    cp backend/data.duckdb "$BACKUP_DIR/data.duckdb.backup"
    info "Base de données DuckDB sauvegardée (sécurité)"
fi
if [ -f "backend/data_staging.duckdb" ]; then
    cp backend/data_staging.duckdb "$BACKUP_DIR/data_staging.duckdb.backup"
    info "Base de données DuckDB staging sauvegardée (sécurité)"
fi

echo ""

# 3. Mettre à jour le code
info "Mise à jour du code depuis Stash..."

# Vérifier s'il y a des modifications locales (en excluant data.db et autres fichiers de DB)
HAS_CHANGES=false

# D'abord, résoudre les conflits avec les fichiers de base de données s'il y en a
DB_FILES="backend/data.db backend/data.duckdb backend/data_staging.duckdb backend/data_staging.duckdb.wal"
for db_file in $DB_FILES; do
    if git status --porcelain 2>/dev/null | grep -q "^UU.*$db_file\|^AA.*$db_file"; then
        warning "Conflit de merge détecté avec $db_file, résolution automatique..."
        info "Conservation de la version locale de $db_file..."
        git checkout --ours "$db_file" 2>/dev/null || true
        git add "$db_file" 2>/dev/null || true
    fi
done

# Exclure les fichiers de base de données, configuration locale et scripts locaux
# IMPORTANT: Exclure aussi scripts/install/update.sh pour éviter les conflits avec le script lui-même
EXCLUDE_PATTERNS="-- ':!backend/data.db' ':!backend/data.duckdb' ':!backend/data_staging.duckdb' ':!backend/data_staging.duckdb.wal' ':!backend/*.db' ':!backend/*.duckdb' ':!backend/*.wal' ':!backend/*.log' ':!backend/__pycache__' ':!backend/**/__pycache__' ':!backend/.app_config' ':!backup.sh' ':!configure_cors.sh' ':!scripts/install/update.sh' ':!update.sh'"

# Vérifier les modifications (sans les fichiers exclus)
if ! git diff --quiet $EXCLUDE_PATTERNS 2>/dev/null || ! git diff --cached --quiet $EXCLUDE_PATTERNS 2>/dev/null; then
    HAS_CHANGES=true
    warning "Modifications locales détectées"
    info "Sauvegarde temporaire des modifications (stash)..."
    
    # Essayer de stash en excluant les fichiers problématiques
    if git stash push $EXCLUDE_PATTERNS -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" 2>/dev/null; then
        success "Modifications sauvegardées temporairement"
    else
        # Si le stash échoue, essayer de résoudre les conflits avec les fichiers de DB
        warning "Conflit détecté avec des fichiers de base de données, résolution automatique..."
        
        # Résoudre les conflits avec tous les fichiers de DB
        for db_file in $DB_FILES; do
            if git status --porcelain | grep -q "$db_file"; then
                info "Résolution du conflit avec $db_file (conservation de la version locale)..."
                git checkout --ours "$db_file" 2>/dev/null || true
                git add "$db_file" 2>/dev/null || true
            fi
        done
        
        # Réessayer le stash
        if git stash push $EXCLUDE_PATTERNS -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" 2>/dev/null; then
            success "Modifications sauvegardées temporairement (après résolution)"
        else
            error "Impossible de sauvegarder les modifications locales"
            echo "   Résolvez les conflits manuellement ou commitez vos changements"
            echo "   Utilisez 'git status' pour voir les fichiers modifiés"
            echo ""
            echo "   Pour résoudre manuellement :"
            echo "   1. git checkout --ours backend/data.db backend/data.duckdb  # Garder vos versions locales"
            echo "   2. git add backend/data.db backend/data.duckdb"
            echo "   3. Relancez ./update.sh"
            exit 1
        fi
    fi
    echo ""
fi

# Forcer la résolution des fichiers de config AVANT le pull
# On sauvegarde, puis on supprime temporairement ces fichiers pour permettre le pull
# IMPORTANT: Inclure scripts/install/update.sh (le script lui-même) pour éviter les conflits
CONFIG_FILES="backend/data.db backend/data.duckdb backend/data_staging.duckdb backend/data_staging.duckdb.wal backend/.app_config backup.sh configure_cors.sh update.sh scripts/install/update.sh"
for file in $CONFIG_FILES; do
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Vérifier s'il y a des modifications locales (staged ou unstaged)
    HAS_MODS=false
    if ! git diff --quiet "$file" 2>/dev/null; then
        HAS_MODS=true
    fi
    if ! git diff --cached --quiet "$file" 2>/dev/null; then
        HAS_MODS=true
    fi
    
    # Vérifier aussi si le fichier est suivi par Git
    IS_TRACKED=false
    if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        IS_TRACKED=true
    fi
    
    if [ "$HAS_MODS" = true ] || [ "$IS_TRACKED" = true ]; then
        info "Mise en pause temporaire des modifications locales de $file (pour permettre le pull)..."
        # S'assurer qu'on a bien sauvegardé la version locale
        local_backup="$BACKUP_DIR/$(basename $file).local"
        if [ ! -f "$local_backup" ]; then
            cp "$file" "$local_backup" 2>/dev/null || true
        fi
        
        # Supprimer temporairement le fichier pour permettre le pull
        # (on le restaurera après)
        if [ "$IS_TRACKED" = true ]; then
            # Fichier suivi : reset et checkout HEAD
            git reset HEAD -- "$file" 2>/dev/null || true
            git checkout HEAD -- "$file" 2>/dev/null || true
            # Si ça ne fonctionne toujours pas, supprimer le fichier
            if ! git diff --quiet "$file" 2>/dev/null || ! git diff --cached --quiet "$file" 2>/dev/null; then
                info "Suppression temporaire de $file (sera restauré après le pull)..."
                rm -f "$file"
            fi
        else
            # Fichier non suivi : simplement le supprimer temporairement
            info "Suppression temporaire de $file (sera restauré après le pull)..."
            rm -f "$file"
        fi
    fi
done

# PROTECTION CRITIQUE: S'assurer que Git ne touche JAMAIS aux fichiers DB
# Supprimer les fichiers DB de l'index Git s'ils y sont (ne devrait jamais arriver)
DB_FILES="backend/data.db backend/data.duckdb backend/data_staging.duckdb backend/data_staging.duckdb.wal backend/data.duckdb.backup backend/data_staging.duckdb.backup"
for db_file in $DB_FILES; do
    if git ls-files --error-unmatch "$db_file" >/dev/null 2>&1; then
        warning "⚠️  Fichier DB détecté dans Git: $db_file (suppression de l'index)"
        git rm --cached "$db_file" 2>/dev/null || true
    fi
done

# Faire le pull depuis master
if git pull origin master; then
    success "Code mis à jour"
    
    # Vérifier l'intégrité des bases de données APRÈS le pull
    cd "$APP_DIR/backend" || {
        error "Impossible de se déplacer dans le répertoire backend"
        exit 1
    }
    
    if [ -f "scripts/check_db_integrity.py" ]; then
        info "Vérification de l'intégrité des bases de données après mise à jour..."
        DB_INTEGRITY_OK=true
        
        # Vérifier production
        if ! python scripts/check_db_integrity.py production > /dev/null 2>&1; then
            warning "⚠️  Problème d'intégrité détecté sur la base production après pull"
            DB_INTEGRITY_OK=false
            
            # Compter les posts avant réparation
            POST_COUNT_BEFORE=0
            if [ -f "data.duckdb" ]; then
                POST_COUNT_BEFORE=$(python -c "import duckdb; conn = duckdb.connect('data.duckdb'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM posts'); print(c.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
            fi
            
            # Tenter de réparer
            info "Tentative de réparation de la base production..."
            python scripts/repair_db.py production > /dev/null 2>&1 || true
            
            # Vérifier si les données sont toujours là après réparation
            POST_COUNT_AFTER=0
            if [ -f "data.duckdb" ]; then
                POST_COUNT_AFTER=$(python -c "import duckdb; conn = duckdb.connect('data.duckdb'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM posts'); print(c.fetchone()[0]); conn.close()" 2>/dev/null || echo "0")
            fi
            
            # Si les données ont été perdues, restaurer depuis le backup
            if [ "$POST_COUNT_BEFORE" -gt 0 ] && [ "$POST_COUNT_AFTER" -eq 0 ]; then
                warning "⚠️  Données perdues lors de la réparation, tentative de restauration depuis backup..."
                LATEST_BACKUP=$(ls -t backend/backups/production_*.duckdb 2>/dev/null | head -1)
                if [ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ]; then
                    cp "$LATEST_BACKUP" "data.duckdb"
                    success "Données restaurées depuis: $LATEST_BACKUP"
                else
                    error "❌ Aucun backup disponible pour restauration"
                fi
            fi
        fi
        
        # Vérifier staging
        if ! python scripts/check_db_integrity.py staging > /dev/null 2>&1; then
            warning "⚠️  Problème d'intégrité détecté sur la base staging après pull"
            DB_INTEGRITY_OK=false
            python scripts/repair_db.py staging > /dev/null 2>&1 || true
        fi
        
        if [ "$DB_INTEGRITY_OK" = true ]; then
            success "Intégrité des bases de données vérifiée après mise à jour"
        fi
    fi
    
    cd "$APP_DIR" || {
        error "Impossible de revenir au répertoire racine"
        exit 1
    }
    
    # Essayer de restaurer les modifications si elles existent
    if [ "$HAS_CHANGES" = true ]; then
        info "Tentative de restauration des modifications locales..."
        if git stash pop > /dev/null 2>&1; then
            success "Modifications locales restaurées"
        else
            warning "Conflits lors de la restauration des modifications"
            echo "   Utilisez 'git stash list' pour voir les modifications sauvegardées"
            echo "   Utilisez 'git stash show' pour voir les changements"
            echo "   Utilisez 'git stash pop' manuellement pour restaurer"
        fi
    fi
else
    error "Échec de la mise à jour git"
    echo "   Vérifiez votre connexion Internet et les permissions git"
    echo ""
    
    # Restaurer le stash si on avait fait un stash
    if [ "$HAS_CHANGES" = true ]; then
        info "Restauration des modifications locales..."
        git stash pop > /dev/null 2>&1 || true
    fi
    
    warning "Restauration de la configuration..."
    if [ -f "$BACKUP_DIR/.env.backup" ]; then
        cp "$BACKUP_DIR/.env.backup" backend/.env
    fi
    if [ -f "$BACKUP_DIR/.app_config.backup" ]; then
        cp "$BACKUP_DIR/.app_config.backup" backend/.app_config
    fi
    if [ -f "$BACKUP_DIR/.host_alias.backup" ]; then
        cp "$BACKUP_DIR/.host_alias.backup" .host_alias
    fi
    if [ -f "$BACKUP_DIR/backup.sh.backup" ]; then
        cp "$BACKUP_DIR/backup.sh.backup" backup.sh
    fi
    if [ -f "$BACKUP_DIR/configure_cors.sh.backup" ]; then
        cp "$BACKUP_DIR/configure_cors.sh.backup" configure_cors.sh
    fi
    # Restaurer aussi les versions locales si elles existent
    for file in backend/data.db backend/data.duckdb backend/data_staging.duckdb backend/.app_config backup.sh configure_cors.sh update.sh scripts/install/update.sh; do
        if [ "$file" = "scripts/install/update.sh" ]; then
            # Pour scripts/install/update.sh, utiliser le backup spécifique
            local_backup="$BACKUP_DIR/update.sh.install.local"
        else
            local_backup="$BACKUP_DIR/$(basename $file).local"
        fi
        if [ -f "$local_backup" ]; then
            cp "$local_backup" "$file" 2>/dev/null || true
        fi
    done
    exit 1
fi

# Résoudre les conflits avec les fichiers de config après le pull si nécessaire
for file in $CONFIG_FILES; do
    if git status --porcelain 2>/dev/null | grep -q "^UU.*$file\|^AA.*$file"; then
        warning "Conflit de merge détecté avec $file, résolution automatique..."
        info "Conservation de la version locale de $file..."
        git checkout --ours "$file" 2>/dev/null || true
        git add "$file" 2>/dev/null || true
    fi
done
echo ""

# 4. Restaurer la configuration
info "Restauration de la configuration..."
if [ -f "$BACKUP_DIR/.env.backup" ]; then
    cp "$BACKUP_DIR/.env.backup" backend/.env
    success "Configuration .env restaurée"
fi

if [ -f "$BACKUP_DIR/.app_config.backup" ]; then
    cp "$BACKUP_DIR/.app_config.backup" backend/.app_config
    success "Configuration .app_config restaurée"
fi

if [ -f "$BACKUP_DIR/.host_alias.backup" ]; then
    cp "$BACKUP_DIR/.host_alias.backup" .host_alias
    success "Configuration alias restaurée"
fi

if [ -f "$BACKUP_DIR/backup.sh.backup" ]; then
    cp "$BACKUP_DIR/backup.sh.backup" backup.sh
    success "Script backup.sh restauré"
fi

if [ -f "$BACKUP_DIR/configure_cors.sh.backup" ]; then
    cp "$BACKUP_DIR/configure_cors.sh.backup" configure_cors.sh
    success "Script configure_cors.sh restauré"
fi

# Restaurer les versions locales des fichiers de config (priorité sur les backups)
CONFIG_FILES="backend/data.db backend/data.duckdb backend/data_staging.duckdb backend/.app_config backup.sh configure_cors.sh update.sh scripts/install/update.sh"
for file in $CONFIG_FILES; do
    if [ "$file" = "scripts/install/update.sh" ]; then
        # Pour scripts/install/update.sh, utiliser le backup spécifique
        local_backup="$BACKUP_DIR/update.sh.install.local"
    else
        local_backup="$BACKUP_DIR/$(basename $file).local"
    fi
    if [ -f "$local_backup" ]; then
        cp "$local_backup" "$file"
        success "Version locale de $file restaurée"
    fi
done

# Nettoyer la sauvegarde
rm -rf "$BACKUP_DIR"
echo ""

# 4b. Rendre tous les scripts exécutables (au cas où les permissions sont perdues)
info "Configuration des permissions des scripts..."
chmod +x start.sh stop.sh status.sh backup.sh configure_cors.sh update.sh install.sh 2>/dev/null || true
chmod +x scripts/install/check_access.sh 2>/dev/null || true
chmod +x scripts/app/*.sh 2>/dev/null || true
find . -maxdepth 1 -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true
success "Permissions des scripts configurées"
echo ""

# 5. Vérifier si requirements.txt a changé
info "Vérification des dépendances..."
if [ -f "backend/requirements.txt" ]; then
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        info "Mise à jour des dépendances Python..."
        cd backend
        pip install --upgrade pip > /dev/null 2>&1
        pip install -r requirements.txt --upgrade
        cd ..
        success "Dépendances mises à jour"
        
        # Vérifier que DuckDB est bien installé
        info "Vérification de l'installation de DuckDB..."
        if python -c "import duckdb" 2>/dev/null; then
            DUCKDB_VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null || echo "inconnue")
            success "DuckDB installé (version $DUCKDB_VERSION)"
        else
            warning "DuckDB n'est pas installé, tentative d'installation..."
            pip install duckdb==0.10.0
            if python -c "import duckdb" 2>/dev/null; then
                success "DuckDB installé avec succès"
            else
                error "Échec de l'installation de DuckDB"
                echo "   L'application fonctionnera en mode SQLite (fallback)"
            fi
        fi
    else
        warning "Environnement virtuel introuvable"
        echo "   Exécutez install.sh pour créer l'environnement"
    fi
else
    warning "Fichier requirements.txt introuvable"
fi
echo ""

# 6. Redémarrer l'application
info "Redémarrage de l'application..."

# S'assurer qu'on est dans le bon répertoire (déjà fait au début, mais on le refait pour être sûr)
cd "$APP_DIR" || {
    error "Impossible de se déplacer dans le répertoire: $APP_DIR"
    exit 1
}

# Afficher le répertoire actuel pour debug
CURRENT_DIR=$(pwd)
echo "🔍 DEBUG: Répertoire de travail: $CURRENT_DIR"
echo "🔍 DEBUG: Répertoire de l'application: $APP_DIR"
echo "🔍 DEBUG: OSTYPE: $OSTYPE"
echo "🔍 DEBUG: powershell.exe disponible: $(command -v powershell.exe > /dev/null 2>&1 && echo 'OUI' || echo 'NON')"

# Détecter le système d'exploitation
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]] || command -v powershell.exe > /dev/null 2>&1; then
    echo "🔍 DEBUG: Détection: WINDOWS"
    # Windows - utiliser PowerShell ou batch
    if [ -f "$APP_DIR/scripts/start/start_server.ps1" ]; then
        info "Démarrage avec PowerShell..."
        powershell.exe -ExecutionPolicy Bypass -File "$APP_DIR/scripts/start/start_server.ps1"
    elif [ -f "$APP_DIR/scripts/start/start.bat" ]; then
        info "Démarrage avec batch..."
        cmd.exe /c "$APP_DIR/scripts/start/start.bat"
    elif [ -f "$APP_DIR/scripts/start/start.sh" ]; then
        bash "$APP_DIR/scripts/start/start.sh"
    else
        warning "Script de démarrage introuvable pour Windows"
        echo "   Recherché dans: $APP_DIR/scripts/start/start_server.ps1"
        echo "   Recherché dans: $APP_DIR/scripts/start/start.bat"
        echo "   Recherché dans: $APP_DIR/scripts/start/start.sh"
        echo "   Démarrez manuellement avec: powershell.exe scripts/start/start_server.ps1"
    fi
else
    # Linux/Mac - utiliser bash
    echo "🔍 DEBUG: Détection: LINUX/MAC"
    # S'assurer qu'on est dans le bon répertoire
    cd "$APP_DIR" || {
        error "Impossible de se déplacer dans: $APP_DIR"
        exit 1
    }
    
    # Afficher les informations de diagnostic (toujours afficher)
    CURRENT_PWD=$(pwd)
    echo "🔍 Diagnostic: Recherche du script start.sh..."
    echo "   Répertoire actuel: $CURRENT_PWD"
    echo "   APP_DIR: $APP_DIR"
    
    # Résoudre le chemin absolu de APP_DIR si possible
    if command -v realpath > /dev/null 2>&1; then
        APP_DIR_ABS=$(realpath "$APP_DIR" 2>/dev/null || echo "$APP_DIR")
    elif command -v readlink > /dev/null 2>&1; then
        APP_DIR_ABS=$(readlink -f "$APP_DIR" 2>/dev/null || echo "$APP_DIR")
    else
        APP_DIR_ABS="$APP_DIR"
    fi
    
    echo "   APP_DIR_ABS: $APP_DIR_ABS"
    
    # Liste des chemins à tester (ordre de priorité)
    CURRENT_DIR=$(pwd)
    
    POSSIBLE_PATHS=(
        "$APP_DIR_ABS/scripts/start/start.sh"
        "$APP_DIR/scripts/start/start.sh"
        "$CURRENT_DIR/scripts/start/start.sh"
        "scripts/start/start.sh"
        "./scripts/start/start.sh"
        "$(pwd)/scripts/start/start.sh"
    )
    
    # Tester chaque chemin et afficher le résultat
    START_SCRIPT=""
    echo "   Vérification des chemins possibles:"
    for path in "${POSSIBLE_PATHS[@]}"; do
        if [ -f "$path" ]; then
            echo "   ✅ Trouvé: $path"
            START_SCRIPT="$path"
            break
        else
            echo "   ❌ Non trouvé: $path"
        fi
    done
    
    # Si toujours pas trouvé, essayer avec find depuis APP_DIR
    if [ -z "$START_SCRIPT" ] || [ ! -f "$START_SCRIPT" ]; then
        echo "   Recherche avec find depuis $APP_DIR..."
        FOUND_SCRIPT=$(find "$APP_DIR" -maxdepth 4 -name "start.sh" -path "*/scripts/start/start.sh" -type f 2>/dev/null | head -1)
        if [ -n "$FOUND_SCRIPT" ] && [ -f "$FOUND_SCRIPT" ]; then
            echo "   ✅ Trouvé avec find: $FOUND_SCRIPT"
            START_SCRIPT="$FOUND_SCRIPT"
        else
            echo "   ❌ Aucun résultat avec find"
            # Vérifier si le répertoire scripts/start existe
            if [ -d "scripts/start" ]; then
                echo "   📁 Le répertoire scripts/start existe, contenu:"
                ls -la scripts/start/ 2>/dev/null | sed 's/^/      /' || echo "      (erreur lors de la liste)"
            elif [ -d "$APP_DIR/scripts/start" ]; then
                echo "   📁 Le répertoire $APP_DIR/scripts/start existe, contenu:"
                ls -la "$APP_DIR/scripts/start/" 2>/dev/null | sed 's/^/      /' || echo "      (erreur lors de la liste)"
            else
                echo "   ❌ Le répertoire scripts/start n'existe pas"
            fi
        fi
    fi
    
    if [ -n "$START_SCRIPT" ] && [ -f "$START_SCRIPT" ]; then
        success "Script trouvé: $START_SCRIPT"
        # Vérifier que le script est exécutable
        if [ ! -x "$START_SCRIPT" ]; then
            info "Ajout des permissions d'exécution au script..."
            chmod +x "$START_SCRIPT"
        fi
        info "Démarrage de l'application..."
        bash "$START_SCRIPT"
    else
        warning "Script start.sh introuvable"
        echo ""
        echo "   Diagnostic détaillé:"
        echo "   Répertoire actuel: $(pwd)"
        echo "   APP_DIR: $APP_DIR"
        echo "   APP_DIR_ABS: $APP_DIR_ABS"
        echo ""
        echo "   Vérifications effectuées:"
        for path in "${POSSIBLE_PATHS[@]}"; do
            if [ -f "$path" ]; then
                echo "     ✅ $path (EXISTE)"
            else
                echo "     ❌ $path (N'EXISTE PAS)"
            fi
        done
        echo ""
        echo "   Structure des répertoires:"
        if [ -d "scripts" ]; then
            echo "     ✅ scripts/ existe"
            if [ -d "scripts/start" ]; then
                echo "     ✅ scripts/start/ existe"
                echo "     Contenu de scripts/start/:"
                ls -la scripts/start/ 2>/dev/null | sed 's/^/       /' || echo "       (erreur lors de la liste)"
            else
                echo "     ❌ scripts/start/ n'existe pas"
                echo "     Contenu de scripts/:"
                ls -la scripts/ 2>/dev/null | sed 's/^/       /' || echo "       (erreur lors de la liste)"
            fi
        else
            echo "     ❌ scripts/ n'existe pas"
            echo "     Répertoires à la racine:"
            ls -la . 2>/dev/null | grep "^d" | sed 's/^/       /' || echo "       (erreur lors de la liste)"
        fi
        echo ""
        echo "   Recherche de fichiers start.sh dans le projet:"
        find . -name "start.sh" -type f 2>/dev/null | head -10 | sed 's/^/     /' || echo "     (aucun fichier start.sh trouvé)"
        echo ""
        echo "   💡 Démarrez manuellement l'application avec:"
        echo "      cd $APP_DIR && bash scripts/start/start.sh"
        echo "   ou"
        echo "      bash $APP_DIR/scripts/start/start.sh"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Mise à jour terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Vérifiez le statut avec : bash scripts/install/status.sh ou ./status.sh"
echo ""

