#!/usr/bin/env python3
"""Script pour réparer ou recréer la base de données DuckDB corrompue."""
import os
import sys
from pathlib import Path
import duckdb

def repair_database(db_file: str):
    """Réparer ou recréer la base de données DuckDB."""
    db_path = Path(db_file)
    backup_path = db_path.with_suffix('.duckdb.backup')
    
    print(f"🔍 Vérification de la base de données: {db_file}")
    
    # Créer un backup si le fichier existe
    if db_path.exists():
        print(f"📦 Création d'un backup: {backup_path}")
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup créé: {backup_path}")
        except Exception as e:
            print(f"⚠️  Impossible de créer le backup: {e}")
    
    # Essayer de se connecter
    try:
        conn = duckdb.connect(str(db_path))
        print("✅ Connexion réussie à la base existante")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("🔧 Tentative de réparation...")
    
    # Supprimer le fichier corrompu et en créer un nouveau
    try:
        if db_path.exists():
            print(f"🗑️  Suppression du fichier corrompu...")
            db_path.unlink()
        
        print(f"✨ Création d'une nouvelle base de données...")
        conn = duckdb.connect(str(db_path))
        
        # Initialiser les tables de base
        c = conn.cursor()
        c.execute("CREATE SEQUENCE IF NOT EXISTS posts_id_seq START 1")
        c.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id BIGINT PRIMARY KEY DEFAULT nextval('posts_id_seq'),
                source TEXT,
                author TEXT,
                content TEXT,
                url TEXT,
                created_at TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                language TEXT DEFAULT 'unknown',
                country TEXT,
                relevance_score REAL DEFAULT 0.0
            )
        ''')
        
        c.execute("CREATE SEQUENCE IF NOT EXISTS saved_queries_id_seq START 1")
        c.execute('''
            CREATE TABLE IF NOT EXISTS saved_queries (
                id BIGINT PRIMARY KEY DEFAULT nextval('saved_queries_id_seq'),
                keyword TEXT UNIQUE,
                created_at TEXT
            )
        ''')
        
        c.execute("CREATE SEQUENCE IF NOT EXISTS scraping_logs_id_seq START 1")
        c.execute('''
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id BIGINT PRIMARY KEY DEFAULT nextval('scraping_logs_id_seq'),
                timestamp TEXT NOT NULL,
                source TEXT,
                level TEXT,
                message TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute("CREATE SEQUENCE IF NOT EXISTS base_keywords_id_seq START 1")
        c.execute('''
            CREATE TABLE IF NOT EXISTS base_keywords (
                id BIGINT PRIMARY KEY DEFAULT nextval('base_keywords_id_seq'),
                category TEXT NOT NULL,
                keyword TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, keyword)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT,
                progress_total INTEGER,
                progress_completed INTEGER,
                results TEXT,
                errors TEXT,
                cancelled INTEGER DEFAULT 0,
                error TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Nouvelle base de données créée avec succès: {db_file}")
        print(f"💡 Si vous aviez des données importantes, elles sont dans: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la réparation: {e}")
        return False

if __name__ == "__main__":
    # Déterminer le fichier de base de données selon l'environnement
    # Vérifier d'abord les arguments de ligne de commande
    if len(sys.argv) > 1:
        env_arg = sys.argv[1].lower()
        if env_arg == "staging":
            db_file = "data_staging.duckdb"
        elif env_arg == "production":
            db_file = "data.duckdb"
        else:
            print(f"❌ Environnement invalide: {env_arg}")
            print("Usage: python repair_db.py [production|staging]")
            sys.exit(1)
    else:
        # Utiliser la variable d'environnement si aucun argument
        env = os.getenv("ENVIRONMENT", "production")
        if env == "staging":
            db_file = "data_staging.duckdb"
        else:
            db_file = "data.duckdb"
    
    # S'assurer qu'on est dans le bon répertoire (backend)
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    success = repair_database(db_file)
    sys.exit(0 if success else 1)


