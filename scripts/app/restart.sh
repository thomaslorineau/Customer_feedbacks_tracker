#!/bin/bash
# Script de redémarrage de l'application
# Usage: bash scripts/app/restart.sh

# Obtenir le répertoire du script (scripts/app/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Remonter à la racine du projet (2 niveaux: scripts/app -> scripts -> racine)
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
echo "🔄 Redémarrage de l'application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Arrêter l'application
info "Arrêt de l'application..."
if [ -f "scripts/app/stop.sh" ]; then
    bash scripts/app/stop.sh
else
    error "Script scripts/app/stop.sh introuvable"
    exit 1
fi

# Attendre un peu pour que l'arrêt soit complet
sleep 2

# 2. Démarrer l'application
info "Démarrage de l'application..."
if [ -f "scripts/app/start.sh" ]; then
    bash scripts/app/start.sh
else
    error "Script scripts/app/start.sh introuvable"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Redémarrage terminé !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


