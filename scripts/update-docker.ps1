# ============================================================================
# Script de mise à jour Docker pour OVH Customer Feedback Tracker (Windows)
# Usage: .\scripts\update-docker.ps1 [-Migrate] [-Rebuild] [-NoBackup]
# ============================================================================

param(
    [switch]$Migrate,
    [switch]$Rebuild,
    [switch]$NoBackup,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warn { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "❌ $args" -ForegroundColor Red }

if ($Help) {
    Write-Host "Usage: .\scripts\update-docker.ps1 [-Migrate] [-Rebuild] [-NoBackup]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Migrate    Exécuter la migration DuckDB → PostgreSQL"
    Write-Host "  -Rebuild    Reconstruire les images Docker (force rebuild)"
    Write-Host "  -NoBackup   Ne pas faire de backup avant la mise à jour"
    exit 0
}

# Répertoire du projet
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Split-Path -Parent $ScriptDir
Set-Location $AppDir

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "🐳 Mise à jour Docker de l'application"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Vérifier Docker
try {
    docker info 2>$null | Out-Null
} catch {
    Write-Err "Docker n'est pas disponible"
    exit 1
}

# Détecter docker compose
$ComposeCmd = "docker compose"
try {
    docker compose version 2>$null | Out-Null
} catch {
    $ComposeCmd = "docker-compose"
}

Write-Info "Utilisation de: $ComposeCmd"
Write-Host ""

# ============================================================================
# 1. Backup PostgreSQL
# ============================================================================
if (-not $NoBackup) {
    Write-Info "Vérification du backup PostgreSQL..."
    
    $pgRunning = docker compose ps postgres 2>$null | Select-String "Up"
    if ($pgRunning) {
        $backupDir = "backend\backups"
        if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }
        
        $backupFile = "$backupDir\postgres_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
        
        Write-Info "Sauvegarde PostgreSQL..."
        try {
            docker compose exec -T postgres pg_dump -U postgres ovh_tracker > $backupFile
            if ((Get-Item $backupFile).Length -gt 0) {
                Write-Success "Backup créé: $backupFile"
            } else {
                Write-Warn "Backup vide (nouvelle installation?)"
                Remove-Item $backupFile -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Warn "Backup échoué (nouvelle installation?)"
        }
    } else {
        Write-Info "PostgreSQL non démarré, backup ignoré"
    }
}
Write-Host ""

# ============================================================================
# 2. Pull du code
# ============================================================================
Write-Info "Mise à jour du code depuis Git..."

if (Test-Path ".git") {
    # Stash les modifications locales
    $changes = git diff --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Modifications locales détectées, sauvegarde temporaire..."
        git stash push -m "Auto-stash before update $(Get-Date -Format 'yyyyMMdd_HHmmss')" 2>$null
    }
    
    # Pull
    git pull origin main 2>$null
    if ($LASTEXITCODE -ne 0) {
        git pull origin master 2>$null
    }
    
    Write-Success "Code mis à jour"
} else {
    Write-Warn "Pas de dépôt Git, mise à jour du code ignorée"
}
Write-Host ""

# ============================================================================
# 3. Arrêt des services
# ============================================================================
Write-Info "Arrêt des services Docker..."
docker compose stop 2>$null
Write-Success "Services arrêtés"
Write-Host ""

# ============================================================================
# 4. Build des images
# ============================================================================
if ($Rebuild) {
    Write-Info "Reconstruction des images Docker (--Rebuild)..."
    docker compose build --no-cache
} else {
    Write-Info "Mise à jour des images Docker..."
    docker compose pull 2>$null
    docker compose build
}
Write-Success "Images Docker prêtes"
Write-Host ""

# ============================================================================
# 5. Redémarrage
# ============================================================================
Write-Info "Démarrage des services Docker..."
docker compose up -d
Write-Success "Services démarrés"
Write-Host ""

# ============================================================================
# 6. Attendre PostgreSQL
# ============================================================================
Write-Info "Attente que PostgreSQL soit prêt..."
for ($i = 0; $i -lt 30; $i++) {
    try {
        $result = docker compose exec -T postgres pg_isready -U postgres 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "PostgreSQL prêt"
            break
        }
    } catch {}
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}
Write-Host ""

# ============================================================================
# 7. Migration si demandée
# ============================================================================
if ($Migrate) {
    Write-Info "Exécution de la migration DuckDB → PostgreSQL..."
    
    if (Test-Path "backend\data.duckdb") {
        docker compose exec api python scripts/migrate_to_postgres.py
        Write-Success "Migration terminée"
    } else {
        Write-Warn "Pas de fichier DuckDB à migrer"
    }
    Write-Host ""
}

# ============================================================================
# 8. Vérification
# ============================================================================
Write-Info "Vérification de l'état des services..."
Write-Host ""

docker compose ps

Write-Host ""

# Test API
Start-Sleep -Seconds 3
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Success "API accessible (HTTP 200)"
    }
} catch {
    Write-Warn "API non accessible"
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/jobs/status" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Success "Endpoint /jobs/status accessible"
    }
} catch {
    Write-Warn "Endpoint /jobs/status non accessible"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "✅ Mise à jour Docker terminée" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "Commandes utiles:"
Write-Host "  Logs API:      docker compose logs -f api"
Write-Host "  Logs Worker:   docker compose logs -f worker"
Write-Host "  Status:        docker compose ps"
Write-Host "  Restart:       docker compose restart"
Write-Host "  Stop:          docker compose stop"
Write-Host ""
