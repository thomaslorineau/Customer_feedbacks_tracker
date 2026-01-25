# ============================================
# Guide de Configuration PostgreSQL
# ============================================

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration PostgreSQL pour VibeCoding" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Option 1: Vérifier si PostgreSQL est déjà installé (installation normale)
Write-Host "Vérification des installations existantes..." -ForegroundColor Yellow

$pgPaths = @(
    "C:\Program Files\PostgreSQL\*\bin\psql.exe",
    "C:\Program Files (x86)\PostgreSQL\*\bin\psql.exe",
    "$env:USERPROFILE\postgresql-portable\bin\psql.exe",
    "$env:LOCALAPPDATA\Programs\PostgreSQL\*\bin\psql.exe"
)

$foundPg = $null
foreach ($path in $pgPaths) {
    $matches = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
    if ($matches) {
        $foundPg = $matches[0].FullName
        Write-Host "✅ PostgreSQL trouvé: $foundPg" -ForegroundColor Green
        break
    }
}

if ($foundPg) {
    $pgDir = Split-Path (Split-Path $foundPg)
    Write-Host ""
    Write-Host "PostgreSQL est déjà installé!" -ForegroundColor Green
    Write-Host "Chemin: $pgDir" -ForegroundColor Gray
    Write-Host ""
    
    # Tester la connexion
    Write-Host "Test de connexion..." -ForegroundColor Yellow
    $testConn = & $foundPg -U postgres -h localhost -c "SELECT version();" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL fonctionne!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ PostgreSQL installé mais non démarré" -ForegroundColor Yellow
        Write-Host "Démarrez le service PostgreSQL ou utilisez un service cloud" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ PostgreSQL non trouvé" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Options d'Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option 1: Service Cloud Gratuit (RECOMMANDÉ - Plus Simple)" -ForegroundColor Green
Write-Host "  ✅ Pas d'installation locale nécessaire" -ForegroundColor Gray
Write-Host "  ✅ Fonctionne sans droits admin" -ForegroundColor Gray
Write-Host "  ✅ Déjà configuré et sécurisé" -ForegroundColor Gray
Write-Host ""
Write-Host "  Étapes:" -ForegroundColor Yellow
Write-Host "    1. Créez un compte sur https://supabase.com" -ForegroundColor White
Write-Host "    2. Créez un nouveau projet" -ForegroundColor White
Write-Host "    3. Récupérez la connection string depuis Settings > Database" -ForegroundColor White
Write-Host "    4. Configurez:" -ForegroundColor White
Write-Host "       `$env:DATABASE_URL = 'postgresql://...'" -ForegroundColor Cyan
Write-Host "    5. Initialisez:" -ForegroundColor White
Write-Host "       python scripts/init-db-python.py" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option 2: PostgreSQL Portable (Sans Droits Admin)" -ForegroundColor Green
Write-Host "  ⚠️ Nécessite un téléchargement manuel" -ForegroundColor Gray
Write-Host ""
Write-Host "  Étapes:" -ForegroundColor Yellow
Write-Host "    1. Téléchargez depuis:" -ForegroundColor White
Write-Host "       https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor Cyan
Write-Host "    2. Extrayez dans: $env:USERPROFILE\postgresql-portable" -ForegroundColor White
Write-Host "    3. Exécutez:" -ForegroundColor White
Write-Host "       .\scripts\setup-postgres-local.ps1" -ForegroundColor Cyan
Write-Host "       .\scripts\start-postgres-local.ps1" -ForegroundColor Cyan
Write-Host "       .\scripts\init-db-local.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option 3: Installation Normale PostgreSQL" -ForegroundColor Green
Write-Host "  ⚠️ Nécessite des droits admin" -ForegroundColor Gray
Write-Host ""
Write-Host "  Téléchargez depuis: https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Rapide avec Python" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Créer un script de test
$testScript = @"
import os
import sys

# Test si DATABASE_URL est configuré
database_url = os.getenv('DATABASE_URL', '')
if not database_url:
    print('❌ DATABASE_URL non configuré')
    print('')
    print('Configurez avec:')
    print('  `$env:DATABASE_URL = \"postgresql://user:password@host:port/database\"')
    sys.exit(1)

if not database_url.startswith('postgresql://'):
    print('❌ DATABASE_URL doit commencer par postgresql://')
    sys.exit(1)

print(f'✅ DATABASE_URL configuré: {database_url.split("@")[1] if "@" in database_url else "..."}')
print('')

# Test de connexion
try:
    sys.path.insert(0, 'backend')
    os.environ['DATABASE_URL'] = database_url
    os.environ['USE_POSTGRES'] = 'true'
    
    from app.database import get_db_connection, init_db
    
    print('Test de connexion...')
    conn, is_duckdb = get_db_connection()
    
    if is_duckdb:
        print('❌ Utilise encore DuckDB au lieu de PostgreSQL')
        sys.exit(1)
    
    print('✅ Connexion PostgreSQL réussie!')
    
    # Test query
    cursor = conn.cursor()
    cursor.execute('SELECT version()')
    version = cursor.fetchone()[0]
    print(f'   Version: {version.split(",")[0]}')
    
    # Test init
    print('Initialisation du schéma...')
    init_db()
    print('✅ Schéma initialisé')
    
    cursor.close()
    conn.close()
    print('')
    print('✅ Tous les tests réussis!')
    print('')
    print('Vous pouvez maintenant lancer l''API:')
    print('  cd backend')
    print('  uvicorn app.main:app --reload')
    
except ImportError as e:
    print(f'❌ Erreur d''import: {e}')
    print('Installez les dépendances: pip install -r backend/requirements.txt')
    sys.exit(1)
except Exception as e:
    print(f'❌ Erreur: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@

$testScript | Out-File -FilePath "$ProjectRoot\test-postgres-connection.py" -Encoding utf8

Write-Host "Script de test créé: test-postgres-connection.py" -ForegroundColor Green
Write-Host ""
Write-Host "Pour tester votre configuration:" -ForegroundColor Yellow
Write-Host "  `$env:DATABASE_URL = 'postgresql://...'" -ForegroundColor White
Write-Host "  python test-postgres-connection.py" -ForegroundColor White
Write-Host ""
