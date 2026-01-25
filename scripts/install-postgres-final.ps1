# ============================================
# Installation PostgreSQL Portable via Scoop
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL Portable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Chemin Scoop
$scoopPath = "$env:USERPROFILE\scoop\shims"
$scoopExe = "$env:USERPROFILE\scoop\shims\scoop.exe"

# Ajouter Scoop au PATH pour cette session
if (Test-Path $scoopPath) {
    $env:PATH = "$scoopPath;$env:PATH"
    Write-Host "✅ Scoop trouvé" -ForegroundColor Green
} else {
    Write-Host "Installation de Scoop..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod get.scoop.sh | Invoke-Expression
        $env:PATH = "$env:USERPROFILE\scoop\shims;$env:PATH"
        Write-Host "✅ Scoop installé" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur installation Scoop: $_" -ForegroundColor Red
        exit 1
    }
}

# Ajouter le bucket extras
Write-Host ""
Write-Host "Configuration de Scoop..." -ForegroundColor Yellow
& $scoopExe bucket add extras 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bucket extras déjà ajouté (normal)" -ForegroundColor Gray
}

# Installer PostgreSQL portable
Write-Host ""
Write-Host "Installation de PostgreSQL portable..." -ForegroundColor Yellow
Write-Host "Cela peut prendre quelques minutes..." -ForegroundColor Gray

try {
    & $scoopExe install postgresql15-portable
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL portable installé!" -ForegroundColor Green
        
        # Trouver le chemin d'installation
        $pgInstallPath = "$env:USERPROFILE\scoop\apps\postgresql15-portable\current"
        if (Test-Path $pgInstallPath) {
            Write-Host "Chemin: $pgInstallPath" -ForegroundColor Gray
            
            # Créer un lien ou copier vers l'emplacement attendu
            $targetPath = "$env:USERPROFILE\postgresql-portable"
            if (-not (Test-Path $targetPath)) {
                Write-Host "Création du lien..." -ForegroundColor Gray
                try {
                    New-Item -ItemType SymbolicLink -Path $targetPath -Target $pgInstallPath -Force | Out-Null
                } catch {
                    # Si symbolic link échoue, créer un dossier et copier bin
                    Write-Host "Création d'une copie du dossier bin..." -ForegroundColor Gray
                    New-Item -ItemType Directory -Path "$targetPath\bin" -Force | Out-Null
                    Copy-Item -Path "$pgInstallPath\bin\*" -Destination "$targetPath\bin" -Recurse -Force
                }
            }
        }
    } else {
        Write-Host "❌ Erreur lors de l'installation" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Erreur: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Installation terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration et test..." -ForegroundColor Cyan
& "$ProjectRoot\scripts\quick-setup-postgres.ps1"
