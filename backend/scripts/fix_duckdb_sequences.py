#!/usr/bin/env python3
"""Fix les séquences auto-increment pour DuckDB"""

import sys
from pathlib import Path
import duckdb

backend_dir = Path(__file__).resolve().parents[1]

def fix_sequences(db_file):
    """Fix les séquences pour auto-increment."""
    print(f"Fixing sequences in {db_file}...")
    conn = duckdb.connect(str(db_file))
    cursor = conn.cursor()
    
    try:
        # Pour posts: créer séquence et définir default
        cursor.execute("SELECT MAX(id) FROM posts")
        max_id = cursor.fetchone()[0] or 0
        cursor.execute(f"CREATE SEQUENCE IF NOT EXISTS posts_id_seq START {max_id + 1}")
        print(f"✅ Sequence posts_id_seq créée (START {max_id + 1})")
        
        # Pour saved_queries
        try:
            cursor.execute("SELECT MAX(id) FROM saved_queries")
            max_id = cursor.fetchone()[0] or 0
            cursor.execute(f"CREATE SEQUENCE IF NOT EXISTS saved_queries_id_seq START {max_id + 1}")
            print(f"✅ Sequence saved_queries_id_seq créée (START {max_id + 1})")
        except Exception as e:
            print(f"⚠️  saved_queries table might not exist: {e}")
        
        # Pour scraping_logs
        try:
            cursor.execute("SELECT MAX(id) FROM scraping_logs")
            max_id = cursor.fetchone()[0] or 0
            cursor.execute(f"CREATE SEQUENCE IF NOT EXISTS scraping_logs_id_seq START {max_id + 1}")
            print(f"✅ Sequence scraping_logs_id_seq créée (START {max_id + 1})")
        except Exception as e:
            print(f"⚠️  scraping_logs table might not exist: {e}")
        
        conn.commit()
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()
    
    return True

if __name__ == '__main__':
    import os
    env = os.getenv("ENVIRONMENT", "production")
    
    if env == "staging":
        db_file = backend_dir / "data_staging.duckdb"
    else:
        db_file = backend_dir / "data.duckdb"
    
    if fix_sequences(db_file):
        print("✅ Sequences fixed!")
    else:
        print("❌ Failed to fix sequences")
        sys.exit(1)



