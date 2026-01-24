# ============================================================================
# Script d'installation Docker pour OVH Customer Feedback Tracker (Windows)
# Usage: .\scripts\install-docker.ps1 [-Migrate]
# ============================================================================

param(
    [switch]$Migrate,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Write-Info { Write-Host "ℹ️  $args" -ForegroundColor Blue }
function Write-Success { Write-Host "✅ $args" -ForegroundColor Green }
function Write-Warn { Write-Host "⚠️  $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "❌ $args" -ForegroundColor Red }

if ($Help) {
    Write-Host "Usage: .\scripts\install-docker.ps1 [-Migrate]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Migrate    Migrer les données DuckDB vers PostgreSQL après installation"
    exit 0
}

# Répertoire du projet
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Split-Path -Parent $ScriptDir
Set-Location $AppDir

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "🐳 Installation Docker - OVH Customer Feedback Tracker"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# ============================================================================
# 1. Vérifier les prérequis
# ============================================================================
Write-Info "Vérification des prérequis..."

# Docker
try {
    $dockerVersion = docker --version
    Write-Success "Docker installé: $dockerVersion"
} catch {
    Write-Err "Docker n'est pas installé"
    Write-Host ""
    Write-Host "Installation de Docker Desktop:"
    Write-Host "  https://www.docker.com/products/docker-desktop/"
    Write-Host ""
    exit 1
}

# Docker Compose
try {
    $composeVersion = docker compose version 2>$null
    if ($composeVersion) {
        Write-Success "Docker Compose (plugin) installé"
        $ComposeCmd = "docker compose"
    }
} catch {
    try {
        $composeVersion = docker-compose --version
        Write-Success "Docker Compose installé: $composeVersion"
        $ComposeCmd = "docker-compose"
    } catch {
        Write-Err "Docker Compose n'est pas installé"
        exit 1
    }
}

# Vérifier Docker daemon
try {
    docker info 2>$null | Out-Null
    Write-Success "Docker daemon actif"
} catch {
    Write-Err "Docker Desktop n'est pas démarré"
    Write-Host "  Lancez Docker Desktop et réessayez"
    exit 1
}

Write-Host ""

# ============================================================================
# 2. Créer le fichier .env si nécessaire
# ============================================================================
Write-Info "Configuration de l'environnement..."

if (-not (Test-Path "backend\.env")) {
    Write-Warn "Fichier backend\.env non trouvé"
    
    if (Test-Path "backend\.env.example") {
        Copy-Item "backend\.env.example" "backend\.env"
        Write-Info "Copié depuis .env.example"
    } else {
        @"
# Configuration générée automatiquement
# Mode Docker
USE_DOCKER=true

# PostgreSQL (via Docker)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ovh_tracker

# Redis (via Docker)
REDIS_URL=redis://redis:6379/0

# API Keys (à configurer)
# OPENAI_API_KEY=sk-...
# REDDIT_CLIENT_ID=...
# REDDIT_CLIENT_SECRET=...
"@ | Out-File -FilePath "backend\.env" -Encoding UTF8
        Write-Info "Fichier .env créé avec configuration Docker par défaut"
    }
    
    Write-Host ""
    Write-Warn "⚠️  N'oubliez pas de configurer vos clés API dans backend\.env"
    Write-Host ""
}

Write-Success "Configuration prête"
Write-Host ""

# ============================================================================
# 3. Build des images
# ============================================================================
Write-Info "Construction des images Docker (peut prendre quelques minutes)..."
Write-Host ""

if ($ComposeCmd -eq "docker compose") {
    docker compose build
} else {
    docker-compose build
}

Write-Success "Images construites"
Write-Host ""

# ============================================================================
# 4. Démarrage des services
# ============================================================================
Write-Info "Démarrage des services..."

if ($ComposeCmd -eq "docker compose") {
    docker compose up -d
} else {
    docker-compose up -d
}

Write-Success "Services démarrés"
Write-Host ""

# ============================================================================
# 5. Attendre que les services soient prêts
# ============================================================================
Write-Info "Attente que les services soient prêts..."

# Attendre quelques secondes
Start-Sleep -Seconds 10

# Test API
Write-Host -NoNewline "  API: "
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "OK" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
}

Write-Host ""

# ============================================================================
# 6. Migration si demandée
# ============================================================================
if ($Migrate) {
    if (Test-Path "backend\data.duckdb") {
        Write-Info "Migration des données DuckDB → PostgreSQL..."
        if ($ComposeCmd -eq "docker compose") {
            docker compose exec api python scripts/migrate_to_postgres.py
        } else {
            docker-compose exec api python scripts/migrate_to_postgres.py
        }
        Write-Success "Migration terminée"
    } else {
        Write-Info "Pas de fichier DuckDB à migrer"
    }
    Write-Host ""
}

# ============================================================================
# 7. Vérification finale
# ============================================================================
Write-Info "Vérification de l'installation..."
Write-Host ""

if ($ComposeCmd -eq "docker compose") {
    docker compose ps
} else {
    docker-compose ps
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "✅ Installation Docker terminée !" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "🌐 Application: http://localhost:8000"
Write-Host "📊 Dashboard:   http://localhost:8000/dashboard"
Write-Host "📚 API Docs:    http://localhost:8000/api/docs"
Write-Host ""
Write-Host "Commandes utiles:"
Write-Host "  Logs:         docker compose logs -f"
Write-Host "  Status:       docker compose ps"
Write-Host "  Restart:      docker compose restart"
Write-Host "  Stop:         docker compose stop"
Write-Host "  Update:       .\scripts\update-docker.ps1"
Write-Host ""
