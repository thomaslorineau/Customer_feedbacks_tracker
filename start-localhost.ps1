# ============================================
# Script de démarrage localhost automatique
# Vérifie et démarre PostgreSQL + API
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage Localhost - OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 1. Vérifier PostgreSQL (Scoop)
# ============================================
Write-Host "[1/4] Vérification PostgreSQL..." -ForegroundColor Yellow

$pgBin = "C:\Users\tlorinea\scoop\apps\postgresql\current\bin"
$pgCtl = Join-Path $pgBin "pg_ctl.exe"
$psql = Join-Path $pgBin "psql.exe"
$dataDir = "C:\Users\tlorinea\scoop\apps\postgresql\current\data"

if (-not (Test-Path $pgCtl)) {
    Write-Host "❌ PostgreSQL non trouvé dans Scoop" -ForegroundColor Red
    Write-Host "   Installez avec: scoop install postgresql" -ForegroundColor Yellow
    exit 1
}

# Vérifier si PostgreSQL est démarré
$pgStatus = & $pgCtl status -D $dataDir 2>&1
if ($pgStatus -match "server is running") {
    Write-Host "   ✅ PostgreSQL déjà démarré" -ForegroundColor Green
} else {
    Write-Host "   ⏳ Démarrage de PostgreSQL..." -ForegroundColor Yellow
    & $pgCtl start -D $dataDir -l "$dataDir\postgres.log" | Out-Null
    Start-Sleep -Seconds 3
    
    $pgStatus = & $pgCtl status -D $dataDir 2>&1
    if ($pgStatus -match "server is running") {
        Write-Host "   ✅ PostgreSQL démarré" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Erreur au démarrage de PostgreSQL" -ForegroundColor Red
        Write-Host "   Vérifiez les logs: $dataDir\postgres.log" -ForegroundColor Yellow
        exit 1
    }
}

# Vérifier que le port 5432 est accessible
Start-Sleep -Seconds 1
$pgPortTest = Test-NetConnection -ComputerName localhost -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $pgPortTest) {
    Write-Host "   ⚠️  PostgreSQL démarré mais port 5432 non accessible" -ForegroundColor Yellow
    Write-Host "   Attente supplémentaire..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
}

# ============================================
# 2. Vérifier/Créer utilisateur et base de données
# ============================================
Write-Host "[2/4] Vérification base de données..." -ForegroundColor Yellow

$dbUser = "ocft_user"
$dbPassword = "ocft_secure_password_2026"
$dbName = "ocft_tracker"

# Vérifier si l'utilisateur existe
$userExists = & $psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$dbUser'" 2>&1
if ($userExists -match "1") {
    Write-Host "   ✅ Utilisateur '$dbUser' existe" -ForegroundColor Green
} else {
    Write-Host "   ⏳ Création de l'utilisateur '$dbUser'..." -ForegroundColor Yellow
    & $psql -U postgres -c "CREATE USER $dbUser WITH PASSWORD '$dbPassword';" 2>&1 | Out-Null
    Write-Host "   ✅ Utilisateur créé" -ForegroundColor Green
}

# Vérifier si la base de données existe
$dbExists = & $psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbName'" 2>&1
if ($dbExists -match "1") {
    Write-Host "   ✅ Base de données '$dbName' existe" -ForegroundColor Green
} else {
    Write-Host "   ⏳ Création de la base de données '$dbName'..." -ForegroundColor Yellow
    & $psql -U postgres -c "CREATE DATABASE $dbName OWNER $dbUser;" 2>&1 | Out-Null
    Write-Host "   ✅ Base de données créée" -ForegroundColor Green
}

# Donner les permissions nécessaires
& $psql -U postgres -d $dbName -c "GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "ALTER SCHEMA public OWNER TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "GRANT ALL ON SCHEMA public TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "GRANT CREATE ON SCHEMA public TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $dbUser;" 2>&1 | Out-Null
& $psql -U postgres -d $dbName -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $dbUser;" 2>&1 | Out-Null

