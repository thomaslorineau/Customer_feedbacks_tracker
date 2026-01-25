# ============================================
# Démarrer le serveur et tester l'accès DB
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage Serveur et Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que PostgreSQL est démarré
Write-Host "Vérification PostgreSQL..." -ForegroundColor Yellow
$PgCtl = "$env:USERPROFILE\scoop\apps\postgresql\current\bin\pg_ctl.exe"
$DataDir = "$env:USERPROFILE\postgresql-data"

$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -notmatch "server is running") {
    Write-Host "Démarrage de PostgreSQL..." -ForegroundColor Yellow
    & $PgCtl -D $DataDir start
    Start-Sleep -Seconds 3
    
    $Status = & $PgCtl -D $DataDir status 2>&1
    if ($Status -notmatch "server is running") {
        Write-Host "ERREUR: PostgreSQL n'a pas démarré" -ForegroundColor Red
        exit 1
    }
}
Write-Host "OK: PostgreSQL démarré" -ForegroundColor Green

# Configurer les variables d'environnement
$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"

Write-Host ""
Write-Host "Test de connexion à la base de données..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\backend"

# Test 1: Connexion simple
python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    
    if is_duckdb:
        print('ERREUR: Utilise encore DuckDB')
        sys.exit(1)
    
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM posts')
    count = cursor.fetchone()[0]
    print(f'OK: Connexion reussie - {count} posts dans la base')
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f'ERREUR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Test de connexion echoue" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Test des fonctions de base de données..." -ForegroundColor Yellow

# Test 2: Fonctions DB
python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import insert_post, get_posts, get_saved_queries
    
    # Test insert_post
    test_post = {
        'source': 'TEST',
        'author': 'Test User',
        'content': 'Test de connexion PostgreSQL - ' + str(__import__('datetime').datetime.now()),
        'url': 'https://test.example.com/test-' + str(__import__('time').time()),
        'created_at': __import__('datetime').datetime.now().isoformat(),
        'sentiment_score': 0.5,
        'sentiment_label': 'neutral',
        'language': 'fr',
        'relevance_score': 0.8
    }
    
    post_id = insert_post(test_post)
    if post_id:
        print(f'OK: insert_post fonctionne - Post ID: {post_id}')
    else:
        print('OK: insert_post fonctionne (doublon detecte, normal)')
    
    # Test get_posts
    posts = get_posts(limit=5)
    print(f'OK: get_posts fonctionne - {len(posts)} posts recuperes')
    
    # Test get_saved_queries
    queries = get_saved_queries()
    print(f'OK: get_saved_queries fonctionne - {len(queries)} queries')
    
    print('OK: Toutes les fonctions DB fonctionnent!')
except Exception as e:
    print(f'ERREUR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Test des fonctions echoue" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Démarrage du serveur FastAPI..." -ForegroundColor Yellow
Write-Host "Le serveur va démarrer en arrière-plan" -ForegroundColor Gray
Write-Host "URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

# Démarrer le serveur
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
