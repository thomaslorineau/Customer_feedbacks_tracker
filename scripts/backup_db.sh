#!/bin/bash
# Script de sauvegarde automatique des bases de données
# Usage: ./scripts/backup_db.sh [production|staging|both]
# Pour cron: ajoutez cette ligne dans crontab (sauvegarde quotidienne à 2h du matin)
# 0 2 * * * /path/to/scripts/backup_db.sh both >> /path/to/backups/backup.log 2>&1

# Obtenir le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

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

# Aller dans le répertoire backend
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

# Déterminer l'environnement à sauvegarder
ENV_ARG="${1:-both}"

# Exécuter le script Python de sauvegarde
info "Démarrage de la sauvegarde automatique..."
python scripts/backup_db.py "$ENV_ARG" --keep=30

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    success "Sauvegarde terminée avec succès"
else
    error "Erreur lors de la sauvegarde (code: $EXIT_CODE)"
fi

exit $EXIT_CODE

