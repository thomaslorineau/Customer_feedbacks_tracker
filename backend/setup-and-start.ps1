# ============================================
# Script de configuration et démarrage automatique
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Configuration Automatique OCFT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Python
Write-Host "1️⃣  Vérification Python..." -ForegroundColor Yellow
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "   ❌ Python non trouvé" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ $(py --version)" -ForegroundColor Green

# Vérifier les dépendances
Write-Host ""
Write-Host "2️⃣  Vérification dépendances..." -ForegroundColor Yellow
try {
    py -c "import fastapi; import psycopg2; print('OK')" 2>&1 | Out-Null
    Write-Host "   ✅ Dépendances installées" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Dépendances manquantes" -ForegroundColor Red
    Write-Host "   Installation..." -ForegroundColor Yellow
    py -m pip install -r requirements.txt --quiet
    Write-Host "   ✅ Dépendances installées" -ForegroundColor Green
}

# Vérifier/créer .env
Write-Host ""
Write-Host "3️⃣  Configuration .env..." -ForegroundColor Yellow
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
    Write-Host "   Création du fichier .env..." -ForegroundColor Yellow
    & (Join-Path $ProjectRoot "create-env.ps1")
}

# Charger .env
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split [Environment]::NewLine
$currentDbUrl = ""
foreach ($line in $envLines) {
    if ($line -match '^\s*DATABASE_URL=(.*)$') {
        $currentDbUrl = $matches[1].Trim()
        break
    }
}

# Vérifier si DATABASE_URL est configuré (pas la valeur par défaut)
$needsConfig = $false
if ([string]::IsNullOrEmpty($currentDbUrl) -or 
    ($currentDbUrl -match "localhost:5432" -and $currentDbUrl -match "ocft_secure_password_2026")) {
    $needsConfig = $true
}

if ($needsConfig) {
    Write-Host ""
    Write-Host "⚠️  PostgreSQL doit être configuré" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Option 1: Service cloud gratuit (RECOMMANDÉ - 2 minutes)" -ForegroundColor Cyan
    Write-Host "   ──────────────────────────────────────────────────────" -ForegroundColor Gray
    Write-Host "   1. Ouvrez https://supabase.com dans votre navigateur" -ForegroundColor White
    Write-Host "   2. Créez un compte gratuit (ou connectez-vous)" -ForegroundColor White
    Write-Host "   3. Cliquez sur 'New Project'" -ForegroundColor White
    Write-Host "   4. Remplissez le formulaire (nom, mot de passe)" -ForegroundColor White
    Write-Host "   5. Attendez 2 minutes que le projet soit créé" -ForegroundColor White
    Write-Host "   6. Allez dans Settings > Database" -ForegroundColor White
    Write-Host "   7. Copiez la 'Connection string' (URI)" -ForegroundColor White
    Write-Host "   8. Collez-la ci-dessous" -ForegroundColor White
    Write-Host ""
    Write-Host "   Option 2: Utiliser une base existante" -ForegroundColor Cyan
    Write-Host "   ──────────────────────────────────────" -ForegroundColor Gray
    Write-Host "   Si vous avez déjà PostgreSQL configuré, collez votre DATABASE_URL" -ForegroundColor White
    Write-Host ""
    
    $dbUrl = Read-Host "Collez votre DATABASE_URL PostgreSQL (ou appuyez sur Entrée pour utiliser Supabase)"
    
    if ([string]::IsNullOrEmpty($dbUrl)) {
        Write-Host ""
        Write-Host "   Ouvrez https://supabase.com dans votre navigateur" -ForegroundColor Yellow
        Write-Host "   Une fois que vous avez la connection string, relancez ce script" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Ou modifiez manuellement backend/.env et changez DATABASE_URL" -ForegroundColor Yellow
        exit 0
    }
    
    # Mettre à jour .env
    Write-Host ""
    Write-Host "   Mise à jour de .env..." -ForegroundColor Yellow
    $newEnvContent = $envContent -replace 'DATABASE_URL=.*', "DATABASE_URL=$dbUrl"
    $newEnvContent | Out-File -FilePath $envPath -Encoding utf8 -NoNewline
    Write-Host "   ✅ DATABASE_URL configuré" -ForegroundColor Green
    
    # Recharger
    $currentDbUrl = $dbUrl
}

