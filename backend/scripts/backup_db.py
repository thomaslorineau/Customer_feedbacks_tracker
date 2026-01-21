#!/usr/bin/env python3
"""
Script de sauvegarde automatique des bases de données DuckDB.
Gère la rotation des sauvegardes (garde seulement les N dernières).
Usage:
    python scripts/backup_db.py [production|staging|both] [--keep=N]
"""
import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import duckdb

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration par défaut
DEFAULT_KEEP_BACKUPS = 30  # Garder 30 sauvegardes par défaut
BACKUP_DIR = Path(__file__).resolve().parents[1] / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


def check_db_integrity(db_path: Path) -> Tuple[bool, str]:
    """
    Vérifie l'intégrité d'une base de données DuckDB.
    Retourne (is_valid, error_message)
    """
    if not db_path.exists():
        return False, f"Le fichier n'existe pas: {db_path}"
    
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        cursor = conn.cursor()
        
        # Vérifier que les tables principales existent
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['posts', 'saved_queries', 'scraping_logs', 'base_keywords', 'jobs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            conn.close()
            return False, f"Tables manquantes: {', '.join(missing_tables)}"
        
        # Essayer une requête simple pour vérifier l'intégrité
        cursor.execute("SELECT COUNT(*) FROM posts")
        cursor.fetchone()
        
        conn.close()
        return True, "OK"
        
    except Exception as e:
        return False, str(e)


def backup_database(db_path: Path, environment: str, keep_backups: int = DEFAULT_KEEP_BACKUPS, backup_type: str = "hourly") -> bool:
    """
    Sauvegarde une base de données DuckDB.
    
    Args:
        db_path: Chemin vers le fichier de base de données
        environment: Nom de l'environnement (production/staging)
        keep_backups: Nombre de sauvegardes à conserver
        
    Returns:
        True si la sauvegarde a réussi, False sinon
    """
    if not db_path.exists():
        logger.warning(f"⚠️  Base de données introuvable: {db_path}")
        return False
    
    # Vérifier l'intégrité avant la sauvegarde
    is_valid, error_msg = check_db_integrity(db_path)
    if not is_valid:
        logger.error(f"❌ Base de données corrompue, sauvegarde annulée: {error_msg}")
        return False
    
    # Créer le nom de sauvegarde avec timestamp et type
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{environment}_data_{backup_type}_{timestamp}.duckdb"
    backup_path = BACKUP_DIR / backup_filename
    
    try:
        # Créer la sauvegarde
        logger.info(f"📦 Création de la sauvegarde: {backup_path}")
        shutil.copy2(db_path, backup_path)
        
        # Vérifier que la sauvegarde est valide
        is_backup_valid, backup_error = check_db_integrity(backup_path)
        if not is_backup_valid:
            logger.error(f"❌ La sauvegarde est corrompue: {backup_error}")
            backup_path.unlink()
            return False
        
        # Obtenir la taille du fichier
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Sauvegarde créée: {backup_filename} ({size_mb:.2f} MB)")
        
        # Nettoyer les anciennes sauvegardes du même type
        cleanup_old_backups(environment, keep_backups, backup_type)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
        return False


def cleanup_old_backups(environment: str, keep_backups: int, backup_type: str = None):
    """
    Supprime les anciennes sauvegardes, en gardant seulement les N plus récentes.
    Si backup_type est spécifié, ne nettoie que ce type de backup.
    """
    try:
        # Lister toutes les sauvegardes pour cet environnement et type
        if backup_type:
            pattern = f"{environment}_data_{backup_type}_*.duckdb"
        else:
            pattern = f"{environment}_data_*.duckdb"
        backups = sorted(BACKUP_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(backups) > keep_backups:
            # Supprimer les plus anciennes
            to_delete = backups[keep_backups:]
            for backup in to_delete:
                logger.info(f"🗑️  Suppression de l'ancienne sauvegarde: {backup.name}")
                backup.unlink()
            
            logger.info(f"✅ {len(to_delete)} ancienne(s) sauvegarde(s) supprimée(s)")
        
    except Exception as e:
        logger.warning(f"⚠️  Erreur lors du nettoyage des sauvegardes: {e}")


def list_backups(environment: str = None):
    """
    Liste toutes les sauvegardes disponibles.
    """
    if environment:
        pattern = f"{environment}_data_*.duckdb"
    else:
        pattern = "*_data_*.duckdb"
    
    backups = sorted(BACKUP_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        logger.info("Aucune sauvegarde trouvée")
        return
    
    logger.info(f"\n📋 Sauvegardes disponibles ({len(backups)}):")
    for backup in backups:
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        logger.info(f"  - {backup.name} ({size_mb:.2f} MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")


def main():
    """Point d'entrée principal."""
    # Déterminer l'environnement
    if len(sys.argv) > 1:
        env_arg = sys.argv[1].lower()
        if env_arg in ['production', 'staging', 'both']:
            environments = ['production', 'staging'] if env_arg == 'both' else [env_arg]
        else:
            logger.error(f"❌ Environnement invalide: {env_arg}")
            logger.info("Usage: python scripts/backup_db.py [production|staging|both] [--keep=N]")
            sys.exit(1)
    else:
        # Par défaut, sauvegarder selon la variable d'environnement
        env = os.getenv("ENVIRONMENT", "production")
        environments = [env]
    
    # Déterminer le nombre de sauvegardes à garder
    keep_backups = DEFAULT_KEEP_BACKUPS
    for arg in sys.argv[2:]:
        if arg.startswith('--keep='):
            try:
                keep_backups = int(arg.split('=')[1])
            except ValueError:
                logger.warning(f"⚠️  Valeur invalide pour --keep: {arg.split('=')[1]}")
    
    # Déterminer les chemins des bases de données
    backend_dir = Path(__file__).resolve().parents[1]
    db_paths = {}
    
    if 'production' in environments:
        db_paths['production'] = backend_dir / "data.duckdb"
    if 'staging' in environments:
        db_paths['staging'] = backend_dir / "data_staging.duckdb"
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("💾 Sauvegarde des bases de données")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"📁 Répertoire de sauvegarde: {BACKUP_DIR}")
    logger.info(f"💾 Conservation: {keep_backups} sauvegardes par environnement\n")
    
    success_count = 0
    total_count = len(db_paths)
    
    for env, db_path in db_paths.items():
        logger.info(f"\n🔄 Sauvegarde de l'environnement: {env}")
        logger.info(f"   Base de données: {db_path}")
        
        if backup_database(db_path, env, keep_backups):
            success_count += 1
        else:
            logger.warning(f"⚠️  Échec de la sauvegarde pour {env}")
    
    logger.info("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if success_count == total_count:
        logger.info(f"✅ Sauvegarde terminée: {success_count}/{total_count} réussie(s)")
    else:
        logger.warning(f"⚠️  Sauvegarde partielle: {success_count}/{total_count} réussie(s)")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Lister les sauvegardes
    if len(environments) == 1:
        list_backups(environments[0])
    else:
        list_backups()
    
    sys.exit(0 if success_count == total_count else 1)


if __name__ == "__main__":
    main()

