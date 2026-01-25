# ============================================
# Setup PostgreSQL Local (sans Docker)
# ============================================

param(
    [string]$PostgresPath = "$env:USERPROFILE\postgresql-portable",
    [string]$DataDir = "$env:USERPROFILE\postgresql-data",
    [string]$Port = "5432"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup PostgreSQL Local" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Vérifier si PostgreSQL existe
$BinPath = Join-Path $PostgresPath "bin"
$InitDb = Join-Path $BinPath "initdb.exe"
$PgCtl = Join-Path $BinPath "pg_ctl.exe"

if (-not (Test-Path $InitDb)) {
    Write-Host "ERREUR: PostgreSQL non trouvé dans $PostgresPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Téléchargez PostgreSQL portable depuis:" -ForegroundColor Yellow
    Write-Host "  https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor White
    Write-Host ""
    Write-Host "Ou utilisez un service cloud gratuit:" -ForegroundColor Yellow
    Write-Host "  - Supabase: https://supabase.com" -ForegroundColor White
    Write-Host "  - Neon: https://neon.tech" -ForegroundColor White
    Write-Host "  - ElephantSQL: https://www.elephantsql.com" -ForegroundColor White
    exit 1
}

# Créer le dossier data s'il n'existe pas
if (-not (Test-Path $DataDir)) {
    Write-Host "Initialisation de la base de données..." -ForegroundColor Green
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    
    # Initialiser la base
    & $InitDb -D $DataDir -U postgres -E UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERREUR lors de l'initialisation" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Base de données initialisée" -ForegroundColor Green
}

# Configurer PostgreSQL
$ConfigFile = Join-Path $DataDir "postgresql.conf"
$PgHbaFile = Join-Path $DataDir "pg_hba.conf"

# Modifier le port dans postgresql.conf
if (Test-Path $ConfigFile) {
    $content = Get-Content $ConfigFile -Raw
    $content = $content -replace "#port = 5432", "port = $Port"
    $content = $content -replace "port = 5432", "port = $Port"
    Set-Content $ConfigFile $content
}

# Configurer pg_hba.conf pour accepter les connexions locales
if (Test-Path $PgHbaFile) {
    $hbaContent = @"
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                  trust
"@
    Set-Content $PgHbaFile $hbaContent
}

Write-Host "Configuration terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "Pour démarrer PostgreSQL:" -ForegroundColor Yellow
Write-Host "  .\scripts\start-postgres-local.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Pour arrêter PostgreSQL:" -ForegroundColor Yellow
Write-Host "  .\scripts\stop-postgres-local.ps1" -ForegroundColor White