# Charger toutes les variables d'environnement
Write-Host ""
Write-Host "4️⃣  Chargement de la configuration..." -ForegroundColor Yellow
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split [Environment]::NewLine
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

# Tester la connexion PostgreSQL
Write-Host ""
Write-Host "5️⃣  Test de connexion PostgreSQL..." -ForegroundColor Yellow
$dbUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")

if ([string]::IsNullOrEmpty($dbUrl)) {
    Write-Host "   ❌ DATABASE_URL non défini" -ForegroundColor Red
    Write-Host "   Configurez DATABASE_URL dans backend/.env" -ForegroundColor Yellow
    exit 1
}

# Créer un script Python temporaire pour tester la connexion
$testScriptPath = Join-Path $ProjectRoot "test_db_connection.py"
$testScriptContent = @"
import os
import sys
sys.path.insert(0, r'$ProjectRoot')
os.environ['DATABASE_URL'] = r'$dbUrl'
os.environ['USE_POSTGRES'] = 'true'
try:
    from app.database import get_db_connection
    conn, is_duckdb = get_db_connection()
    print('✅ Connexion réussie!')
    conn.close()
except Exception as e:
    print(f'❌ Erreur: {e}')
    sys.exit(1)
"@
$testScriptContent | Out-File -FilePath $testScriptPath -Encoding utf8

try {
    $result = py $testScriptPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   $result" -ForegroundColor Red
        Write-Host ""
        Write-Host "   ⚠️  La connexion a échoué" -ForegroundColor Yellow
        Write-Host "   Vérifiez que:" -ForegroundColor Yellow
        Write-Host "   - PostgreSQL est accessible" -ForegroundColor White
        Write-Host "   - DATABASE_URL est correct" -ForegroundColor White
        Write-Host "   - La base de données existe" -ForegroundColor White
        Write-Host ""
        Write-Host "   Le serveur démarrera quand même, les tables seront créées au premier démarrage" -ForegroundColor Yellow
    } else {
        Write-Host "   $result" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Impossible de tester la connexion: $_" -ForegroundColor Yellow
} finally {
    if (Test-Path $testScriptPath) {
        Remove-Item $testScriptPath -ErrorAction SilentlyContinue
    }
}

# Initialiser la base de données (créer les tables)
Write-Host ""
Write-Host "6️⃣  Initialisation de la base de données..." -ForegroundColor Yellow

$initScriptPath = Join-Path $ProjectRoot "init_db.py"
$initScriptContent = @"
import os
import sys
sys.path.insert(0, r'$ProjectRoot')
os.environ['DATABASE_URL'] = r'$dbUrl'
os.environ['USE_POSTGRES'] = 'true'
try:
    from app.database import init_db
    init_db()
    print('✅ Base de données initialisée')
except Exception as e:
    print(f'⚠️  Erreur: {e}')
    import traceback
    traceback.print_exc()
"@
$initScriptContent | Out-File -FilePath $initScriptPath -Encoding utf8

try {
    $initResult = py $initScriptPath 2>&1
    Write-Host "   $initResult" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  L'initialisation sera faite au démarrage" -ForegroundColor Yellow
} finally {
    if (Test-Path $initScriptPath) {
        Remove-Item $initScriptPath -ErrorAction SilentlyContinue
    }
}

# Démarrer le serveur
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Démarrage du serveur..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Application:  http://localhost:8000" -ForegroundColor Green
Write-Host "📍 API Docs:     http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "📍 Dashboard:    http://localhost:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot

# Recharger toutes les variables d'environnement
$envContent = Get-Content $envPath -Raw
$envLines = $envContent -split [Environment]::NewLine
foreach ($line in $envLines) {
    if ($line -match '^\s*([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

# Démarrer uvicorn
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
