#!/usr/bin/env python3
"""
Script de migration pour fusionner les sources GitHub Issues et GitHub Discussions en une seule source "GitHub".

Ce script met à jour tous les posts dans la base de données qui ont comme source :
- "GitHub Issues" → "GitHub"
- "GitHub Discussions" → "GitHub"
"""

import sqlite3
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour importer db
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import DB_FILE

def migrate_github_sources():
    """Migre les sources GitHub Issues et GitHub Discussions vers GitHub."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Compter les posts à migrer
        c.execute("SELECT COUNT(*) FROM posts WHERE source IN ('GitHub Issues', 'GitHub Discussions')")
        count = c.fetchone()[0]
        
        if count == 0:
            print("✅ Aucun post à migrer. Toutes les sources GitHub sont déjà normalisées.")
            return
        
        print(f"📊 {count} posts trouvés avec 'GitHub Issues' ou 'GitHub Discussions'")
        
        # Migrer GitHub Issues
        c.execute("UPDATE posts SET source = 'GitHub' WHERE source = 'GitHub Issues'")
        issues_count = c.rowcount
        print(f"✅ {issues_count} posts 'GitHub Issues' → 'GitHub'")
        
        # Migrer GitHub Discussions
        c.execute("UPDATE posts SET source = 'GitHub' WHERE source = 'GitHub Discussions'")
        discussions_count = c.rowcount
        print(f"✅ {discussions_count} posts 'GitHub Discussions' → 'GitHub'")
        
        # Commit les changements
        conn.commit()
        
        print(f"\n✅ Migration terminée : {issues_count + discussions_count} posts migrés vers 'GitHub'")
        
        # Vérifier le résultat
        c.execute("SELECT COUNT(*) FROM posts WHERE source = 'GitHub'")
        total_github = c.fetchone()[0]
        print(f"📊 Total posts GitHub après migration : {total_github}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur lors de la migration : {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Migration des sources GitHub...")
    migrate_github_sources()
    print("✅ Migration terminée avec succès")

