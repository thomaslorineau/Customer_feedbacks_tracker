# Script de test pour démarrer le serveur
cd $PSScriptRoot
Write-Host "Démarrage du serveur sur le port 8000..." -ForegroundColor Cyan
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload





