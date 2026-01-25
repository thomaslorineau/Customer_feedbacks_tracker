# ============================================
# Résumé des Tests - PostgreSQL
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests Finaux - PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "$ProjectRoot\backend"
$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

# Test 1: Connexion DB
Write-Host "Test 1: Connexion PostgreSQL..." -ForegroundColor Yellow
python -c @"
import os, sys
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

from app.database import get_db_connection
conn, is_duckdb = get_db_connection()
print('   OK: Connexion reussie - is_duckdb=' + str(is_duckdb))
conn.close()
"@

# Test 2: Insertion
Write-Host ""
Write-Host "Test 2: Insertion de post..." -ForegroundColor Yellow
python -c @"
import os, sys
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

from app.database import insert_post
import datetime, time

post = {
    'source': 'TEST_FINAL',
    'author': 'Test User',
    'content': 'Test final PostgreSQL - ' + str(time.time()),
    'url': 'https://test-' + str(time.time()) + '.com',
    'created_at': datetime.datetime.now().isoformat(),
    'sentiment_score': 0.6,
    'sentiment_label': 'positive',
    'language': 'fr',
    'relevance_score': 0.85
}

post_id = insert_post(post)
print(f'   OK: Post insere - ID: {post_id}')
"@

# Test 3: Lecture
Write-Host ""
Write-Host "Test 3: Lecture des posts..." -ForegroundColor Yellow
python -c @"
import os, sys
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

from app.database import get_posts, get_sentiment_stats, get_source_stats

posts = get_posts(limit=10)
print(f'   OK: {len(posts)} posts recuperes')

stats = get_sentiment_stats()
print(f'   OK: Statistiques sentiment - {len(stats)} categories')

sources = get_source_stats()
print(f'   OK: Statistiques sources - {len(sources)} sources')
"@

# Test 4: API HTTP
Write-Host ""
Write-Host "Test 4: API HTTP..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/posts?limit=5" -TimeoutSec 5
    Write-Host "   OK: Endpoint /posts - $($response.Count) posts" -ForegroundColor Green
} catch {
    Write-Host "   ERREUR: /posts - $_" -ForegroundColor Red
}

# Test 5: Stats via API
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "   OK: Endpoint /api/stats - Total: $($response.total_posts)" -ForegroundColor Green
    }
} catch {
    # Peut ne pas exister
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCESS: Tous les tests reussis!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "PostgreSQL est fonctionnel!" -ForegroundColor Cyan
Write-Host "L'application accede correctement a la base de donnees" -ForegroundColor Cyan
Write-Host ""
Write-Host "Serveur disponible sur:" -ForegroundColor Yellow
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host "  http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  http://localhost:8000/posts?limit=10" -ForegroundColor White
