#!/bin/bash
# Script de mise à jour de l'application via git
# Usage: ./update.sh ou bash update.sh

# Se rendre exécutable soi-même (au cas où les permissions sont perdues)
# Note: Si le script n'est pas exécutable, utilisez: bash update.sh
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
chmod +x "$SCRIPT_PATH" 2>/dev/null || true

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

# 2. Sauvegarder la configuration
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

# Sauvegarder aussi la base de données (juste pour sécurité, on ne la restaure pas)
if [ -f "backend/data.db" ]; then
    cp backend/data.db "$BACKUP_DIR/data.db.backup"
    info "Base de données sauvegardée (sécurité)"
fi

echo ""

# 3. Mettre à jour le code
info "Mise à jour du code depuis Stash..."

# Vérifier s'il y a des modifications locales (en excluant data.db et autres fichiers de DB)
HAS_CHANGES=false

# D'abord, résoudre les conflits avec data.db s'il y en a
if git status --porcelain 2>/dev/null | grep -q "^UU.*backend/data.db\|^AA.*backend/data.db"; then
    warning "Conflit de merge détecté avec data.db, résolution automatique..."
    info "Conservation de la version locale de data.db..."
    git checkout --ours backend/data.db 2>/dev/null || true
    git add backend/data.db 2>/dev/null || true
fi

# Exclure les fichiers de base de données, configuration locale et scripts locaux
EXCLUDE_PATTERNS="-- ':!backend/data.db' ':!backend/*.db' ':!backend/*.log' ':!backend/__pycache__' ':!backend/**/__pycache__' ':!backend/.app_config' ':!backup.sh' ':!configure_cors.sh'"

# Vérifier les modifications (sans les fichiers exclus)
if ! git diff --quiet $EXCLUDE_PATTERNS 2>/dev/null || ! git diff --cached --quiet $EXCLUDE_PATTERNS 2>/dev/null; then
    HAS_CHANGES=true
    warning "Modifications locales détectées"
    info "Sauvegarde temporaire des modifications (stash)..."
    
    # Essayer de stash en excluant les fichiers problématiques
    if git stash push $EXCLUDE_PATTERNS -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" 2>/dev/null; then
        success "Modifications sauvegardées temporairement"
    else
        # Si le stash échoue, essayer de résoudre les conflits avec data.db
        warning "Conflit détecté avec data.db, résolution automatique..."
        
        # Si data.db a un conflit de merge, utiliser notre version locale
        if git status --porcelain | grep -q "backend/data.db"; then
            info "Résolution du conflit avec data.db (conservation de la version locale)..."
            git checkout --ours backend/data.db 2>/dev/null || true
            git add backend/data.db 2>/dev/null || true
        fi
        
        # Réessayer le stash
        if git stash push $EXCLUDE_PATTERNS -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" 2>/dev/null; then
            success "Modifications sauvegardées temporairement (après résolution)"
        else
            error "Impossible de sauvegarder les modifications locales"
            echo "   Résolvez les conflits manuellement ou commitez vos changements"
            echo "   Utilisez 'git status' pour voir les fichiers modifiés"
            echo ""
            echo "   Pour résoudre manuellement :"
            echo "   1. git checkout --ours backend/data.db  # Garder votre version locale"
            echo "   2. git add backend/data.db"
            echo "   3. Relancez ./update.sh"
            exit 1
        fi
    fi
    echo ""
fi

# Forcer la résolution des fichiers de config AVANT le pull
# On sauvegarde, puis on supprime temporairement ces fichiers pour permettre le pull
# Note: install.sh et scripts/install/install.sh sont aussi gérés car ce sont des scripts versionnés
CONFIG_FILES="backend/data.db backend/.app_config backup.sh configure_cors.sh update.sh install.sh scripts/install/install.sh"
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

# Détecter le remote à utiliser
REMOTE_TO_USE="origin"
if git remote get-url origin > /dev/null 2>&1; then
    ORIGIN_URL=$(git remote get-url origin)
    info "Remote origin détecté: $ORIGIN_URL"
    REMOTE_TO_USE="origin"
else
    # Essayer GitHub si origin n'existe pas
    if git remote get-url github > /dev/null 2>&1; then
        warning "Remote origin non trouvé, utilisation de github"
        REMOTE_TO_USE="github"
    else
        error "Aucun remote configuré (origin ou github)"
        exit 1
    fi
fi

