# Script interactif pour choisir où push (Stash, GitHub, ou les deux)
# Usage: .\scripts\utils\push.ps1 [branch]

$ErrorActionPreference = "Continue"

function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warning { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "❌ $args" -ForegroundColor Red }

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "📤 Push Git - Choix du remote"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Vérifier que c'est un dépôt git
if (-not (Test-Path ".git")) {
    Write-Error "Ce répertoire n'est pas un dépôt git"
    exit 1
}

# Afficher les remotes disponibles
Write-Info "Remotes disponibles :"
git remote -v
Write-Host ""

# Vérifier que les remotes existent
$hasOrigin = $false
$hasGithub = $false

try {
    $originUrl = git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasOrigin = $true
        Write-Info "✓ Origin (Stash) : $originUrl"
    }
} catch {
    # Ignore
}

try {
    $githubUrl = git remote get-url github 2>$null
    if ($LASTEXITCODE -eq 0) {
        $hasGithub = $true
        Write-Info "✓ GitHub : $githubUrl"
    }
} catch {
    # Ignore
}

if (-not $hasOrigin -and -not $hasGithub) {
    Write-Error "Aucun remote configuré"
    exit 1
}

Write-Host ""

# Détecter la branche actuelle ou utiliser celle passée en paramètre
if ($args.Count -gt 0) {
    $branch = $args[0]
} else {
    $branch = git rev-parse --abbrev-ref HEAD
}

Write-Info "Branche actuelle : $branch"
Write-Host ""

# Menu de choix
# Si un choix est passé en paramètre (2ème argument), l'utiliser
if ($args.Count -gt 1) {
    $choice = $args[1]
    Write-Info "Choix automatique : $choice"
} else {
    Write-Host "Où voulez-vous push ?"
    if ($hasOrigin -and $hasGithub) {
        Write-Host "  1) Stash uniquement (origin)"
        Write-Host "  2) GitHub uniquement (github)"
        Write-Host "  3) Les deux (origin + github)"
        $choice = Read-Host "Choix (1-3)"
    } elseif ($hasOrigin) {
        Write-Host "  1) Stash (origin)"
        $choice = Read-Host "Choix (1)"
        $choice = "1"
    } elseif ($hasGithub) {
        Write-Host "  1) GitHub (github)"
        $choice = Read-Host "Choix (1)"
        $choice = "2"
    }
}

Write-Host ""

# Fonction pour push sur un remote
function Push-ToRemote {
    param($remote, $branch)
    
    Write-Info "Push sur $remote ($branch)..."
    git push $remote $branch
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Push réussi sur $remote"
        return $true
    } else {
        Write-Error "Échec du push sur $remote"
        return $false
    }
}

# Exécuter le push selon le choix
$pushSuccess = $true

switch ($choice) {
    "1" {
        if ($hasOrigin) {
            if (-not (Push-ToRemote "origin" $branch)) {
                $pushSuccess = $false
            }
        } else {
            Write-Error "Remote origin non configuré"
            exit 1
        }
    }
    "2" {
        if ($hasGithub) {
            if (-not (Push-ToRemote "github" $branch)) {
                $pushSuccess = $false
            }
        } else {
            Write-Error "Remote github non configuré"
            Write-Host ""
            Write-Info "Pour ajouter GitHub :"
            Write-Host "   git remote add github https://github.com/thomaslorineau/Customer_feedbacks_tracker.git"
            exit 1
        }
    }
    "3" {
        if ($hasOrigin -and $hasGithub) {
            if (-not (Push-ToRemote "origin" $branch)) {
                $pushSuccess = $false
            }
            Write-Host ""
            if (-not (Push-ToRemote "github" $branch)) {
                $pushSuccess = $false
            }
        } else {
            Write-Error "Les deux remotes ne sont pas configurés"
            exit 1
        }
    }
    default {
        Write-Error "Choix invalide"
        exit 1
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ($pushSuccess) {
    Write-Success "Push terminé !"
} else {
    Write-Error "Certains pushs ont échoué"
    exit 1
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

