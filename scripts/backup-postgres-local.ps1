# ============================================
# Script de backup PostgreSQL local
# Crée un backup complet de la base de données
# ============================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backup PostgreSQL - OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$pgBin = "C:\Users\tlorinea\scoop\apps\postgresql\current\bin"
$pgDump = Join-Path $pgBin "pg_dump.exe"
# Utiliser postgres pour le backup (permissions complètes)
$dbUser = "postgres"
$dbPassword = "ocft_secure_password_2026"
$dbName = "ocft_tracker"
$dbHost = "localhost"
$dbPort = "5432"

# Vérifier que pg_dump existe
if (-not (Test-Path $pgDump)) {
    Write-Host "❌ pg_dump non trouvé dans: $pgBin" -ForegroundColor Red
    Write-Host "   Vérifiez que PostgreSQL est installé via Scoop" -ForegroundColor Yellow
    exit 1
}

# Créer le dossier de backup si nécessaire
$backupDir = Join-Path $ProjectRoot "backend\archives\backups"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Host "✅ Dossier de backup créé: $backupDir" -ForegroundColor Green
}

# Générer le nom du fichier avec timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $backupDir "postgres_backup_$timestamp.sql"

Write-Host "[1/3] Vérification de la connexion PostgreSQL..." -ForegroundColor Yellow
$env:PGPASSWORD = $dbPassword

# Test de connexion
$testConnection = & "C:\Users\tlorinea\scoop\apps\postgresql\current\bin\psql.exe" -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "SELECT 1;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur de connexion à PostgreSQL" -ForegroundColor Red
    Write-Host $testConnection -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Connexion PostgreSQL OK" -ForegroundColor Green
Write-Host ""

Write-Host "[2/3] Création du backup..." -ForegroundColor Yellow
Write-Host "   Fichier: $backupFile" -ForegroundColor Gray

# Créer le backup
$backupResult = & $pgDump -U $dbUser -d $dbName -h $dbHost -p $dbPort -F p -f $backupFile 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors de la création du backup" -ForegroundColor Red
    Write-Host $backupResult -ForegroundColor Red
    exit 1
}

Write-Host "   ✅ Backup créé" -ForegroundColor Green
Write-Host ""

Write-Host "[3/3] Vérification du backup..." -ForegroundColor Yellow

if (Test-Path $backupFile) {
    $fileSize = (Get-Item $backupFile).Length / 1MB
    $fileSizeFormatted = "{0:N2}" -f $fileSize
    
    # Vérifier que le fichier n'est pas vide
    if ($fileSize -lt 0.01) {
        Write-Host "⚠️  Le fichier de backup est très petit ($fileSizeFormatted MB)" -ForegroundColor Yellow
        Write-Host "   Vérifiez que la base de données contient des données" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ Backup valide" -ForegroundColor Green
        Write-Host "   Taille: $fileSizeFormatted MB" -ForegroundColor Gray
    }
} else {
    Write-Host "❌ Le fichier de backup n'a pas été créé" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Backup terminé avec succès !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Fichier de backup:" -ForegroundColor Cyan
Write-Host "   $backupFile" -ForegroundColor White
Write-Host ""
Write-Host "Pour restaurer ce backup:" -ForegroundColor Yellow
Write-Host "   psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -f '$backupFile'" -ForegroundColor Gray
Write-Host ""
