# ============================================
# Installation PostgreSQL via Scoop
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL via Scoop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Scoop est installé
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    Write-Host "Installation de Scoop (gestionnaire de paquets Windows)..." -ForegroundColor Yellow
    Write-Host "Scoop fonctionne sans droits admin!" -ForegroundColor Green
    
    try {
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Invoke-RestMethod -Uri get.scoop.sh | Invoke-Expression
        
        if (Get-Command scoop -ErrorAction SilentlyContinue) {
            Write-Host "✅ Scoop installé!" -ForegroundColor Green
        } else {
            throw "Scoop non installé après exécution"
        }
    } catch {
        Write-Host "❌ Erreur lors de l'installation de Scoop: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Installation manuelle de Scoop:" -ForegroundColor Yellow
        Write-Host "  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
        Write-Host "  Invoke-RestMethod get.scoop.sh | Invoke-Expression" -ForegroundColor White
        exit 1
    }
}

# Ajouter le bucket extras (contient PostgreSQL)
Write-Host ""
Write-Host "Configuration de Scoop..." -ForegroundColor Yellow
scoop bucket add extras 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bucket extras déjà ajouté ou erreur (peut être ignoré)" -ForegroundColor Gray
}

# Installer PostgreSQL portable
Write-Host ""
Write-Host "Installation de PostgreSQL portable..." -ForegroundColor Yellow
Write-Host "Cela peut prendre quelques minutes..." -ForegroundColor Gray

try {
    scoop install postgresql15-portable 2>&1 | Tee-Object -Variable output
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL portable installé!" -ForegroundColor Green
        
        # Trouver le chemin d'installation
        $scoopPath = "$env:USERPROFILE\scoop\apps\postgresql15-portable\current"
        if (Test-Path $scoopPath) {
            Write-Host "Chemin: $scoopPath" -ForegroundColor Gray
            
            # Créer un lien symbolique ou copier vers l'emplacement attendu
            $targetPath = "$env:USERPROFILE\postgresql-portable"
            if (-not (Test-Path $targetPath)) {
                Write-Host "Création du lien vers l'emplacement attendu..." -ForegroundColor Gray
                New-Item -ItemType SymbolicLink -Path $targetPath -Target $scoopPath -Force | Out-Null
            }
        }
    } else {
        # Essayer avec un autre nom
        Write-Host "Essai avec un autre nom de paquet..." -ForegroundColor Gray
        scoop install postgresql-portable 2>&1 | Out-Null
    }
} catch {
    Write-Host "❌ Erreur lors de l'installation: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Essayons une autre méthode..." -ForegroundColor Yellow
}

# Vérifier l'installation
$possiblePaths = @(
    "$env:USERPROFILE\scoop\apps\postgresql15-portable\current",
    "$env:USERPROFILE\scoop\apps\postgresql-portable\current",
    "$env:USERPROFILE\postgresql-portable"
)

$pgPath = $null
foreach ($path in $possiblePaths) {
    if (Test-Path (Join-Path $path "bin\initdb.exe")) {
        $pgPath = $path
        Write-Host "✅ PostgreSQL trouvé dans: $pgPath" -ForegroundColor Green
        break
    }
}

if (-not $pgPath) {
    Write-Host "❌ PostgreSQL non trouvé après installation" -ForegroundColor Red
    Write-Host ""
    Write-Host "Vérifiez l'installation avec: scoop list" -ForegroundColor Yellow
    exit 1
}

# Créer le lien si nécessaire
$targetPath = "$env:USERPROFILE\postgresql-portable"
if (-not (Test-Path $targetPath)) {
    try {
        New-Item -ItemType SymbolicLink -Path $targetPath -Target $pgPath -Force | Out-Null
        Write-Host "✅ Lien créé vers: $targetPath" -ForegroundColor Green
    } catch {
        # Si symbolic link échoue, copier les fichiers essentiels
        Write-Host "Création d'une copie..." -ForegroundColor Gray
        Copy-Item -Path "$pgPath\bin" -Destination "$targetPath\bin" -Recurse -Force
    }
}

Write-Host ""
Write-Host "✅ Installation terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration et test..." -ForegroundColor Cyan
& "$ProjectRoot\scripts\quick-setup-postgres.ps1"
