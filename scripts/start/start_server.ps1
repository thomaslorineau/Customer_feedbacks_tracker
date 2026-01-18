# Script de démarrage du serveur OVH Complaints Tracker

# Répertoire du backend (2 niveaux au-dessus du dossier courant du script)
$BackendDir = Resolve-Path "$PSScriptRoot/../../backend"

Set-Location $BackendDir
Write-Host "✅ Répertoire: $(Get-Location)" -ForegroundColor Green

# Vérifier si Python est disponible
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python n'est pas trouvé dans le PATH" -ForegroundColor Red
    Write-Host "   Assurez-vous que Python est installé et dans le PATH" -ForegroundColor Yellow
    exit 1
}

# Vérifier si le serveur tourne déjà
$port = 8000
$existingProcess = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "⚠️  Le port $port est déjà utilisé" -ForegroundColor Yellow
    Write-Host "   Arrêtez le serveur existant ou changez le port" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 Démarrage du serveur sur http://localhost:$port..." -ForegroundColor Cyan
Write-Host "📋 Documentation API: http://localhost:$port/docs" -ForegroundColor Cyan
Write-Host ""

# Démarrer le serveur
python -m uvicorn app.main:app --reload --port $port --host 0.0.0.0
