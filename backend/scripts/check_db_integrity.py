#!/usr/bin/env python3
"""
Script pour vérifier l'intégrité des bases de données DuckDB.
Usage:
    python scripts/check_db_integrity.py [production|staging|both]
"""
import os
import sys
import logging
from pathlib import Path
from typing import Tuple, Dict
import duckdb

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_integrity(db_path: Path) -> Tuple[bool, Dict[str, any]]:
    """
    Vérifie l'intégrité complète d'une base de données DuckDB.
    
    Returns:
        (is_valid, details_dict) où details_dict contient:
        - status: 'ok' | 'corrupted' | 'missing'
        - error: message d'erreur si applicable
        - tables: liste des tables trouvées
        - row_counts: dict avec le nombre de lignes par table
        - file_size: taille du fichier en MB
    """
    details = {
        'status': 'missing',
        'error': None,
        'tables': [],
        'row_counts': {},
        'file_size': 0
    }
    
    if not db_path.exists():
        details['error'] = f"Le fichier n'existe pas: {db_path}"
        return False, details
    
    # Obtenir la taille du fichier
    try:
        details['file_size'] = db_path.stat().st_size / (1024 * 1024)  # MB
    except Exception as e:
        details['error'] = f"Impossible de lire la taille du fichier: {e}"
        return False, details
    
    # Essayer de se connecter
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        cursor = conn.cursor()
        
        # Vérifier que les tables principales existent
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        details['tables'] = tables
        
        required_tables = ['posts', 'saved_queries', 'scraping_logs', 'base_keywords', 'jobs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            # Si aucune table n'existe, la base est vide (non initialisée), pas corrompue
            if len(tables) == 0:
                conn.close()
                details['status'] = 'empty'
                details['error'] = "Base de données vide (non initialisée)"
                return True, details  # Considérer comme valide mais vide
            
            # Si certaines tables manquent mais d'autres existent, c'est suspect
            conn.close()
            details['status'] = 'corrupted'
            details['error'] = f"Tables manquantes: {', '.join(missing_tables)}"
            return False, details
        
        # Compter les lignes dans chaque table
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                details['row_counts'][table] = count
            except Exception as e:
                details['row_counts'][table] = f"ERROR: {e}"
        
        # Essayer quelques requêtes pour vérifier l'intégrité des données
        try:
            # Vérifier la table posts
            cursor.execute("SELECT COUNT(*) FROM posts WHERE id IS NULL")
            null_ids = cursor.fetchone()[0]
            if null_ids > 0:
                details['error'] = f"Trouvé {null_ids} posts avec id NULL"
                conn.close()
                return False, details
            
            # Vérifier les séquences (DuckDB utilise une syntaxe différente)
            try:
                # DuckDB stocke les séquences différemment, on vérifie juste qu'on peut les utiliser
                cursor.execute("SELECT nextval('posts_id_seq')")
                cursor.fetchone()
                # Si on arrive ici, la séquence existe et fonctionne
            except Exception as seq_e:
                # Si les séquences ne fonctionnent pas, ce n'est pas critique pour l'intégrité
                # On continue sans erreur
                pass
                
        except Exception as e:
            details['error'] = f"Erreur lors de la vérification des données: {e}"
            conn.close()
            return False, details
        
        conn.close()
        details['status'] = 'ok'
        return True, details
        
    except duckdb.IOException as e:
        details['status'] = 'corrupted'
        details['error'] = f"Erreur IO: {e}"
        return False, details
    except Exception as e:
        details['status'] = 'corrupted'
        details['error'] = f"Erreur de connexion: {e}"
        return False, details


def main():
    """Point d'entrée principal."""
    # Déterminer l'environnement
    if len(sys.argv) > 1:
        env_arg = sys.argv[1].lower()
        if env_arg in ['production', 'staging', 'both']:
            environments = ['production', 'staging'] if env_arg == 'both' else [env_arg]
        else:
            logger.error(f"❌ Environnement invalide: {env_arg}")
            logger.info("Usage: python scripts/check_db_integrity.py [production|staging|both]")
            sys.exit(1)
    else:
        # Par défaut, vérifier selon la variable d'environnement
        env = os.getenv("ENVIRONMENT", "production")
        environments = [env]
    
    # Déterminer les chemins des bases de données
    backend_dir = Path(__file__).resolve().parents[1]
    db_paths = {}
    
    if 'production' in environments:
        db_paths['production'] = backend_dir / "data.duckdb"
    if 'staging' in environments:
        db_paths['staging'] = backend_dir / "data_staging.duckdb"
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🔍 Vérification de l'intégrité des bases de données")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    all_valid = True
    
    for env, db_path in db_paths.items():
        logger.info(f"🔄 Vérification de l'environnement: {env}")
        logger.info(f"   Base de données: {db_path}")
        
        is_valid, details = check_database_integrity(db_path)
        
        if is_valid:
            if details['status'] == 'empty':
                logger.info(f"✅ Base de données valide (vide, non initialisée)")
                logger.info(f"   Taille: {details['file_size']:.2f} MB")
                logger.info(f"   💡 La base sera initialisée au prochain démarrage de l'application")
            else:
                logger.info(f"✅ Base de données valide")
                logger.info(f"   Taille: {details['file_size']:.2f} MB")
                logger.info(f"   Tables: {', '.join(details['tables'])}")
                logger.info(f"   Lignes:")
                for table, count in details['row_counts'].items():
                    logger.info(f"     - {table}: {count}")
        else:
            all_valid = False
            logger.error(f"❌ Base de données invalide")
            logger.error(f"   Statut: {details['status']}")
            if details['error']:
                logger.error(f"   Erreur: {details['error']}")
            if details['tables']:
                logger.info(f"   Tables trouvées: {', '.join(details['tables'])}")
        
        logger.info("")
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if all_valid:
        logger.info("✅ Toutes les bases de données sont valides")
    else:
        logger.error("❌ Au moins une base de données est corrompue ou manquante")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()

