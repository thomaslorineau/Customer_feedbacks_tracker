# ============================================
# Configuration PostgreSQL installé via Scoop
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Chemin PostgreSQL installé via Scoop
$scoopPgPath = "$env:USERPROFILE\scoop\apps\postgresql\current"
$targetPath = "$env:USERPROFILE\postgresql-portable"

# Vérifier si PostgreSQL est installé via Scoop
if (Test-Path "$scoopPgPath\bin\initdb.exe") {
    Write-Host "✅ PostgreSQL trouvé dans Scoop: $scoopPgPath" -ForegroundColor Green
    
    # Créer un lien ou copier vers l'emplacement attendu
    if (-not (Test-Path $targetPath)) {
        Write-Host "Création du lien..." -ForegroundColor Yellow
        try {
            New-Item -ItemType SymbolicLink -Path $targetPath -Target $scoopPgPath -Force | Out-Null
            Write-Host "✅ Lien créé vers: $targetPath" -ForegroundColor Green
        } catch {
            # Si symbolic link échoue, copier le dossier bin
            Write-Host "Création d'une copie du dossier bin..." -ForegroundColor Yellow
            New-Item -ItemType Directory -Path "$targetPath\bin" -Force | Out-Null
            Copy-Item -Path "$scoopPgPath\bin\*" -Destination "$targetPath\bin" -Recurse -Force
            Write-Host "✅ Copie créée" -ForegroundColor Green
        }
    } else {
        Write-Host "✅ Lien/copie existe déjà" -ForegroundColor Green
    }
} else {
    Write-Host "❌ PostgreSQL non trouvé dans Scoop" -ForegroundColor Red
    Write-Host "Vérifiez: $scoopPgPath" -ForegroundColor Yellow
    exit 1
}

# Utiliser le chemin Scoop pour les commandes
$InitDb = "$scoopPgPath\bin\initdb.exe"
$PgCtl = "$scoopPgPath\bin\pg_ctl.exe"
$Psql = "$scoopPgPath\bin\psql.exe"
$DataDir = "$env:USERPROFILE\postgresql-data"

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
    
    # Configurer postgresql.conf
    $ConfigFile = Join-Path $DataDir "postgresql.conf"
    if (Test-Path $ConfigFile) {
        (Get-Content $ConfigFile -Raw) -replace "#port = 5432", "port = 5432" | Set-Content $ConfigFile -NoNewline
    }
    
    # Configurer pg_hba.conf
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
        if (Test-Path $LogFile) {
            Write-Host "Dernières lignes:" -ForegroundColor Yellow
            Get-Content $LogFile -Tail 5
        }
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

Write-Host "✅ Base de données créée" -ForegroundColor Green

# Initialiser le schéma
Write-Host ""
Write-Host "Initialisation du schéma..." -ForegroundColor Green
$InitScript = Join-Path $ProjectRoot "backend\scripts\init_postgres.sql"
$env:PGPASSWORD = "dev_password_123"

if (Test-Path $InitScript) {
    & $Psql -U vibe_user -h localhost -d vibe_tracker -f $InitScript 2>&1 | Out-Null
    Write-Host "✅ Schéma initialisé" -ForegroundColor Green
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
