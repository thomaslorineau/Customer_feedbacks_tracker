# ============================================
# Installation Automatique PostgreSQL Portable
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL Portable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$PostgresPath = "$env:USERPROFILE\postgresql-portable"
$DataDir = "$env:USERPROFILE\postgresql-data"
$BinPath = Join-Path $PostgresPath "bin"

# Vérifier si PostgreSQL portable existe déjà
if (-not (Test-Path $BinPath)) {
    Write-Host ""
    Write-Host "PostgreSQL portable non trouvé. Téléchargement..." -ForegroundColor Yellow
    
    # Créer le dossier de destination
    New-Item -ItemType Directory -Path $PostgresPath -Force | Out-Null
    
    # Essayer plusieurs sources de téléchargement
    $downloadUrls = @(
        "https://github.com/garethflowers/postgresql-portable/releases/download/v15.5.0/postgresql-portable-15.5.0-win-x64.zip",
        "https://github.com/garethflowers/postgresql-portable/releases/latest/download/postgresql-portable-win-x64.zip"
    )
    
    $zipPath = "$env:TEMP\postgresql-portable.zip"
    $downloaded = $false
    
    foreach ($url in $downloadUrls) {
        try {
            Write-Host "Tentative de téléchargement depuis: $url" -ForegroundColor Gray
            Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing -TimeoutSec 30
            $downloaded = $true
            break
        } catch {
            Write-Host "Échec: $_" -ForegroundColor Gray
            continue
        }
    }
    
    if (-not $downloaded) {
        Write-Host ""
        Write-Host "❌ Impossible de télécharger automatiquement PostgreSQL portable" -ForegroundColor Red
        Write-Host ""
        Write-Host "Veuillez télécharger manuellement:" -ForegroundColor Yellow
        Write-Host "  1. Allez sur: https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor White
        Write-Host "  2. Téléchargez la dernière version (postgresql-portable-*-win-x64.zip)" -ForegroundColor White
        Write-Host "  3. Extrayez dans: $PostgresPath" -ForegroundColor White
        Write-Host ""
        Write-Host "Ou utilisez un service cloud gratuit:" -ForegroundColor Cyan
        Write-Host "  - Supabase: https://supabase.com" -ForegroundColor White
        Write-Host "  - Neon: https://neon.tech" -ForegroundColor White
        exit 1
    }
    
    Write-Host "Extraction..." -ForegroundColor Yellow
    try {
        Expand-Archive -Path $zipPath -DestinationPath $PostgresPath -Force
        Remove-Item $zipPath -Force
        Write-Host "✅ PostgreSQL portable installé!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur lors de l'extraction: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ PostgreSQL portable déjà installé" -ForegroundColor Green
}

# Vérifier que les binaires existent
$InitDb = Join-Path $BinPath "initdb.exe"
$PgCtl = Join-Path $BinPath "pg_ctl.exe"
$Psql = Join-Path $BinPath "psql.exe"

if (-not (Test-Path $InitDb)) {
    Write-Host "❌ initdb.exe non trouvé dans $BinPath" -ForegroundColor Red
    Write-Host "Structure attendue: $BinPath\initdb.exe" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Vérifiez que l'archive a été correctement extraite" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Binaires PostgreSQL trouvés" -ForegroundColor Green

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
        $content = Get-Content $ConfigFile -Raw
        $content = $content -replace "#port = 5432", "port = 5432"
        $content = $content -replace "port = 5432", "port = 5432"
        Set-Content $ConfigFile $content -NoNewline
    }
    
    # Configurer pg_hba.conf
    $PgHbaFile = Join-Path $DataDir "pg_hba.conf"
    if (Test-Path $PgHbaFile) {
        $hbaContent = @"
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                  trust
"@
        Set-Content $PgHbaFile $hbaContent
    }
    
    Write-Host "✅ Base de données initialisée" -ForegroundColor Green
}

# Démarrer PostgreSQL
Write-Host ""
Write-Host "Démarrage de PostgreSQL..." -ForegroundColor Green
$LogFile = Join-Path $DataDir "postgres.log"

$Status = & $PgCtl -D $DataDir status 2>&1
if ($Status -match "server is running") {
    Write-Host "✅ PostgreSQL est déjà démarré" -ForegroundColor Green
} else {
    & $PgCtl -D $DataDir -l $LogFile start
    Start-Sleep -Seconds 3
    
    $Status = & $PgCtl -D $DataDir status 2>&1
    if ($Status -match "server is running") {
        Write-Host "✅ PostgreSQL démarré" -ForegroundColor Green
    } else {
        Write-Host "❌ Erreur au démarrage" -ForegroundColor Red
        if (Test-Path $LogFile) {
            Write-Host "Dernières lignes du log:" -ForegroundColor Yellow
            Get-Content $LogFile -Tail 10
        }
        exit 1
    }
}

# Créer la base de données et l'utilisateur
Write-Host ""
Write-Host "Configuration de la base de données..." -ForegroundColor Green
$env:PGPASSWORD = "postgres"

& $Psql -U postgres -h localhost -c "CREATE DATABASE vibe_tracker;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "CREATE USER vibe_user WITH PASSWORD 'dev_password_123';" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "ALTER DATABASE vibe_tracker OWNER TO vibe_user;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE vibe_tracker TO vibe_user;" 2>&1 | Out-Null

Write-Host "✅ Base de données et utilisateur créés" -ForegroundColor Green

# Initialiser le schéma
Write-Host ""
Write-Host "Initialisation du schéma..." -ForegroundColor Green
$InitScript = Join-Path $ProjectRoot "backend\scripts\init_postgres.sql"
$env:PGPASSWORD = "dev_password_123"

if (Test-Path $InitScript) {
    & $Psql -U vibe_user -h localhost -d vibe_tracker -f $InitScript 2>&1 | Out-Null
    Write-Host "✅ Schéma initialisé" -ForegroundColor Green
} else {
    Write-Host "⚠️ Script d'initialisation non trouvé: $InitScript" -ForegroundColor Yellow
}

# Test de connexion avec Python
Write-Host ""
Write-Host "Test de connexion avec Python..." -ForegroundColor Green
Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

$testScript = @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    print('✅ Connexion PostgreSQL réussie!')
    print(f'   Type: PostgreSQL (is_duckdb={is_duckdb})')
    
    # Test simple query
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()[0]
    print(f'   Version: {version.split(",")[0]}')
    
    # Test init_db
    from app.database import init_db
    init_db()
    print('✅ Schéma initialisé')
    
    cursor.close()
    conn.close()
    print('✅ Tous les tests réussis!')
except Exception as e:
    print(f'❌ Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

$testScript | Out-File -FilePath "$env:TEMP\test_postgres.py" -Encoding utf8

try {
    python "$env:TEMP\test_postgres.py"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✅ Installation et Test Réussis!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "PostgreSQL est prêt à être utilisé!" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Pour lancer l'API:" -ForegroundColor Yellow
        Write-Host "  cd backend" -ForegroundColor White
        Write-Host "  `$env:DATABASE_URL = 'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker'" -ForegroundColor White
        Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
        Write-Host ""
        Write-Host "Pour arrêter PostgreSQL:" -ForegroundColor Yellow
        Write-Host "  .\scripts\stop-postgres-local.ps1" -ForegroundColor White
    } else {
        Write-Host "❌ Test échoué" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Erreur lors du test: $_" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item "$env:TEMP\test_postgres.py" -ErrorAction SilentlyContinue
}
