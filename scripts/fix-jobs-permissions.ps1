# ============================================
# Script de correction des permissions sur la table jobs
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Correction permissions table jobs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$pgBin = "C:\Users\tlorinea\scoop\apps\postgresql\current\bin"
$psql = Join-Path $pgBin "psql.exe"
$dbUser = "postgres"
$dbPassword = "ocft_secure_password_2026"
$dbName = "ocft_tracker"
$dbHost = "localhost"
$dbPort = "5432"
$targetUser = "ocft_user"

Write-Host "[1/3] Vérification de la connexion PostgreSQL..." -ForegroundColor Yellow
$env:PGPASSWORD = $dbPassword

# Test de connexion
$testConnection = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "SELECT 1;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur de connexion à PostgreSQL" -ForegroundColor Red
    Write-Host $testConnection -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Connexion PostgreSQL OK" -ForegroundColor Green
Write-Host ""

Write-Host "[2/3] Vérification de l'existence de la table jobs..." -ForegroundColor Yellow
$tableExists = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'jobs');" 2>&1
if ($tableExists -match "t|true|1") {
    Write-Host "   ✅ Table 'jobs' existe" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Table 'jobs' n'existe pas, création..." -ForegroundColor Yellow
    # Créer la table jobs
    $createTable = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c @"
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    payload JSONB,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    progress INTEGER DEFAULT 0,
    result JSONB,
    error TEXT,
    worker_id TEXT
);
"@ 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erreur lors de la création de la table jobs" -ForegroundColor Red
        Write-Host $createTable -ForegroundColor Red
        exit 1
    }
    Write-Host "   ✅ Table 'jobs' créée" -ForegroundColor Green
}
Write-Host ""

Write-Host "[3/3] Correction des permissions..." -ForegroundColor Yellow

# Donner le propriétaire à ocft_user
$alterOwner = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "ALTER TABLE IF EXISTS jobs OWNER TO $targetUser;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Erreur lors du changement de propriétaire (peut être normal si déjà propriétaire)" -ForegroundColor Yellow
}

# Donner toutes les permissions
$grantAll = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "GRANT ALL PRIVILEGES ON TABLE jobs TO $targetUser;" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors de l'attribution des permissions" -ForegroundColor Red
    Write-Host $grantAll -ForegroundColor Red
    exit 1
}

# Donner les permissions sur les séquences si elles existent
$grantSeq = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $targetUser;" 2>&1

# Créer les index si nécessaire
$createIndex = & $psql -U $dbUser -d $dbName -h $dbHost -p $dbPort -c "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Erreur lors de la création de l'index (peut être normal si existe déjà)" -ForegroundColor Yellow
}

Write-Host "   ✅ Permissions corrigées" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Correction terminée !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Testez maintenant l'endpoint:" -ForegroundColor Yellow
Write-Host "   http://localhost:8000/scrape/jobs?status=running&limit=5" -ForegroundColor Gray
Write-Host ""
