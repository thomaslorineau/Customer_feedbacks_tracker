# ============================================
# Installation automatique PostgreSQL via Scoop
# ============================================

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL via Scoop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Scoop est installé
Write-Host "[1/4] Vérification Scoop..." -ForegroundColor Yellow
$scoopInstalled = Get-Command scoop -ErrorAction SilentlyContinue

if (-not $scoopInstalled) {
    Write-Host "   Scoop n'est pas installe, installation..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Execution en tant qu'administrateur requise..." -ForegroundColor Yellow
    
    # Vérifier si on est admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "   Ce script doit etre execute en tant qu'administrateur" -ForegroundColor Red
        Write-Host ""
        Write-Host "   Instructions manuelles:" -ForegroundColor Yellow
        Write-Host "   1. Ouvrez PowerShell en tant qu'administrateur" -ForegroundColor White
        Write-Host "   2. Executez: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
        Write-Host "   3. Executez: irm get.scoop.sh | iex" -ForegroundColor White
        Write-Host "   4. Relancez ce script" -ForegroundColor White
        exit 1
    }
    
    # Installer Scoop
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    irm get.scoop.sh | iex
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   Scoop installe" -ForegroundColor Green
    } else {
        Write-Host "   Erreur lors de l'installation de Scoop" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   Scoop est deja installe" -ForegroundColor Green
}

# Installer PostgreSQL
Write-Host ""
Write-Host "[2/4] Installation PostgreSQL..." -ForegroundColor Yellow
Write-Host "   Cela peut prendre quelques minutes..." -ForegroundColor Yellow

scoop install postgresql

if ($LASTEXITCODE -eq 0) {
    Write-Host "   PostgreSQL installe" -ForegroundColor Green
} else {
    Write-Host "   Erreur lors de l'installation de PostgreSQL" -ForegroundColor Red
    exit 1
}

# Initialiser PostgreSQL
Write-Host ""
Write-Host "[3/4] Initialisation de PostgreSQL..." -ForegroundColor Yellow

$pgBin = "C:\Users\$env:USERNAME\scoop\apps\postgresql\current\bin"
$pgData = "C:\Users\$env:USERNAME\scoop\apps\postgresql\current\data"
$initdb = Join-Path $pgBin "initdb.exe"

if (-not (Test-Path $initdb)) {
    Write-Host "   initdb.exe non trouve dans $pgBin" -ForegroundColor Red
    Write-Host "   Verifiez l'installation de PostgreSQL" -ForegroundColor Yellow
    exit 1
}

# Créer le répertoire de données s'il n'existe pas
if (-not (Test-Path $pgData)) {
    New-Item -ItemType Directory -Path $pgData -Force | Out-Null
}

# Vérifier si déjà initialisé
if (Test-Path (Join-Path $pgData "postgresql.conf")) {
    Write-Host "   PostgreSQL deja initialise" -ForegroundColor Cyan
} else {
    Write-Host "   Initialisation de la base de donnees..." -ForegroundColor Yellow
    Write-Host "   (Vous devrez definir un mot de passe pour l'utilisateur postgres)" -ForegroundColor Yellow
    
    & $initdb -D $pgData -U postgres -A password -E UTF8 --locale=C
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   PostgreSQL initialise" -ForegroundColor Green
    } else {
        Write-Host "   Erreur lors de l'initialisation" -ForegroundColor Red
        exit 1
    }
}

# Démarrer PostgreSQL
Write-Host ""
Write-Host "[4/4] Démarrage de PostgreSQL..." -ForegroundColor Yellow

$pgCtl = Join-Path $pgBin "pg_ctl.exe"

# Vérifier si déjà démarré
$pgStatus = & $pgCtl status -D $pgData 2>&1
if ($pgStatus -match "server is running") {
    Write-Host "   PostgreSQL deja demarre" -ForegroundColor Green
} else {
    Write-Host "   Demarrage de PostgreSQL..." -ForegroundColor Yellow
    $logFile = Join-Path $pgData "postgres.log"
    & $pgCtl start -D $pgData -l $logFile 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    
    $pgStatus = & $pgCtl status -D $pgData 2>&1
    if ($pgStatus -match "server is running") {
        Write-Host "   PostgreSQL demarre" -ForegroundColor Green
    } else {
        Write-Host "   PostgreSQL demarre mais verifiez les logs: $logFile" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation terminee!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Vous pouvez maintenant utiliser:" -ForegroundColor Green
Write-Host "  .\start-localhost.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: Le script vous demandera le mot de passe PostgreSQL" -ForegroundColor Cyan
Write-Host "      (utilisateur postgres) lors du premier demarrage" -ForegroundColor Cyan
Write-Host ""
