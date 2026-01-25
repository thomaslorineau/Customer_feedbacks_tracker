# Test direct du serveur
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"

Write-Host "Test de démarrage du serveur..." -ForegroundColor Yellow
Write-Host ""

# Tester l'import d'abord
python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    print('Test import app.main...')
    from app.main import app
    print('OK: Import reussi')
    
    print('Test connexion DB...')
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    print(f'OK: Connexion DB - is_duckdb={is_duckdb}')
    conn.close()
    
    print('OK: Tous les tests pre-demarrage reussis')
except Exception as e:
    print(f'ERREUR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Tests pre-demarrage echoues" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Démarrage du serveur (Ctrl+C pour arrêter)..." -ForegroundColor Green
Write-Host ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
