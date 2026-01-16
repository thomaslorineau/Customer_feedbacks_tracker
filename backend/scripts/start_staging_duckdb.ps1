# Script de démarrage du serveur staging avec DuckDB
# Usage: .\scripts\start_staging_duckdb.ps1

$env:ENVIRONMENT = "staging"
$env:USE_DUCKDB = "true"
$env:APP_PORT = "8001"

Write-Host "🚀 Démarrage du serveur staging avec DuckDB..." -ForegroundColor Cyan
Write-Host "   Environnement: staging" -ForegroundColor White
Write-Host "   Base de données: DuckDB" -ForegroundColor White
Write-Host "   Port: 8001" -ForegroundColor White
Write-Host "   URL: http://127.0.0.1:8001" -ForegroundColor White
Write-Host ""

Set-Location $PSScriptRoot\..
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

