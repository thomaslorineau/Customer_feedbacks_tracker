# ============================================
# Démarrage Serveur Local (Configuration OCFT)
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage Serveur Local" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration PostgreSQL (même que production)
$env:DATABASE_URL = "postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker"
$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"
$env:REDIS_URL = "redis://localhost:6379/0"

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Base de données: ocft_tracker" -ForegroundColor Gray
Write-Host "  Utilisateur: ocft_user" -ForegroundColor Gray
Write-Host ""

# Vérifier PostgreSQL
Write-Host "Vérification de PostgreSQL..." -ForegroundColor Yellow
$pgRunning = netstat -an | Select-String "5432" | Select-String "LISTENING"

if (-not $pgRunning) {
    Write-Host "⚠️  PostgreSQL n'est pas démarré" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Démarrez PostgreSQL avec:" -ForegroundColor Cyan
    Write-Host "  .\scripts\start-postgres-local.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Ou configurez PostgreSQL avec:" -ForegroundColor Cyan
    Write-Host "  .\setup-postgres-manual.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✅ PostgreSQL est démarré" -ForegroundColor Green

# Aller dans backend
Set-Location "$ProjectRoot\backend"

Write-Host ""
Write-Host "Démarrage du serveur..." -ForegroundColor Green
Write-Host "  API:  http://localhost:8000" -ForegroundColor White
Write-Host "  Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
