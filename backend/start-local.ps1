# ============================================
# Script de démarrage local avec vérifications
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Démarrage Local - OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Python
Write-Host "1️⃣  Vérification de Python..." -ForegroundColor Yellow
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "   ❌ Python n'est pas trouvé" -ForegroundColor Red
    Write-Host "   Installez Python 3.11+ depuis https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$pythonVersion = py --version
Write-Host "   ✅ $pythonVersion" -ForegroundColor Green

# Vérifier le fichier .env
Write-Host ""
Write-Host "2️⃣  Vérification de la configuration..." -ForegroundColor Yellow
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "   ⚠️  Fichier .env non trouvé" -ForegroundColor Yellow
    Write-Host "   Création du fichier .env..." -ForegroundColor Yellow
    & (Join-Path $ProjectRoot "create-env.ps1")
    Write-Host ""
    Write-Host "   ⚠️  IMPORTANT: Configurez DATABASE_URL dans backend/.env" -ForegroundColor Red
    Write-Host "   Voir backend/SETUP_POSTGRES.md pour les instructions" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Appuyez sur Entrée après avoir configuré DATABASE_URL..."
    Read-Host
}

# Charger les variables d'environnement depuis .env
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split "`n"
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Vérifier DATABASE_URL
$dbUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
if ([string]::IsNullOrEmpty($dbUrl) -or $dbUrl -match "localhost:5432" -and $dbUrl -match "ocft_secure_password_2026") {
    Write-Host "   ⚠️  DATABASE_URL n'est pas configuré ou utilise les valeurs par défaut" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Options:" -ForegroundColor Cyan
    Write-Host "   1. Service cloud gratuit (Supabase/Neon) - RECOMMANDÉ" -ForegroundColor White
    Write-Host "   2. PostgreSQL local" -ForegroundColor White
    Write-Host "   3. Docker PostgreSQL" -ForegroundColor White
    Write-Host ""
    Write-Host "   Voir backend/SETUP_POSTGRES.md pour les instructions détaillées" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continuer quand même? (o/N)"
    if ($continue -ne "o" -and $continue -ne "O") {
        exit 0
    }
} else {
    Write-Host "   ✅ DATABASE_URL configuré" -ForegroundColor Green
}

# Tester la connexion PostgreSQL (optionnel)
Write-Host ""
Write-Host "3️⃣  Test de connexion PostgreSQL..." -ForegroundColor Yellow
try {
    $testScript = @"
import os
import sys
sys.path.insert(0, r'$ProjectRoot')
os.environ['DATABASE_URL'] = r'$dbUrl'
os.environ['USE_POSTGRES'] = 'true'
try:
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    print('✅ Connexion PostgreSQL réussie!')
    conn.close()
except Exception as e:
    print(f'❌ Erreur de connexion: {e}')
    sys.exit(1)
"@
    $testScript | py -
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ⚠️  La connexion a échoué, mais on continue..." -ForegroundColor Yellow
        Write-Host "   Assurez-vous que PostgreSQL est démarré et que DATABASE_URL est correct" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Impossible de tester la connexion: $_" -ForegroundColor Yellow
}

# Vérifier les dépendances
Write-Host ""
Write-Host "4️⃣  Vérification des dépendances..." -ForegroundColor Yellow
try {
    py -c "import fastapi; import psycopg2; print('✅ Dépendances OK')" 2>&1 | Out-Null
    Write-Host "   ✅ Dépendances installées" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Dépendances manquantes" -ForegroundColor Red
    Write-Host "   Installez avec: py -m pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Démarrer le serveur
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Démarrage du serveur..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 API:  http://localhost:8000" -ForegroundColor Green
Write-Host "📍 Docs: http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📍 Dashboard: http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot

# Charger les variables d'environnement pour uvicorn
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split "`n"
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Démarrer uvicorn
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


