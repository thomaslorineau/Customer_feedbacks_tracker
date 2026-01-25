#!/usr/bin/env python3
"""
Script pour nettoyer les doublons dans la base de données.
Peut être exécuté manuellement ou programmé.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import database as db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Nettoyer les doublons dans la base de données."""
    logger.info("🔍 Recherche des doublons dans la base de données...")
    
    try:
        deleted_count = db.delete_duplicate_posts()
        
        if deleted_count > 0:
            logger.info(f"✅ {deleted_count} doublons supprimés avec succès")
        else:
            logger.info("✅ Aucun doublon trouvé dans la base de données")
        
        return deleted_count
    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage des doublons: {e}")
        raise


if __name__ == "__main__":
    main()