# Si la base existe déjà, corriger le propriétaire des tables existantes
Write-Host "   ⏳ Vérification des tables existantes..." -ForegroundColor Yellow
$existingTables = & $psql -U postgres -d $dbName -tAc "SELECT tablename FROM pg_tables WHERE schemaname = 'public';" 2>&1
if ($existingTables -and $existingTables -notmatch "ERROR") {
    $tables = $existingTables -split "`n" | Where-Object { $_.Trim() -ne "" }
    foreach ($table in $tables) {
        $table = $table.Trim()
        if ($table) {
            # Changer le propriétaire
            & $psql -U postgres -d $dbName -c "ALTER TABLE IF EXISTS $table OWNER TO $dbUser;" 2>&1 | Out-Null
            # Donner toutes les permissions
            & $psql -U postgres -d $dbName -c "GRANT ALL PRIVILEGES ON TABLE $table TO $dbUser;" 2>&1 | Out-Null
        }
    }
    Write-Host "   ✅ Propriétaires et permissions des tables corrigés" -ForegroundColor Green
}

# ============================================
# 3. Initialiser le schéma de la base de données
# ============================================
Write-Host "[3/5] Initialisation du schéma..." -ForegroundColor Yellow

$initScript = "$ProjectRoot\backend\scripts\init_postgres.sql"
if (Test-Path $initScript) {
    Write-Host "   ⏳ Exécution du script d'initialisation..." -ForegroundColor Yellow
    # Exécuter le script avec l'utilisateur postgres pour créer les tables
    $initResult = & $psql -U postgres -d $dbName -f $initScript 2>&1
    # Ignorer les erreurs "already exists" et "must be owner" si les tables existent déjà
    $errors = $initResult | Where-Object { $_ -match "ERROR" -and $_ -notmatch "already exists" -and $_ -notmatch "must be owner" }
    if ($errors) {
        Write-Host "   ⚠️  Certaines erreurs (peut être normal si tables existent déjà)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ Schéma initialisé" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠️  Script d'initialisation non trouvé, utilisation de init_db() Python" -ForegroundColor Yellow
}

# ============================================
# 4. Vérifier la connexion
# ============================================
Write-Host "[4/5] Test de connexion..." -ForegroundColor Yellow

$env:DATABASE_URL = "postgresql://${dbUser}:${dbPassword}@localhost:5432/${dbName}"
$env:USE_POSTGRES = "true"

Set-Location "$ProjectRoot\backend"

$connectionTest = python -c "
import os
import sys
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'
try:
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    conn.close()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1

if ($connectionTest -match "OK") {
    Write-Host "   ✅ Connexion PostgreSQL OK" -ForegroundColor Green
} else {
    Write-Host "   ❌ Erreur de connexion: $connectionTest" -ForegroundColor Red
    exit 1
}

# ============================================
# 5. Vérifier si le port 8000 est libre
# ============================================
Write-Host "[5/5] Vérification port 8000..." -ForegroundColor Yellow

$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $process = Get-Process -Id $port8000.OwningProcess -ErrorAction SilentlyContinue
    if ($process -and $process.ProcessName -eq "python") {
        Write-Host "   ⚠️  Le serveur semble déjà démarré (PID: $($process.Id))" -ForegroundColor Yellow
        Write-Host "   Voulez-vous le redémarrer ? (O/N)" -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq "O" -or $response -eq "o") {
            Write-Host "   ⏳ Arrêt du serveur existant..." -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        } else {
            Write-Host "   ℹ️  Utilisation du serveur existant" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "🌐 API:  http://localhost:8000" -ForegroundColor Green
            Write-Host "📚 Docs: http://localhost:8000/api/docs" -ForegroundColor Green
            Write-Host "📊 Dashboard: http://localhost:8000/dashboard" -ForegroundColor Green
            exit 0
        }
    } else {
        Write-Host "   ⚠️  Le port 8000 est utilisé par un autre processus" -ForegroundColor Yellow
        Write-Host "   Arrêtez-le manuellement ou changez le port" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "   ✅ Port 8000 disponible" -ForegroundColor Green
}

# ============================================
# 5. Configuration et démarrage du serveur
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Démarrage de l'API..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$env:ENVIRONMENT = "development"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:LOG_LEVEL = "INFO"

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  DATABASE_URL: postgresql://${dbUser}:****@localhost:5432/${dbName}" -ForegroundColor Gray
Write-Host "  ENVIRONMENT: $env:ENVIRONMENT" -ForegroundColor Gray
Write-Host "  REDIS_URL: $env:REDIS_URL" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 API:  http://localhost:8000" -ForegroundColor Green
Write-Host "📚 Docs: http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📊 Dashboard: http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

# Démarrer l'API
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
