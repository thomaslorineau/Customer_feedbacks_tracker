"""
Initialize PostgreSQL database using Python (alternative to psql).
Useful if psql is not available or you prefer Python.
"""
import os
import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Configurer les variables d'environnement
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker'
)
os.environ['DATABASE_URL'] = DATABASE_URL

if __name__ == '__main__':
    print("=" * 60)
    print("Initialisation de la base de données PostgreSQL")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print()
    
    try:
        # Importer et initialiser
        from app.database import init_db
        
        print("Initialisation du schéma...")
        init_db()
        print("✅ Base de données initialisée avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
