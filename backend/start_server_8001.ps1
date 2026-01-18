# Script de démarrage du serveur staging sur le port 8001
# Usage: .\start_server_8001.ps1

$env:ENVIRONMENT = "staging"
$env:USE_DUCKDB = "true"
$env:APP_PORT = "8001"

Write-Host "🚀 Démarrage du serveur STAGING sur le port 8001..." -ForegroundColor Cyan
Write-Host "   Environnement: staging" -ForegroundColor White
Write-Host "   Base de données: DuckDB (data_staging.duckdb)" -ForegroundColor White
Write-Host "   Port: 8001" -ForegroundColor White
Write-Host "   URL: http://127.0.0.1:8001" -ForegroundColor White
Write-Host "   Documentation: http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host ""

# Vérifier que nous sommes dans le bon répertoire
if (-not (Test-Path "app\main.py")) {
    Write-Host "❌ Erreur: app\main.py introuvable. Assurez-vous d'être dans le répertoire backend." -ForegroundColor Red
    exit 1
}

# Vérifier que duckdb est installé
try {
    python -c "import duckdb" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Installation de duckdb..." -ForegroundColor Yellow
        pip install duckdb
    }
} catch {
    Write-Host "⚠️  Installation de duckdb..." -ForegroundColor Yellow
    pip install duckdb
}

# Tente d'arrêter les processus Python existants sur le port 8001
try {
    Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object OwningProcess | ForEach-Object {
        if ($_.OwningProcess -ne 0) {
            Write-Host "Arrêt du processus $($_.OwningProcess) sur le port 8001..." -ForegroundColor Yellow
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
} catch {
    # Ignore si la commande échoue
}

# Démarrer le serveur Uvicorn
Write-Host "✅ Démarrage du serveur staging..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host '🚀 Serveur STAGING sur le port 8001...' -ForegroundColor Cyan; Write-Host '   URL: http://localhost:8001' -ForegroundColor White; Write-Host ''; `$env:ENVIRONMENT='staging'; `$env:USE_DUCKDB='true'; `$env:APP_PORT='8001'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

Write-Host "`n Le serveur démarre... Vérifiez dans quelques secondes avec: http://localhost:8001`n" -ForegroundColor Yellow

# Vérification que le serveur est bien démarré
$maxAttempts = 6
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/version" -UseBasicParsing -TimeoutSec 3
        Write-Host "`n ✅ SERVEUR STAGING DÉMARRÉ AVEC SUCCÈS!`n" -ForegroundColor Green
        Write-Host "    URL: http://localhost:8001" -ForegroundColor Cyan
        Write-Host "    API Docs: http://localhost:8001/docs" -ForegroundColor Cyan
        Write-Host "    Logs: http://localhost:8001/logs" -ForegroundColor Cyan
        Write-Host "`n   Status: $($response.StatusCode)" -ForegroundColor White
        $version = ($response.Content | ConvertFrom-Json).version
        Write-Host "   Version: v$version`n" -ForegroundColor White
        break
    } catch {
        if ($attempt -eq $maxAttempts) {
            Write-Host "`n ⚠️  Le serveur ne répond pas après $($maxAttempts * 2) secondes`n" -ForegroundColor Yellow
            Write-Host "   Vérifiez la fenêtre PowerShell pour voir les erreurs de démarrage.`n" -ForegroundColor Yellow
        } else {
            Start-Sleep -Seconds 2
        }
    }
}


