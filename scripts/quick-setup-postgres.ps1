# ============================================
# Configuration Rapide PostgreSQL
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PostgresPath = "$env:USERPROFILE\postgresql-portable"
$DataDir = "$env:USERPROFILE\postgresql-data"
$BinPath = Join-Path $PostgresPath "bin"
$InitDb = Join-Path $BinPath "initdb.exe"
$PgCtl = Join-Path $BinPath "pg_ctl.exe"
$Psql = Join-Path $BinPath "psql.exe"

# Vérifier si PostgreSQL portable existe
if (-not (Test-Path $InitDb)) {
    Write-Host "❌ PostgreSQL portable non trouvé dans: $PostgresPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "INSTRUCTIONS:" -ForegroundColor Yellow
    Write-Host "  1. Téléchargez PostgreSQL portable depuis:" -ForegroundColor White
    Write-Host "     https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Cherchez le fichier: postgresql-portable-*-win-x64.zip" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Extrayez le contenu dans:" -ForegroundColor White
    Write-Host "     $PostgresPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  4. Relancez ce script:" -ForegroundColor White
    Write-Host "     .\scripts\quick-setup-postgres.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "ALTERNATIVE: Utilisez un service cloud gratuit (Supabase, Neon)" -ForegroundColor Green
    Write-Host "  Plus simple, pas besoin d'installation locale!" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ PostgreSQL portable trouvé" -ForegroundColor Green

# Setup initial si nécessaire
if (-not (Test-Path $DataDir)) {
    Write-Host ""
    Write-Host "Initialisation de la base de données..." -ForegroundColor Green
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    
    & $InitDb -D $DataDir -U postgres -E UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors de l'initialisation" -ForegroundColor Red
        exit 1
    }
    
    # Configurer
    $ConfigFile = Join-Path $DataDir "postgresql.conf"
    if (Test-Path $ConfigFile) {
        (Get-Content $ConfigFile -Raw) -replace "#port = 5432", "port = 5432" | Set-Content $ConfigFile -NoNewline
    }
    
    $PgHbaFile = Join-Path $DataDir "pg_hba.conf"
    if (Test-Path $PgHbaFile) {
        @"
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                  trust
"@ | Set-Content $PgHbaFile
    }
    
    Write-Host "✅ Base initialisée" -ForegroundColor Green
}

# Démarrer PostgreSQL
Write-Host ""
Write-Host "Démarrage de PostgreSQL..." -ForegroundColor Green
$LogFile = Join-Path $DataDir "postgres.log"

$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -match "server is running") {
    Write-Host "✅ PostgreSQL déjà démarré" -ForegroundColor Green
} else {
    & $PgCtl -D $DataDir -l $LogFile start
    Start-Sleep -Seconds 3
    
    if ((& $PgCtl -D $DataDir status 2>&1) -match "server is running") {
        Write-Host "✅ PostgreSQL démarré" -ForegroundColor Green
    } else {
        Write-Host "❌ Erreur au démarrage. Vérifiez: $LogFile" -ForegroundColor Red
        exit 1
    }
}

# Créer DB et utilisateur
Write-Host ""
Write-Host "Configuration de la base..." -ForegroundColor Green
$env:PGPASSWORD = "postgres"

& $Psql -U postgres -h localhost -c "CREATE DATABASE vibe_tracker;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "CREATE USER vibe_user WITH PASSWORD 'dev_password_123';" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "ALTER DATABASE vibe_tracker OWNER TO vibe_user;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE vibe_tracker TO vibe_user;" 2>&1 | Out-Null

# Initialiser le schéma
Write-Host "Initialisation du schéma..." -ForegroundColor Green
$InitScript = Join-Path $ProjectRoot "backend\scripts\init_postgres.sql"
$env:PGPASSWORD = "dev_password_123"

if (Test-Path $InitScript) {
    & $Psql -U vibe_user -h localhost -d vibe_tracker -f $InitScript 2>&1 | Out-Null
}

# Test Python
Write-Host ""
Write-Host "Test de connexion Python..." -ForegroundColor Green
Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

python "$ProjectRoot\test-postgres-connection.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ Configuration Réussie!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Pour lancer l'API:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor White
    Write-Host "  `$env:DATABASE_URL = 'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker'" -ForegroundColor White
    Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
} else {
    Write-Host "❌ Test échoué" -ForegroundColor Red
    exit 1
}
