# Script de sauvegarde automatique des bases de données (Windows PowerShell)
# Usage: .\scripts\backup_db.ps1 [production|staging|both]
# Pour Task Scheduler: créez une tâche planifiée qui exécute ce script quotidiennement

param(
    [Parameter(Position=0)]
    [ValidateSet("production", "staging", "both")]
    [string]$Environment = "both"
)

$ErrorActionPreference = "Stop"

# Obtenir le répertoire du script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $AppDir "backend"

# Couleurs
function Write-Info {
    Write-Host "ℹ️  $args" -ForegroundColor Cyan
}

function Write-Success {
    Write-Host "✅ $args" -ForegroundColor Green
}

function Write-Warning {
    Write-Host "⚠️  $args" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "❌ $args" -ForegroundColor Red
}

# Aller dans le répertoire backend
Set-Location $BackendDir

# Activer l'environnement virtuel si disponible
if (Test-Path "..\.venv\Scripts\Activate.ps1") {
    & "..\.venv\Scripts\Activate.ps1"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
}

# Exécuter le script Python de sauvegarde
Write-Info "Démarrage de la sauvegarde automatique..."
try {
    $output = python scripts/backup_db.py $Environment --keep=30 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Success "Sauvegarde terminée avec succès"
        exit 0
    } else {
        Write-Error "Erreur lors de la sauvegarde (code: $exitCode)"
        Write-Host $output
        exit $exitCode
    }
} catch {
    Write-Error "Erreur lors de l'exécution du script de sauvegarde: $_"
    exit 1
}

