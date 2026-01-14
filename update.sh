#!/bin/bash
# Script de mise à jour de l'application via git
# Usage: ./update.sh

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
        if [ -f "stop.sh" ]; then
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

# Sauvegarder aussi la base de données (juste pour sécurité, on ne la restaure pas)
if [ -f "backend/data.db" ]; then
    cp backend/data.db "$BACKUP_DIR/data.db.backup"
    info "Base de données sauvegardée (sécurité)"
fi

echo ""

# 3. Mettre à jour le code
info "Mise à jour du code depuis GitHub..."

# Vérifier s'il y a des modifications locales
HAS_CHANGES=false
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    HAS_CHANGES=true
    warning "Modifications locales détectées"
    info "Sauvegarde temporaire des modifications (stash)..."
    if git stash push -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" 2>/dev/null; then
        success "Modifications sauvegardées temporairement"
    else
        error "Impossible de sauvegarder les modifications locales"
        echo "   Résolvez les conflits manuellement ou commitez vos changements"
        echo "   Utilisez 'git status' pour voir les fichiers modifiés"
        exit 1
    fi
    echo ""
fi

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
    exit 1
fi
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

# Nettoyer la sauvegarde
rm -rf "$BACKUP_DIR"
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
if [ -f "start.sh" ]; then
    ./start.sh
else
    warning "Script start.sh introuvable"
    echo "   Démarrez manuellement l'application"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Mise à jour terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Vérifiez le statut avec : ./status.sh"
echo ""

