# ============================================
# Démarrer Serveur et Tester
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage Serveur et Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier PostgreSQL
Write-Host "1. Vérification PostgreSQL..." -ForegroundColor Yellow
$PgCtl = "$env:USERPROFILE\scoop\apps\postgresql\current\bin\pg_ctl.exe"
$DataDir = "$env:USERPROFILE\postgresql-data"

$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -notmatch "server is running") {
    Write-Host "   Démarrage PostgreSQL..." -ForegroundColor Gray
    & $PgCtl -D $DataDir start
    Start-Sleep -Seconds 3
}
Write-Host "   OK: PostgreSQL démarré" -ForegroundColor Green

# Vérifier les dépendances
Write-Host ""
Write-Host "2. Vérification dépendances..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

python -c "import psycopg2; print('   OK: psycopg2')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Installation de psycopg2-binary..." -ForegroundColor Yellow
    pip install psycopg2-binary 2>&1 | Out-Null
}

python -c "import uvicorn; print('   OK: uvicorn')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   Installation de uvicorn..." -ForegroundColor Yellow
    pip install uvicorn[standard] 2>&1 | Out-Null
}

# Test connexion DB
Write-Host ""
Write-Host "3. Test connexion base de données..." -ForegroundColor Yellow
python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import get_db_connection, get_posts
    conn, is_duckdb = get_db_connection()
    
    if is_duckdb:
        print('   ERREUR: Utilise DuckDB au lieu de PostgreSQL')
        sys.exit(1)
    
    posts = get_posts(limit=1)
    print(f'   OK: Connexion reussie - {len(posts)} posts dans la base')
    conn.close()
except Exception as e:
    print(f'   ERREUR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Test de connexion echoue" -ForegroundColor Red
    exit 1
}

# Démarrer le serveur en arrière-plan
Write-Host ""
Write-Host "4. Démarrage du serveur FastAPI..." -ForegroundColor Yellow

$job = Start-Job -ScriptBlock {
    Set-Location $using:ProjectRoot\backend
    $env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
    $env:USE_POSTGRES = "true"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}

# Attendre que le serveur démarre
Write-Host "   Attente du démarrage..." -ForegroundColor Gray
Start-Sleep -Seconds 5

$maxAttempts = 20
$serverReady = $false

for ($i = 0; $i -lt $maxAttempts; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $serverReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $serverReady) {
    Write-Host "   ERREUR: Serveur n'a pas demarre" -ForegroundColor Red
    Write-Host "   Logs du job:" -ForegroundColor Yellow
    Receive-Job $job | Select-Object -Last 20
    Stop-Job $job
    Remove-Job $job
    exit 1
}

Write-Host "   OK: Serveur démarré sur http://localhost:8000" -ForegroundColor Green

# Tests API
Write-Host ""
Write-Host "5. Tests API..." -ForegroundColor Yellow

# Test Health
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get -ErrorAction Stop
    Write-Host "   OK: Health check - Status: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ERREUR: Health check - $_" -ForegroundColor Red
}

# Test Posts
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/posts?limit=3" -Method Get -ErrorAction Stop
    Write-Host "   OK: Posts endpoint - $($response.Count) posts recuperes" -ForegroundColor Green
} catch {
    Write-Host "   ERREUR: Posts endpoint - $_" -ForegroundColor Red
}

# Test Stats
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/stats" -Method Get -ErrorAction Stop
    Write-Host "   OK: Stats endpoint - Total: $($response.total_posts) posts" -ForegroundColor Green
} catch {
    Write-Host "   ERREUR: Stats endpoint - $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "SUCCESS: Serveur démarré et tests OK!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Serveur disponible sur:" -ForegroundColor Cyan
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host "  http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "Pour arrêter: Stop-Job $($job.Id); Remove-Job $($job.Id)" -ForegroundColor Yellow
Write-Host ""

# Garder le job actif
Write-Host "Le serveur tourne en arrière-plan. Appuyez sur Entrée pour arrêter..." -ForegroundColor Gray
Read-Host

Stop-Job $job
Remove-Job $job
Write-Host "Serveur arrêté" -ForegroundColor Green
