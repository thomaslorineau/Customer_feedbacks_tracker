# ============================================
# Migration DuckDB -> PostgreSQL en Docker (PowerShell)
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration DuckDB -> PostgreSQL (Docker)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier docker-compose
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "ERREUR: docker-compose n'est pas installe" -ForegroundColor Red
    exit 1
}

# Vérifier que les conteneurs sont démarrés
Write-Host "Verification des conteneurs Docker..." -ForegroundColor Yellow
$postgresStatus = docker-compose ps postgres 2>&1
if ($postgresStatus -notmatch "Up") {
    Write-Host "Demarrage des conteneurs..." -ForegroundColor Yellow
    docker-compose up -d postgres
    Write-Host "Attente du demarrage de PostgreSQL..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
}

# Vérifier que PostgreSQL est prêt
Write-Host "Verification de PostgreSQL..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $result = docker-compose exec -T postgres pg_isready -U ocft_user -d ocft_tracker 2>&1
    if ($LASTEXITCODE -eq 0) {
        break
    }
    Start-Sleep -Seconds 2
    $attempt++
}

if ($attempt -eq $maxAttempts) {
    Write-Host "ERREUR: PostgreSQL n'a pas demarre dans les delais" -ForegroundColor Red
    exit 1
}

Write-Host "OK: PostgreSQL est pret" -ForegroundColor Green

# Chemin du fichier DuckDB
$DuckDbFile = $args[0]
if (-not $DuckDbFile) {
    $DuckDbFile = "backend\data.duckdb"
}

if (-not (Test-Path $DuckDbFile)) {
    Write-Host "ERREUR: Fichier DuckDB non trouve: $DuckDbFile" -ForegroundColor Red
    Write-Host "Usage: .\scripts\migrate-docker.ps1 [chemin\vers\data.duckdb]" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Fichier DuckDB: $DuckDbFile" -ForegroundColor Yellow

# Vérifier le nombre de posts (optionnel)
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Verification des donnees DuckDB..." -ForegroundColor Yellow
    try {
        $postCount = python -c "import duckdb; conn = duckdb.connect('$DuckDbFile', read_only=True); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM posts'); print(cur.fetchone()[0]); conn.close()" 2>&1
        Write-Host "  Posts a migrer: $postCount" -ForegroundColor Cyan
    } catch {
        Write-Host "  Impossible de lire DuckDB (normal si duckdb n'est pas installe localement)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Copie du fichier DuckDB dans le conteneur..." -ForegroundColor Yellow

# Vérifier si le conteneur API existe
$apiContainer = docker ps --format "{{.Names}}" | Select-String "ocft_api"
$tempContainer = $false

if (-not $apiContainer) {
    Write-Host "Le conteneur API n'est pas demarre, utilisation d'un conteneur temporaire..." -ForegroundColor Yellow
    $tempContainer = $true
}

# Obtenir DATABASE_URL depuis docker-compose
Write-Host ""
Write-Host "Recuperation de la configuration..." -ForegroundColor Yellow
$postgresPassword = docker-compose exec -T postgres printenv POSTGRES_PASSWORD 2>&1
if ($LASTEXITCODE -ne 0 -or -not $postgresPassword) {
    $postgresPassword = "ocft_secure_password_2026"
}
$databaseUrl = "postgresql://ocft_user:${postgresPassword}@postgres:5432/ocft_tracker"

Write-Host "  DATABASE_URL: postgresql://ocft_user:***@postgres:5432/ocft_tracker" -ForegroundColor Cyan

# Exécuter la migration
Write-Host ""
Write-Host "Execution de la migration..." -ForegroundColor Yellow
Write-Host ""

if ($tempContainer) {
    # Utiliser docker-compose run pour créer un conteneur temporaire
    $absolutePath = (Resolve-Path $DuckDbFile).Path
    $relativePath = $DuckDbFile -replace "\\", "/"
    
    docker-compose run --rm `
        -v "${absolutePath}:/tmp/data.duckdb:ro" `
        -e "DATABASE_URL=$databaseUrl" `
        api `
        python scripts/migrate_to_postgres.py `
        --duckdb /tmp/data.duckdb `
        --postgres $databaseUrl
} else {
    # Copier le fichier dans le conteneur existant
    docker cp $DuckDbFile "ocft_api:/tmp/data.duckdb"
    
    # Exécuter la migration
    docker-compose exec -e "DATABASE_URL=$databaseUrl" api `
        python scripts/migrate_to_postgres.py `
        --duckdb /tmp/data.duckdb `
        --postgres $databaseUrl
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "OK: Migration reussie!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verification des donnees migrees..." -ForegroundColor Yellow
    
    # Vérifier le nombre de posts
    docker-compose exec -T postgres psql -U ocft_user -d ocft_tracker -c "SELECT COUNT(*) as total_posts FROM posts;" 2>&1 | Select-String -Pattern "total_posts|^\s*\d+" | Select-Object -First 2
    
    Write-Host ""
    Write-Host "Prochaines etapes:" -ForegroundColor Cyan
    Write-Host "  1. Verifier que l'API fonctionne correctement" -ForegroundColor White
    Write-Host "  2. Tester quelques endpoints pour confirmer les donnees" -ForegroundColor White
    Write-Host "  3. (Optionnel) Supprimer le fichier DuckDB apres verification" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERREUR: Migration echouee (code: $LASTEXITCODE)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit $LASTEXITCODE
}
