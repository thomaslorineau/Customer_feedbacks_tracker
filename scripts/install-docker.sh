#!/bin/bash
# ============================================================================
# Script d'installation Docker pour OVH Customer Feedback Tracker
# Usage: ./scripts/install-docker.sh [--migrate]
# ============================================================================

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }

# Répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Options
MIGRATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --migrate)
            MIGRATE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--migrate]"
            echo ""
            echo "Options:"
            echo "  --migrate    Migrer les données DuckDB vers PostgreSQL après installation"
            exit 0
            ;;
        *)
            error "Option inconnue: $1"
            exit 1
            ;;
    esac
done

cd "$APP_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐳 Installation Docker - OVH Customer Feedback Tracker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# 1. Vérifier les prérequis
# ============================================================================
info "Vérification des prérequis..."

# Docker
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé"
    echo ""
    echo "Installation de Docker:"
    echo "  Ubuntu/Debian: curl -fsSL https://get.docker.com | sh"
    echo "  CentOS/RHEL:   yum install docker-ce docker-ce-cli containerd.io"
    echo ""
    exit 1
fi

DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
success "Docker $DOCKER_VERSION installé"

# Docker Compose
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "v2+")
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $4}' | tr -d ',')
else
    error "Docker Compose n'est pas installé"
    echo ""
    echo "Installation de Docker Compose:"
    echo "  Docker récent: docker compose est inclus (plugin)"
    echo "  Sinon: pip install docker-compose"
    echo ""
    exit 1
fi

success "Docker Compose $COMPOSE_VERSION installé"

# Vérifier que Docker daemon tourne
if ! docker info &> /dev/null; then
    error "Le daemon Docker ne tourne pas"
    echo "  Démarrez-le avec: sudo systemctl start docker"
    exit 1
fi

success "Docker daemon actif"
echo ""

# ============================================================================
# 2. Créer le fichier .env si nécessaire
# ============================================================================
info "Configuration de l'environnement..."

if [ ! -f "backend/.env" ]; then
    warning "Fichier backend/.env non trouvé"
    
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        info "Copié depuis .env.example"
    else
        cat > backend/.env << 'EOF'
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
EOF
        info "Fichier .env créé avec configuration Docker par défaut"
    fi
    
    echo ""
    warning "⚠️  N'oubliez pas de configurer vos clés API dans backend/.env"
    echo ""
fi

success "Configuration prête"
echo ""

# ============================================================================
# 3. Créer les volumes Docker
# ============================================================================
info "Création des volumes Docker..."

docker volume create ovh_tracker_postgres 2>/dev/null || true
docker volume create ovh_tracker_redis 2>/dev/null || true

success "Volumes créés"
echo ""

# ============================================================================
# 4. Build des images
# ============================================================================
info "Construction des images Docker (peut prendre quelques minutes)..."
echo ""

$COMPOSE_CMD build

success "Images construites"
echo ""

# ============================================================================
# 5. Démarrage des services
# ============================================================================
info "Démarrage des services..."

$COMPOSE_CMD up -d

success "Services démarrés"
echo ""

# ============================================================================
# 6. Attendre que les services soient prêts
# ============================================================================
info "Attente que les services soient prêts..."

# PostgreSQL
echo -n "  PostgreSQL: "
for i in {1..30}; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U postgres &>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# Redis
echo -n "  Redis: "
for i in {1..15}; do
    if $COMPOSE_CMD exec -T redis redis-cli ping &>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# API
echo -n "  API: "
sleep 3
for i in {1..30}; do
    if curl -s http://localhost:8000/ &>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""

# ============================================================================
# 7. Migration si demandée
# ============================================================================
if [ "$MIGRATE" = true ]; then
    if [ -f "backend/data.duckdb" ]; then
        info "Migration des données DuckDB → PostgreSQL..."
        $COMPOSE_CMD exec api python scripts/migrate_to_postgres.py
        success "Migration terminée"
    else
        info "Pas de fichier DuckDB à migrer"
    fi
    echo ""
fi

# ============================================================================
# 8. Vérification finale
# ============================================================================
info "Vérification de l'installation..."

echo ""
$COMPOSE_CMD ps
echo ""

# Test API
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
JOBS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/jobs/status 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    success "API accessible sur http://localhost:8000"
else
    warning "API non accessible (HTTP $API_STATUS)"
fi

if [ "$JOBS_STATUS" = "200" ]; then
    success "Endpoint /jobs/status fonctionnel"
else
    warning "Endpoint /jobs/status non accessible (HTTP $JOBS_STATUS)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Installation Docker terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Application: http://localhost:8000"
echo "📊 Dashboard:   http://localhost:8000/dashboard"
echo "📚 API Docs:    http://localhost:8000/api/docs"
echo ""
echo "Commandes utiles:"
echo "  Logs:         $COMPOSE_CMD logs -f"
echo "  Status:       $COMPOSE_CMD ps"
echo "  Restart:      $COMPOSE_CMD restart"
echo "  Stop:         $COMPOSE_CMD stop"
echo "  Update:       ./scripts/update-docker.sh"
echo ""
