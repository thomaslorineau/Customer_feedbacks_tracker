# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

# Ajouter le backend au path
backend_path = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_path))

# Test si DATABASE_URL est configuré
database_url = os.getenv('DATABASE_URL', '')
if not database_url:
    print('ERROR: DATABASE_URL non configure')
    print('')
    print('Configurez avec:')
    print('  $env:DATABASE_URL = "postgresql://user:password@host:port/database"')
    sys.exit(1)

if not database_url.startswith('postgresql://'):
    print('ERROR: DATABASE_URL doit commencer par postgresql://')
    sys.exit(1)

print(f'OK: DATABASE_URL configure: {database_url.split("@")[1] if "@" in database_url else "..."}')
print('')

# Test de connexion
try:
    os.environ['DATABASE_URL'] = database_url
    os.environ['USE_POSTGRES'] = 'true'
    
    from app.database import get_db_connection, init_db
    
    print('Test de connexion...')
    conn, is_duckdb = get_db_connection()
    
    if is_duckdb:
        print('ERROR: Utilise encore DuckDB au lieu de PostgreSQL')
        sys.exit(1)
    
    print('OK: Connexion PostgreSQL reussie!')
    
    # Test query
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()[0]
    print(f'   Version: {version.split(",")[0]}')
    
    # Test init
    print('Initialisation du schema...')
    init_db()
    print('OK: Schema initialise')
    
    cursor.close()
    conn.close()
    print('')
    print('OK: Tous les tests reussis!')
    print('')
    print('Vous pouvez maintenant lancer l\'API:')
    print('  cd backend')
    print('  uvicorn app.main:app --reload')
    
except ImportError as e:
    print(f'ERROR: Erreur d\'import: {e}')
    print('Installez les dependances: pip install -r backend/requirements.txt')
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f'ERROR: Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
