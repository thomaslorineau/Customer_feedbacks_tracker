# Script de mise à jour de l'application via git (PowerShell)
# Usage: .\update.ps1

$ErrorActionPreference = "Stop"

# Couleurs
function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "🔄 Mise à jour de l'application"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Vérifier si on est sur Windows avec WSL ou Git Bash
if (Get-Command bash -ErrorAction SilentlyContinue) {
    Write-Info "Bash détecté, utilisation du script update.sh..."
    if (Test-Path "update.sh") {
        bash update.sh
        exit $LASTEXITCODE
    } else {
        Write-Error "Script update.sh introuvable"
        exit 1
    }
}

# Vérifier que c'est un dépôt git
if (-not (Test-Path ".git")) {
    Write-Error "Ce répertoire n'est pas un dépôt git"
    Write-Host "   Utilisez install.ps1 pour installer l'application"
    exit 1
}

# Arrêter l'application si elle tourne
Write-Info "Arrêt de l'application..."
if (Test-Path "backend\server.pid") {
    $pid = Get-Content "backend\server.pid"
    if (Get-Process -Id $pid -ErrorAction SilentlyContinue) {
        if (Test-Path "scripts\app\stop.sh") {
            bash scripts/app/stop.sh 2>$null
        } else {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
        Write-Success "Application arrêtée"
    } else {
        Remove-Item "backend\server.pid" -ErrorAction SilentlyContinue
        Write-Info "Application déjà arrêtée"
    }
} else {
    Write-Info "Application non démarrée"
}

# Sauvegarder la configuration
Write-Info "Sauvegarde de la configuration..."
$backupDir = ".update_backup"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

if (Test-Path "backend\.env") {
    Copy-Item "backend\.env" "$backupDir\.env.backup"
    Write-Success "Configuration .env sauvegardée"
}

# Détecter le remote à utiliser
$remoteToUse = "origin"
try {
    $originUrl = git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Remote origin détecté: $originUrl"
        $remoteToUse = "origin"
    } else {
        # Essayer GitHub si origin n'existe pas
        $githubUrl = git remote get-url github 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Warning "Remote origin non trouvé, utilisation de github"
            $remoteToUse = "github"
        } else {
            Write-Error "Aucun remote configuré (origin ou github)"
            exit 1
        }
    }
} catch {
    Write-Error "Erreur lors de la détection du remote"
    exit 1
}

# Mettre à jour le code
Write-Info "Mise à jour du code depuis $remoteToUse..."
try {
    git pull $remoteToUse master
    Write-Success "Code mis à jour"
} catch {
    Write-Error "Échec de la mise à jour git"
    Write-Host "   Vérifiez votre connexion Internet et les permissions git"
    exit 1
}

# Restaurer la configuration
Write-Info "Restauration de la configuration..."
if (Test-Path "$backupDir\.env.backup") {
    Copy-Item "$backupDir\.env.backup" "backend\.env"
    Write-Success "Configuration .env restaurée"
}

Remove-Item -Recurse -Force $backupDir

# Mettre à jour les dépendances
Write-Info "Vérification des dépendances..."
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Info "Mise à jour des dépendances Python..."
    Set-Location backend
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt --upgrade
    Set-Location ..
    
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
        }
    }
    
    Write-Success "Dépendances mises à jour"
} else {
    Write-Warning "Environnement virtuel introuvable"
    Write-Host "   Exécutez install.ps1 pour créer l'environnement"
}

# Redémarrer l'application
Write-Info "Redémarrage de l'application..."
if (Test-Path "scripts\app\start.sh") {
    bash scripts/app/start.sh
} else {
    Write-Warning "Script scripts/app/start.sh introuvable"
    Write-Host "   Démarrez manuellement avec: bash scripts/app/start.sh"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Success "Mise à jour terminée !"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