# Faire le pull depuis master
info "Mise à jour depuis $REMOTE_TO_USE/master..."
if git pull $REMOTE_TO_USE master; then
    success "Code mis à jour"
    
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
    for file in backend/data.db backend/.app_config backup.sh configure_cors.sh update.sh; do
        local_backup="$BACKUP_DIR/$(basename $file).local"
        if [ -f "$local_backup" ]; then
            cp "$local_backup" "$file" 2>/dev/null || true
        fi
    done
    exit 1
fi

# Résoudre les conflits avec les fichiers de config après le pull si nécessaire
# Pour install.sh et scripts/install/install.sh, on prend la version distante (ce sont des scripts versionnés)
SCRIPT_FILES="install.sh scripts/install/install.sh"
for file in $SCRIPT_FILES; do
    if git status --porcelain 2>/dev/null | grep -q "^UU.*$file\|^AA.*$file"; then
        warning "Conflit de merge détecté avec $file, résolution automatique..."
        info "Conservation de la version distante de $file (script versionné)..."
        git checkout --theirs "$file" 2>/dev/null || true
        git add "$file" 2>/dev/null || true
    fi
done

# Pour les autres fichiers de config, on conserve la version locale
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
# Note: install.sh et scripts/install/install.sh ne sont PAS restaurés car ce sont des scripts versionnés
CONFIG_FILES="backend/data.db backend/.app_config backup.sh configure_cors.sh update.sh"
for file in $CONFIG_FILES; do
    local_backup="$BACKUP_DIR/$(basename $file).local"
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
# Scripts à la racine
chmod +x install.sh update.sh quick-update.sh 2>/dev/null || true
# Scripts dans scripts/app/
chmod +x scripts/app/*.sh 2>/dev/null || true
# Scripts dans scripts/install/
chmod +x scripts/install/*.sh 2>/dev/null || true
# Scripts dans scripts/utils/
chmod +x scripts/utils/*.sh 2>/dev/null || true
# Support anciennes installations avec scripts à la racine
chmod +x start.sh stop.sh status.sh backup.sh configure_cors.sh 2>/dev/null || true
# Tous les autres scripts .sh à la racine
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
    if [ -f "$APP_DIR/scripts/app/start.sh" ]; then
        info "Démarrage de l'application..."
        bash "$APP_DIR/scripts/app/start.sh"
    else
        warning "Script de démarrage introuvable"
        echo "   Recherché dans: $APP_DIR/scripts/app/start.sh"
        echo "   Démarrez manuellement avec: bash scripts/app/start.sh"
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
        "$APP_DIR_ABS/scripts/app/start.sh"
        "$APP_DIR/scripts/app/start.sh"
        "$CURRENT_DIR/scripts/app/start.sh"
        "scripts/app/start.sh"
        "./scripts/app/start.sh"
        "$(pwd)/scripts/app/start.sh"
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
        FOUND_SCRIPT=$(find "$APP_DIR" -maxdepth 4 -name "start.sh" -path "*/scripts/app/start.sh" -type f 2>/dev/null | head -1)
        if [ -n "$FOUND_SCRIPT" ] && [ -f "$FOUND_SCRIPT" ]; then
            echo "   ✅ Trouvé avec find: $FOUND_SCRIPT"
            START_SCRIPT="$FOUND_SCRIPT"
        else
            echo "   ❌ Aucun résultat avec find"
            # Vérifier si le répertoire scripts/app existe
            if [ -d "scripts/app" ]; then
                echo "   📁 Le répertoire scripts/app existe, contenu:"
                ls -la scripts/app/ 2>/dev/null | sed 's/^/      /' || echo "      (erreur lors de la liste)"
            elif [ -d "$APP_DIR/scripts/app" ]; then
                echo "   📁 Le répertoire $APP_DIR/scripts/app existe, contenu:"
                ls -la "$APP_DIR/scripts/app/" 2>/dev/null | sed 's/^/      /' || echo "      (erreur lors de la liste)"
            else
                echo "   ❌ Le répertoire scripts/app n'existe pas"
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
        if [ -d "scripts/app" ]; then
            echo "     ✅ scripts/app/ existe"
            echo "     Contenu de scripts/app/:"
            ls -la scripts/app/ 2>/dev/null | sed 's/^/       /' || echo "       (erreur lors de la liste)"
        else
            echo "     ❌ scripts/app/ n'existe pas"
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
        echo "      cd $APP_DIR && bash scripts/app/start.sh"
        echo "   ou"
        echo "      bash $APP_DIR/scripts/app/start.sh"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Mise à jour terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Vérifiez le statut avec : bash scripts/install/status.sh ou ./status.sh"
echo ""

