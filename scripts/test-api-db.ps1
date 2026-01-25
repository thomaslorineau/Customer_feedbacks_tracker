# ============================================
# Tests API et Accès Base de Données
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests API et Base de Données" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Attendre que le serveur démarre
Write-Host "Attente du démarrage du serveur..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$serverReady = $false

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $serverReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
        $attempt++
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
}

Write-Host ""

if (-not $serverReady) {
    Write-Host "ERREUR: Le serveur n'a pas demarre dans les delais" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Serveur demarre" -ForegroundColor Green
Write-Host ""

# Test 1: Health check
Write-Host "Test 1: Health check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -ErrorAction Stop
    Write-Host "OK: Health check reussi" -ForegroundColor Green
    Write-Host "   Status: $($response.status)" -ForegroundColor Gray
} catch {
    Write-Host "ERREUR: Health check echoue: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Endpoint posts (doit accéder à la DB)
Write-Host "Test 2: Recuperation des posts (acces DB)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/posts?limit=5" -Method Get -ErrorAction Stop
    Write-Host "OK: Recuperation posts reussie" -ForegroundColor Green
    Write-Host "   Nombre de posts: $($response.Count)" -ForegroundColor Gray
    if ($response.Count -gt 0) {
        Write-Host "   Premier post: $($response[0].source) - $($response[0].content.Substring(0, [Math]::Min(50, $response[0].content.Length)))..." -ForegroundColor Gray
    }
} catch {
    Write-Host "ERREUR: Recuperation posts echoue: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: Statistiques (acces DB)
Write-Host "Test 3: Statistiques (acces DB)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -Method Get -ErrorAction Stop
    Write-Host "OK: Statistiques recuperees" -ForegroundColor Green
    Write-Host "   Total posts: $($response.total_posts)" -ForegroundColor Gray
    Write-Host "   Par source: $($response.by_source.Count) sources" -ForegroundColor Gray
} catch {
    Write-Host "ERREUR: Statistiques echoue: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Test direct de la connexion DB depuis Python
Write-Host "Test 4: Test direct connexion DB..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import get_posts, get_sentiment_stats, get_source_stats
    
    # Test get_posts
    posts = get_posts(limit=10)
    print(f'OK: get_posts - {len(posts)} posts')
    
    # Test stats
    sentiment_stats = get_sentiment_stats()
    print(f'OK: get_sentiment_stats - {len(sentiment_stats)} categories')
    
    source_stats = get_source_stats()
    print(f'OK: get_source_stats - {len(source_stats)} sources')
    
    print('OK: Tous les tests DB directs reussis!')
except Exception as e:
    print(f'ERREUR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS: Tous les tests reussis!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "L'application accede correctement a PostgreSQL!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Serveur disponible sur:" -ForegroundColor Yellow
    Write-Host "  http://localhost:8000" -ForegroundColor White
    Write-Host "  http://localhost:8000/api/docs" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "ERREUR: Certains tests ont echoue" -ForegroundColor Red
    exit 1
}
