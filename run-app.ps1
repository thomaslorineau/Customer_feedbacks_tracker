# Script simple pour demarrer l'application
$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Demarrage OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifier PostgreSQL via Scoop
$pgBin = "C:\Users\$env:USERNAME\scoop\apps\postgresql\current\bin"
$pgCtl = Join-Path $pgBin "pg_ctl.exe"
$psql = Join-Path $pgBin "psql.exe"
$pgData = "C:\Users\$env:USERNAME\scoop\apps\postgresql\current\data"

if (-not (Test-Path $pgCtl)) {
    Write-Host "PostgreSQL non trouve. Installation via Scoop..." -ForegroundColor Yellow
    scoop install postgresql
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erreur installation PostgreSQL" -ForegroundColor Red
        exit 1
    }
}

# Initialiser PostgreSQL si necessaire
if (-not (Test-Path (Join-Path $pgData "postgresql.conf"))) {
    Write-Host "Initialisation PostgreSQL..." -ForegroundColor Yellow
    if (-not (Test-Path $pgData)) {
        New-Item -ItemType Directory -Path $pgData -Force | Out-Null
    }
    $initdb = Join-Path $pgBin "initdb.exe"
    & $initdb -D $pgData -U postgres -A trust -E UTF8 --locale=C
}

# Demarrer PostgreSQL
Write-Host "Demarrage PostgreSQL..." -ForegroundColor Yellow
$pgStatus = & $pgCtl status -D $pgData 2>&1
if ($pgStatus -notmatch "server is running") {
    $logFile = Join-Path $pgData "postgres.log"
    & $pgCtl start -D $pgData -l $logFile
    Start-Sleep -Seconds 3
}
Write-Host "PostgreSQL OK" -ForegroundColor Green

# Creer utilisateur et base de donnees
Write-Host "Configuration base de donnees..." -ForegroundColor Yellow
$dbUser = "ocft_user"
$dbPassword = "ocft_secure_password_2026"
$dbName = "ocft_tracker"

& $psql -U postgres -c "CREATE USER $dbUser WITH PASSWORD '$dbPassword';" 2>&1 | Out-Null
& $psql -U postgres -c "CREATE DATABASE $dbName OWNER $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "ALTER SCHEMA public OWNER TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "GRANT ALL ON SCHEMA public TO $dbUser;" 2>&1 | Out-Null
Write-Host "Base de donnees OK" -ForegroundColor Green

# Configurer environnement
$env:DATABASE_URL = "postgresql://${dbUser}:${dbPassword}@localhost:5432/${dbName}"
$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:LOG_LEVEL = "INFO"

# Aller dans le dossier backend
Set-Location "$ProjectRoot\backend"

# Demarrer le serveur
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Demarrage du serveur..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API:       http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs:  http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arreter" -ForegroundColor Yellow
Write-Host ""

py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

