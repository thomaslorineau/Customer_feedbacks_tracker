#!/usr/bin/env python3
"""Script pour restaurer la base de données depuis un backup."""

import sys
import shutil
from pathlib import Path
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python restore_from_backup.py <backup_filename>")
        print("\nBackups disponibles:")
        backend_dir = Path(__file__).resolve().parents[1]
        backups = list(backend_dir.glob("data_backup_*.duckdb"))
        backups.extend((backend_dir / "backups").glob("*.duckdb"))
        for backup in backups:
            if backup.exists():
                size_mb = backup.stat().st_size / (1024 * 1024)
                print(f"  - {backup.name} ({size_mb:.2f} MB)")
        sys.exit(1)
    
    backup_name = sys.argv[1]
    backend_dir = Path(__file__).resolve().parents[1]
    
    # Chercher le backup
    backup_path = None
    possible_paths = [
        backend_dir / backup_name,
        backend_dir / "backups" / backup_name,
    ]
    
    for path in possible_paths:
        if path.exists():
            backup_path = path
            break
    
    if not backup_path:
        print(f"❌ Backup '{backup_name}' introuvable")
        sys.exit(1)
    
    current_db = backend_dir / "data.duckdb"
    
    # Créer un backup de la base actuelle avant restauration
    if current_db.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup = backend_dir / f"data_before_restore_{timestamp}.duckdb"
        print(f"📦 Création d'un backup de sécurité: {safety_backup.name}")
        shutil.copy2(current_db, safety_backup)
    
    # Restaurer depuis le backup
    print(f"🔄 Restauration depuis: {backup_path.name}")
    shutil.copy2(backup_path, current_db)
    
    print(f"✅ Base de données restaurée avec succès!")
    print(f"   Backup utilisé: {backup_path.name}")
    print(f"   Taille: {backup_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"\n💡 Redémarrez le serveur pour appliquer les changements")

if __name__ == "__main__":
    main()

