# ============================================
# Initialiser la base de données VibeCoding
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Initialisation Base de Données" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Vérifier que PostgreSQL est démarré
$PostgresPath = "$env:USERPROFILE\postgresql-portable"
$BinPath = Join-Path $PostgresPath "bin"
$Psql = Join-Path $BinPath "psql.exe"

if (-not (Test-Path $Psql)) {
    Write-Host "ERREUR: psql.exe non trouvé" -ForegroundColor Red
    Write-Host "Assurez-vous que PostgreSQL est installé" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ou utilisez un service cloud et configurez DATABASE_URL" -ForegroundColor Yellow
    exit 1
}

# Variables d'environnement pour PostgreSQL
$env:PGPASSWORD = "postgres"

# Créer la base de données et l'utilisateur
Write-Host "Création de la base de données..." -ForegroundColor Green

& $Psql -U postgres -h localhost -c "CREATE DATABASE vibe_tracker;" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Base de données existe déjà ou erreur (normal si déjà créée)" -ForegroundColor Yellow
}

& $Psql -U postgres -h localhost -c "CREATE USER vibe_user WITH PASSWORD 'dev_password_123';" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Utilisateur existe déjà ou erreur (normal si déjà créé)" -ForegroundColor Yellow
}

& $Psql -U postgres -h localhost -c "ALTER DATABASE vibe_tracker OWNER TO vibe_user;" 2>&1 | Out-Null
& $Psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE vibe_tracker TO vibe_user;" 2>&1 | Out-Null

# Exécuter le script d'initialisation
Write-Host "Exécution du schéma SQL..." -ForegroundColor Green
$InitScript = Join-Path $ProjectRoot "backend\scripts\init_postgres.sql"
$env:PGPASSWORD = "dev_password_123"

& $Psql -U vibe_user -h localhost -d vibe_tracker -f $InitScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Base de données initialisée avec succès!" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors de l'initialisation" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Configuration terminée!" -ForegroundColor Green
Write-Host ""
Write-Host "DATABASE_URL=postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour lancer l'API:" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  `$env:DATABASE_URL = 'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker'" -ForegroundColor White
Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
