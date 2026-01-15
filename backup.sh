#!/bin/bash
# Script de sauvegarde de la base de données

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/backups/ovh-tracker"
DB_FILE="$APP_DIR/backend/data.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Créer le répertoire de sauvegarde
mkdir -p "$BACKUP_DIR"

# Vérifier que la base de données existe
if [ ! -f "$DB_FILE" ]; then
    echo "⚠️  Base de données introuvable: $DB_FILE"
    exit 1
fi

# Effectuer la sauvegarde
BACKUP_FILE="$BACKUP_DIR/data_$DATE.db"
cp "$DB_FILE" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Obtenir la taille du fichier
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Sauvegarde effectuée avec succès"
    echo "   Fichier: $BACKUP_FILE"
    echo "   Taille: $SIZE"
    
    # Garder seulement les 30 derniers backups
    echo "🧹 Nettoyage des anciennes sauvegardes (> 30 jours)..."
    find "$BACKUP_DIR" -name "data_*.db" -mtime +30 -delete 2>/dev/null
    
    # Compter les sauvegardes
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/data_*.db 2>/dev/null | wc -l)
    echo "   Total de sauvegardes: $BACKUP_COUNT"
else
    echo "❌ Échec de la sauvegarde"
    exit 1
fi


