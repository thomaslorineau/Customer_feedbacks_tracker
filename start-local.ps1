# ============================================
# Script de démarrage local (sans Docker)
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage Local - OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERREUR: Python n'est pas trouvé" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "Python: $pythonVersion" -ForegroundColor Green

# Aller dans le répertoire backend
Set-Location "$ProjectRoot\backend"

# Vérifier les dépendances
Write-Host ""
Write-Host "Vérification des dépendances..." -ForegroundColor Yellow
try {
    python -c "import fastapi; import psycopg2; print('OK')" 2>&1 | Out-Null
    Write-Host "Dépendances OK" -ForegroundColor Green
} catch {
    Write-Host "ERREUR: Dépendances manquantes" -ForegroundColor Red
    Write-Host "Installez avec: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Configuration PostgreSQL
Write-Host ""
Write-Host "Configuration de la base de données..." -ForegroundColor Yellow

# Option 1: Service cloud (Supabase/Neon) - RECOMMANDÉ
Write-Host ""
Write-Host "Choisissez votre option PostgreSQL:" -ForegroundColor Cyan
Write-Host "1. Service cloud gratuit (Supabase/Neon) - RECOMMANDÉ" -ForegroundColor White
Write-Host "2. PostgreSQL local (si installé)" -ForegroundColor White
Write-Host "3. Utiliser la configuration par défaut" -ForegroundColor White
Write-Host ""
$choice = Read-Host "Votre choix (1/2/3)"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "Pour utiliser un service cloud gratuit:" -ForegroundColor Yellow
    Write-Host "1. Créez un compte sur https://supabase.com" -ForegroundColor White
    Write-Host "2. Créez un nouveau projet" -ForegroundColor White
    Write-Host "3. Récupérez la connection string depuis Settings > Database" -ForegroundColor White
    Write-Host ""
    $dbUrl = Read-Host "Collez votre DATABASE_URL PostgreSQL"
    $env:DATABASE_URL = $dbUrl
} elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "Configuration PostgreSQL local..." -ForegroundColor Yellow
    $dbUser = Read-Host "Utilisateur PostgreSQL (défaut: postgres)" 
    if ([string]::IsNullOrEmpty($dbUser)) { $dbUser = "postgres" }
    
    $dbPassword = Read-Host "Mot de passe PostgreSQL" -AsSecureString
    $dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword))
    
    $dbName = Read-Host "Nom de la base (défaut: ocft_tracker)"
    if ([string]::IsNullOrEmpty($dbName)) { $dbName = "ocft_tracker" }
    
    $env:DATABASE_URL = "postgresql://${dbUser}:${dbPasswordPlain}@localhost:5432/${dbName}"
} else {
    # Configuration par défaut (nécessite PostgreSQL local ou cloud)
    Write-Host ""
    Write-Host "Utilisation de la configuration par défaut..." -ForegroundColor Yellow
    Write-Host "NOTE: Vous devez avoir PostgreSQL configuré" -ForegroundColor Yellow
    $env:DATABASE_URL = "postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker"
}

$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"
$env:REDIS_URL = "redis://localhost:6379/0"

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  DATABASE_URL: $($env:DATABASE_URL -replace ':[^:@]+@', ':****@')" -ForegroundColor Gray
Write-Host "  REDIS_URL: $env:REDIS_URL" -ForegroundColor Gray
Write-Host ""

# Tester la connexion PostgreSQL
Write-Host "Test de connexion PostgreSQL..." -ForegroundColor Yellow
try {
    python -c "
import os
import sys
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'
from app.database import get_db_connection
conn, is_duckdb = get_db_connection()
print('OK: Connexion PostgreSQL réussie')
conn.close()
" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERREUR: Impossible de se connecter à PostgreSQL" -ForegroundColor Red
        Write-Host "Vérifiez votre configuration DATABASE_URL" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "1. Utiliser un service cloud gratuit: https://supabase.com" -ForegroundColor White
        Write-Host "2. Installer PostgreSQL localement" -ForegroundColor White
        Write-Host "3. Utiliser Docker Desktop pour PostgreSQL" -ForegroundColor White
        exit 1
    }
} catch {
    Write-Host "ERREUR lors du test de connexion" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage de l'API..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API:  http://localhost:8000" -ForegroundColor Green
Write-Host "Docs: http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

# Démarrer l'API
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
