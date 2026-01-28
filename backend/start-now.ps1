# ============================================
# Démarrage immédiat du serveur
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Démarrage OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier .env
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "Création de .env..." -ForegroundColor Yellow
    & (Join-Path $ProjectRoot "create-env.ps1")
}

# Charger .env
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split [Environment]::NewLine
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

Write-Host "✅ Configuration chargée" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Serveur démarré!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Application:  http://localhost:8000" -ForegroundColor Green
Write-Host "📍 API Docs:     http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📍 Dashboard:    http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  Si PostgreSQL n'est pas configuré, configurez DATABASE_URL dans .env" -ForegroundColor Yellow
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


