# ============================================
# Finalisation Configuration PostgreSQL
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Finalisation Configuration PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Psql = "$env:USERPROFILE\scoop\apps\postgresql\current\bin\psql.exe"

# Créer l'utilisateur
Write-Host "Création de l'utilisateur..." -ForegroundColor Green
$env:PGPASSWORD = "postgres"
try {
    $result = & $Psql -U postgres -h localhost -c "CREATE USER vibe_user WITH PASSWORD 'dev_password_123';" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Utilisateur créé" -ForegroundColor Gray
    }
} catch {
    if ($_ -match "already exists") {
        Write-Host "Utilisateur existe déjà (normal)" -ForegroundColor Gray
    } else {
        Write-Host "Note: $($_.Exception.Message)" -ForegroundColor Gray
    }
}
# Ignorer l'erreur "already exists"
$ErrorActionPreference = "SilentlyContinue"
& $Psql -U postgres -h localhost -c "CREATE USER vibe_user WITH PASSWORD 'dev_password_123';" 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Write-Host "Utilisateur vérifié" -ForegroundColor Gray

# Configurer la base de données
Write-Host "Configuration de la base de données..." -ForegroundColor Green
& $Psql -U postgres -h localhost -c "ALTER DATABASE vibe_tracker OWNER TO vibe_user;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE vibe_tracker TO vibe_user;" 2>&1 | Out-Null

# Initialiser le schéma
Write-Host "Initialisation du schéma..." -ForegroundColor Green
$InitScript = Join-Path $ProjectRoot "backend\scripts\init_postgres.sql"
$env:PGPASSWORD = "dev_password_123"

if (Test-Path $InitScript) {
    $ErrorActionPreference = "SilentlyContinue"
    $output = & $Psql -U vibe_user -h localhost -d vibe_tracker -f $InitScript 2>&1
    $ErrorActionPreference = "Stop"
    # Filtrer les notices (ce ne sont pas des erreurs)
    $errors = $output | Where-Object { $_ -match "ERROR" -and $_ -notmatch "NOTICE" }
    if ($errors) {
        Write-Host "⚠️ Erreurs lors de l'initialisation:" -ForegroundColor Yellow
        $errors | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    } else {
        Write-Host "✅ Schéma initialisé" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️ Script d'initialisation non trouvé" -ForegroundColor Yellow
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
    Write-Host "PostgreSQL est installé et configuré!" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Pour lancer l'API:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor White
    Write-Host "  `$env:DATABASE_URL = 'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker'" -ForegroundColor White
    Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
    Write-Host ""
    Write-Host "Pour arrêter PostgreSQL:" -ForegroundColor Yellow
    Write-Host "  & '$env:USERPROFILE\scoop\apps\postgresql\current\bin\pg_ctl.exe' -D '$env:USERPROFILE\postgresql-data' stop" -ForegroundColor White
} else {
    Write-Host "❌ Test échoué" -ForegroundColor Red
    exit 1
}
