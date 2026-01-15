# Script de démarrage du serveur OVH Complaints Tracker
Set-Location $PSScriptRoot\backend
Write-Host "✅ Répertoire: $(Get-Location)" -ForegroundColor Green
Write-Host "🚀 Démarrage du serveur sur http://localhost:8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
