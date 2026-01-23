# Script de démarrage du serveur
Write-Host "🚀 Démarrage du serveur sur http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "📋 Documentation: http://127.0.0.1:8000/api/docs" -ForegroundColor Cyan
Write-Host "📊 Dashboard: http://127.0.0.1:8000/dashboard" -ForegroundColor Cyan
Write-Host ""

# Arrêter les processus Python existants
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Démarrer le serveur
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000










