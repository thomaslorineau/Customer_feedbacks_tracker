# Script d'installation automatique pour OVH Customer Feedback Tracker (PowerShell)
# Usage: .\install.ps1

$ErrorActionPreference = "Stop"

# Couleurs
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $1" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "🚀 Installation de OVH Customer Feedback Tracker"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Vérifier si on est sur Windows avec WSL ou Git Bash
if (Get-Command bash -ErrorAction SilentlyContinue) {
    Write-Info "Bash détecté, utilisation du script install.sh..."
    if (Test-Path "install.sh") {
        bash install.sh
        exit $LASTEXITCODE
    } else {
        Write-Error "Script install.sh introuvable"
        exit 1
    }
}

# Sinon, installation PowerShell native (Windows)
Write-Info "Installation en mode PowerShell (Windows)"

# Vérifier Python
Write-Info "Vérification des prérequis..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python n'est pas installé."
    Write-Host "   Veuillez installer Python 3.11 ou 3.12 depuis python.org"
    exit 1
}

$pythonVersion = python --version 2>&1
Write-Success "Python $pythonVersion trouvé"

# Vérifier Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git n'est pas installé."
    Write-Host "   Veuillez installer Git depuis git-scm.com"
    exit 1
}

$gitVersion = (git --version).Split(' ')[2]
Write-Success "Git $gitVersion trouvé"

# Déterminer le répertoire d'installation
$installDir = $PWD.Path
if (-not (Test-Path "backend\requirements.txt")) {
    $installDir = Join-Path $env:USERPROFILE "apps\complaints_tracker"
    Write-Info "Installation dans: $installDir"
    
    if (Test-Path $installDir) {
        $response = Read-Host "Le répertoire $installDir existe déjà. Voulez-vous continuer ? (o/N)"
        if ($response -notmatch "^[Oo]$") {
            Write-Info "Installation annulée."
            exit 0
        }
    }
} else {
    Write-Info "Installation dans le répertoire actuel: $installDir"
}

# Cloner le dépôt si nécessaire
if (-not (Test-Path "backend\requirements.txt")) {
    Write-Info "Téléchargement de l'application..."
    
    # Détecter quelle source utiliser (Stash par défaut, mais peut être GitHub)
    $gitSource = $env:GIT_SOURCE
    if (-not $gitSource) {
        $gitSource = "stash"
    }
    
    if (Test-Path $installDir) {
        Remove-Item -Recurse -Force $installDir
    }
    
    if ($gitSource -eq "github") {
        Write-Info "Clonage depuis GitHub..."
        git clone https://github.com/thomaslorineau/Customer_feedbacks_tracker.git $installDir
    } else {
        Write-Info "Clonage depuis Stash..."
        git clone ssh://git@stash.ovh.net:7999/~thomas.lorineau/customer_feedbacks_tracker.git $installDir
    }
    Set-Location $installDir
    Write-Success "Application téléchargée"
} else {
    Set-Location $installDir
    Write-Info "Utilisation du répertoire existant: $installDir"
}

# Créer l'environnement virtuel
Write-Info "Création de l'environnement virtuel Python..."
if (Test-Path "venv") {
    $response = Read-Host "L'environnement virtuel existe déjà. Voulez-vous le recréer ? (o/N)"
    if ($response -match "^[Oo]$") {
        Remove-Item -Recurse -Force venv
        python -m venv venv
        Write-Success "Environnement virtuel recréé"
    } else {
        Write-Info "Utilisation de l'environnement virtuel existant"
    }
} else {
    python -m venv venv
    Write-Success "Environnement virtuel créé"
}

# Installer les dépendances
Write-Info "Installation des dépendances Python..."
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip --quiet
Set-Location backend
python -m pip install -r requirements.txt

# Vérifier DuckDB
Write-Info "Vérification de l'installation de DuckDB..."
try {
    $duckdbVersion = python -c "import duckdb; print(duckdb.__version__)" 2>$null
    Write-Success "DuckDB installé (version $duckdbVersion)"
} catch {
    Write-Warning "DuckDB n'est pas installé, tentative d'installation..."
    python -m pip install duckdb==0.10.0
    try {
        python -c "import duckdb" 2>$null
        Write-Success "DuckDB installé avec succès"
    } catch {
        Write-Error "Échec de l'installation de DuckDB"
        Write-Host "   L'application fonctionnera en mode SQLite (fallback)"
    }
}

Set-Location ..
Write-Success "Dépendances installées"

# Configuration CORS
Write-Info "Configuration CORS..."
if (-not (Test-Path "backend\.env")) {
    $corsOrigins = "http://localhost:8000,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8000"
    Add-Content -Path "backend\.env" -Value "CORS_ORIGINS=$corsOrigins"
    Write-Success "CORS configuré"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Success "Installation terminée avec succès !"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "📋 Pour démarrer l'application :"
Write-Host "   cd $installDir"
Write-Host "   bash scripts/app/start.sh"
Write-Host ""

