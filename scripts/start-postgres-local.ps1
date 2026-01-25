# ============================================
# Démarrer PostgreSQL Local
# ============================================

param(
    [string]$PostgresPath = "$env:USERPROFILE\postgresql-portable",
    [string]$DataDir = "$env:USERPROFILE\postgresql-data"
)

$BinPath = Join-Path $PostgresPath "bin"
$PgCtl = Join-Path $BinPath "pg_ctl.exe"
$LogFile = Join-Path $DataDir "postgres.log"

if (-not (Test-Path $PgCtl)) {
    Write-Host "ERREUR: PostgreSQL non trouvé dans $PostgresPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Exécutez d'abord:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup-postgres-local.ps1" -ForegroundColor White
    exit 1
}

# Vérifier si déjà démarré
$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -match "server is running") {
    Write-Host "✅ PostgreSQL est déjà démarré" -ForegroundColor Green
    exit 0
}

Write-Host "Démarrage de PostgreSQL..." -ForegroundColor Green
& $PgCtl -D $DataDir -l $LogFile start

Start-Sleep -Seconds 2

$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -match "server is running") {
    Write-Host "✅ PostgreSQL démarré sur le port 5432" -ForegroundColor Green
    Write-Host "Logs: $LogFile" -ForegroundColor Gray
} else {
    Write-Host "❌ Erreur au démarrage" -ForegroundColor Red
    Write-Host "Vérifiez les logs: $LogFile" -ForegroundColor Yellow
    exit 1
}
