# ============================================
# Configuration automatique complète
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Configuration Automatique OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Python
Write-Host "✅ Python: $(py --version)" -ForegroundColor Green

# Vérifier/créer .env
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    & (Join-Path $ProjectRoot "create-env.ps1")
}

# Charger .env
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split [Environment]::NewLine
$dbUrl = ""
foreach ($line in $envLines) {
    if ($line -match '^\s*DATABASE_URL=(.*)$') {
        $dbUrl = $matches[1].Trim()
        break
    }
}

# Vérifier si besoin de configuration
if ([string]::IsNullOrEmpty($dbUrl) -or 
    ($dbUrl -match "localhost:5432" -and $dbUrl -match "ocft_secure_password_2026")) {
    
    Write-Host ""
    Write-Host "⚠️  Configuration PostgreSQL requise" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Pour tester rapidement, utilisez Supabase (gratuit):" -ForegroundColor Cyan
    Write-Host "1. Allez sur https://supabase.com" -ForegroundColor White
    Write-Host "2. Créez un compte et un projet" -ForegroundColor White
    Write-Host "3. Settings > Database > Connection string (URI)" -ForegroundColor White
    Write-Host "4. Collez la connection string ci-dessous" -ForegroundColor White
    Write-Host ""
    
    $newDbUrl = Read-Host "DATABASE_URL (ou Entrée pour continuer sans)"
    
    if (-not [string]::IsNullOrEmpty($newDbUrl)) {
        $envContent = $envContent -replace 'DATABASE_URL=.*', "DATABASE_URL=$newDbUrl"
        $envContent | Out-File -FilePath $envPath -Encoding utf8 -NoNewline
        $dbUrl = $newDbUrl
        Write-Host "✅ Configuration sauvegardée" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️  Le serveur démarrera mais nécessitera PostgreSQL pour fonctionner" -ForegroundColor Yellow
        Write-Host "   Configurez DATABASE_URL dans backend/.env puis redémarrez" -ForegroundColor Yellow
    }
}

# Charger toutes les variables d'environnement
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Démarrage du serveur..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 http://localhost:8000" -ForegroundColor Green
Write-Host "📍 http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📍 http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


