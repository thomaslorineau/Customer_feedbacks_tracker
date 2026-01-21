#!/usr/bin/env python3
"""Script pour vérifier l'état de la base de données et des backups."""

import sys
from pathlib import Path
import duckdb
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def check_db(db_path):
    """Vérifier le nombre de posts dans une base de données."""
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM posts')
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        return f"Erreur: {e}"

def main():
    print("🔍 Vérification de l'état des bases de données...\n")
    
    backend_dir = Path(__file__).resolve().parents[1]
    current_db = backend_dir / "data.duckdb"
    
    # Vérifier la base actuelle
    print(f"📊 Base actuelle (data.duckdb):")
    current_count = check_db(current_db)
    print(f"   Posts: {current_count}\n")
    
    # Vérifier les backups
    print("📦 Backups disponibles:")
    backups = [
        backend_dir / "data_backup_20260121_125342.duckdb",
        backend_dir / "data_backup_20260120_115448.duckdb",
        backend_dir / "data_backup_20260120_093014.duckdb",
        backend_dir / "backups" / "production_data_20260118_002325.duckdb",
        backend_dir / "backups" / "production_data_20260118_001558.duckdb",
    ]
    
    backup_info = []
    for backup in backups:
        if backup.exists():
            count = check_db(backup)
            size_mb = backup.stat().st_size / (1024 * 1024)
            backup_info.append({
                'path': backup,
                'name': backup.name,
                'count': count,
                'size_mb': size_mb,
                'modified': datetime.fromtimestamp(backup.stat().st_mtime)
            })
            print(f"   {backup.name}:")
            print(f"      Posts: {count}")
            print(f"      Taille: {size_mb:.2f} MB")
            print(f"      Modifié: {backup_info[-1]['modified']}\n")
    
    # Trouver le backup avec le plus de posts
    if backup_info:
        best_backup = max(backup_info, key=lambda x: x['count'] if isinstance(x['count'], int) else 0)
        print(f"✅ Backup avec le plus de posts: {best_backup['name']}")
        print(f"   Posts: {best_backup['count']}")
        
        if isinstance(current_count, int) and isinstance(best_backup['count'], int):
            if best_backup['count'] > current_count:
                print(f"\n⚠️  La base actuelle a moins de posts que le backup le plus récent!")
                print(f"   Actuel: {current_count} posts")
                print(f"   Backup: {best_backup['count']} posts")
                print(f"\n💡 Pour restaurer depuis le backup:")
                print(f"   python scripts/restore_from_backup.py {best_backup['name']}")

if __name__ == "__main__":
    main()

