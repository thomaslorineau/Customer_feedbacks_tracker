#!/bin/bash
# Script de migration du dépôt GitHub vers Stash
# Usage: bash scripts/install/migrate_to_stash.sh

set -e

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
echo "🔄 Migration vers Stash"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier que c'est un dépôt git
if [ ! -d ".git" ]; then
    error "Ce répertoire n'est pas un dépôt git"
    exit 1
fi

# Afficher le remote actuel
info "Remote actuel :"
git remote -v
echo ""

# Détecter la branche actuelle
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
info "Branche actuelle : $CURRENT_BRANCH"
echo ""

# Changer le remote origin vers Stash
info "Changement du remote origin vers Stash..."
git remote set-url origin ssh://git@stash.ovh.net:7999/~thomas.lorineau/customer_feedbacks_tracker.git
success "Remote origin mis à jour"
echo ""

# Vérifier la connexion
info "Vérification de la connexion à Stash..."
if git ls-remote origin > /dev/null 2>&1; then
    success "Connexion à Stash réussie"
else
    error "Impossible de se connecter à Stash"
    echo "   Vérifiez votre clé SSH et vos permissions"
    exit 1
fi
echo ""

# Mettre à jour le code depuis Stash
info "Mise à jour du code depuis Stash (branche $CURRENT_BRANCH)..."
if git pull origin "$CURRENT_BRANCH"; then
    success "Code mis à jour depuis Stash"
else
    warning "Le pull a échoué, mais la migration du remote est terminée"
    echo "   Vous pouvez réessayer avec : git pull origin $CURRENT_BRANCH"
fi
echo ""

# Afficher le nouveau remote
info "Nouveau remote :"
git remote -v
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Migration terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Vous pouvez maintenant utiliser :"
echo "   ./update.sh"
echo "   ou"
echo "   bash scripts/install/update.sh"
echo ""

