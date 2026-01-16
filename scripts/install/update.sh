#!/bin/bash
# Script de mise à jour de l'application via git
# Usage: ./update.sh

# Obtenir le répertoire du script (scripts/install/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Remonter à la racine du projet (2 niveaux: scripts/install -> scripts -> racine)
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_DIR"

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
        if [ -f "scripts/start/stop.sh" ]; then
            bash scripts/start/stop.sh > /dev/null 2>&1
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
info "Mise à jour du code depuis GitHub..."

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
CONFIG_FILES="backend/data.db backend/.app_config backup.sh configure_cors.sh update.sh"
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

# Faire le pull
if git pull origin master; then
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
chmod +x start.sh stop.sh status.sh backup.sh configure_cors.sh update.sh install.sh 2>/dev/null || true
chmod +x scripts/install/check_access.sh 2>/dev/null || true
chmod +x scripts/start/*.sh 2>/dev/null || true
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

# Détecter le système d'exploitation
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]] || command -v powershell.exe > /dev/null 2>&1; then
    # Windows - utiliser PowerShell ou batch
    if [ -f "scripts/start/start_server.ps1" ]; then
        info "Démarrage avec PowerShell..."
        powershell.exe -ExecutionPolicy Bypass -File scripts/start/start_server.ps1
    elif [ -f "scripts/start/start.bat" ]; then
        info "Démarrage avec batch..."
        cmd.exe /c scripts/start/start.bat
    elif [ -f "scripts/start/start.sh" ]; then
        bash scripts/start/start.sh
    else
        warning "Script de démarrage introuvable pour Windows"
        echo "   Démarrez manuellement avec: powershell.exe scripts/start/start_server.ps1"
    fi
else
    # Linux/Mac - utiliser bash
    if [ -f "$APP_DIR/scripts/start/start.sh" ]; then
        info "Démarrage avec scripts/start/start.sh..."
        bash "$APP_DIR/scripts/start/start.sh"
    elif [ -f "$APP_DIR/start.sh" ]; then
        info "Démarrage avec start.sh..."
        bash "$APP_DIR/start.sh"
    elif [ -f "scripts/start/start.sh" ]; then
        info "Démarrage avec scripts/start/start.sh (chemin relatif)..."
        bash scripts/start/start.sh
    elif [ -f "start.sh" ]; then
        info "Démarrage avec start.sh (chemin relatif)..."
        ./start.sh
    else
        warning "Script start.sh introuvable"
        echo "   Recherché dans: $APP_DIR/scripts/start/start.sh"
        echo "   Recherché dans: $APP_DIR/start.sh"
        echo "   Recherché dans: scripts/start/start.sh"
        echo "   Recherché dans: start.sh"
        echo "   Démarrez manuellement l'application avec: bash scripts/start/start.sh"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Mise à jour terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Vérifiez le statut avec : bash scripts/install/status.sh ou ./status.sh"
echo ""

