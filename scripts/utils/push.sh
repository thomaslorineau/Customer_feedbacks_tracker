#!/bin/bash
# Script interactif pour choisir où push (Stash, GitHub, ou les deux)
# Usage: bash scripts/utils/push.sh [branch]

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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
echo "📤 Push Git - Choix du remote"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier que c'est un dépôt git
if [ ! -d ".git" ]; then
    error "Ce répertoire n'est pas un dépôt git"
    exit 1
fi

# Afficher les remotes disponibles
info "Remotes disponibles :"
git remote -v
echo ""

# Vérifier que les remotes existent
HAS_ORIGIN=false
HAS_GITHUB=false

if git remote get-url origin > /dev/null 2>&1; then
    HAS_ORIGIN=true
    ORIGIN_URL=$(git remote get-url origin)
    info "✓ Origin (Stash) : $ORIGIN_URL"
fi

if git remote get-url github > /dev/null 2>&1; then
    HAS_GITHUB=true
    GITHUB_URL=$(git remote get-url github)
    info "✓ GitHub : $GITHUB_URL"
fi

if [ "$HAS_ORIGIN" = false ] && [ "$HAS_GITHUB" = false ]; then
    error "Aucun remote configuré"
    exit 1
fi

echo ""

# Détecter la branche actuelle ou utiliser celle passée en paramètre
if [ -n "$1" ]; then
    BRANCH="$1"
else
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
fi

info "Branche actuelle : $BRANCH"
echo ""

# Menu de choix
# Si un choix est passé en paramètre (2ème argument), l'utiliser
if [ -n "$2" ]; then
    choice="$2"
    info "Choix automatique : $choice"
else
    echo "Où voulez-vous push ?"
    if [ "$HAS_ORIGIN" = true ] && [ "$HAS_GITHUB" = true ]; then
        echo "  1) Stash uniquement (origin)"
        echo "  2) GitHub uniquement (github)"
        echo "  3) Les deux (origin + github)"
        read -p "Choix (1-3): " choice
    elif [ "$HAS_ORIGIN" = true ]; then
        echo "  1) Stash (origin)"
        read -p "Choix (1): " choice
        choice=1
    elif [ "$HAS_GITHUB" = true ]; then
        echo "  1) GitHub (github)"
        read -p "Choix (1): " choice
        choice=2
    fi
fi

echo ""

# Fonction pour push sur un remote
push_to_remote() {
    local remote=$1
    local branch=$2
    
    info "Push sur $remote ($branch)..."
    if git push "$remote" "$branch"; then
        success "Push réussi sur $remote"
        return 0
    else
        error "Échec du push sur $remote"
        return 1
    fi
}

# Exécuter le push selon le choix
PUSH_SUCCESS=true

case $choice in
    1)
        if [ "$HAS_ORIGIN" = true ]; then
            push_to_remote "origin" "$BRANCH" || PUSH_SUCCESS=false
        else
            error "Remote origin non configuré"
            exit 1
        fi
        ;;
    2)
        if [ "$HAS_GITHUB" = true ]; then
            push_to_remote "github" "$BRANCH" || PUSH_SUCCESS=false
        else
            error "Remote github non configuré"
            echo ""
            info "Pour ajouter GitHub :"
            echo "   git remote add github https://github.com/thomaslorineau/Customer_feedbacks_tracker.git"
            exit 1
        fi
        ;;
    3)
        if [ "$HAS_ORIGIN" = true ] && [ "$HAS_GITHUB" = true ]; then
            push_to_remote "origin" "$BRANCH" || PUSH_SUCCESS=false
            echo ""
            push_to_remote "github" "$BRANCH" || PUSH_SUCCESS=false
        else
            error "Les deux remotes ne sont pas configurés"
            exit 1
        fi
        ;;
    *)
        error "Choix invalide"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$PUSH_SUCCESS" = true ]; then
    success "Push terminé !"
else
    error "Certains pushs ont échoué"
    exit 1
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

