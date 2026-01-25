# ============================================
# Arrêter PostgreSQL Local
# ============================================

param(
    [string]$PostgresPath = "$env:USERPROFILE\postgresql-portable",
    [string]$DataDir = "$env:USERPROFILE\postgresql-data"
)

$BinPath = Join-Path $PostgresPath "bin"
$PgCtl = Join-Path $BinPath "pg_ctl.exe"

if (-not (Test-Path $PgCtl)) {
    Write-Host "ERREUR: PostgreSQL non trouvé" -ForegroundColor Red
    exit 1
}

Write-Host "Arrêt de PostgreSQL..." -ForegroundColor Yellow
& $PgCtl -D $DataDir stop

Start-Sleep -Seconds 1
Write-Host "✅ PostgreSQL arrêté" -ForegroundColor Green
