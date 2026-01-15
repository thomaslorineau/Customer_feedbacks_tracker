"""Fix EU country codes - remove invalid 'EU' codes"""
import sqlite3
from pathlib import Path
from app import db

def fix_eu_codes():
    conn = sqlite3.connect(db.DB_FILE)
    c = conn.cursor()
    
    # Remove EU codes
    c.execute('UPDATE posts SET country = NULL WHERE country = ?', ('EU',))
    updated = c.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Removed 'EU' code from {updated} posts")
    print("Run 'python -m app.migrate_add_country' to re-detect countries")

if __name__ == '__main__':
    fix_eu_codes()



