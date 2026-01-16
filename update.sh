#!/bin/bash
# Script wrapper pour update.sh
# Ce script appelle le vrai script dans scripts/install/update.sh

# Obtenir le répertoire du script actuel
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Appeler le vrai script avec le chemin absolu
if [ -f "$SCRIPT_DIR/scripts/install/update.sh" ]; then
    exec bash "$SCRIPT_DIR/scripts/install/update.sh" "$@"
else
    echo "Erreur: Script scripts/install/update.sh introuvable dans $SCRIPT_DIR" >&2
    exit 1
fi

