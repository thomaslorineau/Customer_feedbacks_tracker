#!/bin/bash
# ============================================================================
# Script de mise à jour Docker pour production Linux
# Usage: ./scripts/update-docker.sh [--migrate] [--rebuild]
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
REBUILD=false
BACKUP=true

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --migrate)
            MIGRATE=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --no-backup)
            BACKUP=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--migrate] [--rebuild] [--no-backup]"
            echo ""
            echo "Options:"
            echo "  --migrate    Exécuter la migration DuckDB → PostgreSQL"
            echo "  --rebuild    Reconstruire les images Docker (force rebuild)"
            echo "  --no-backup  Ne pas faire de backup avant la mise à jour"
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
echo "🐳 Mise à jour Docker de l'application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose n'est pas installé"
    exit 1
fi

# Détecter docker-compose ou docker compose
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

info "Utilisation de: $COMPOSE_CMD"

# 1. Backup de la base PostgreSQL (si running)
if [ "$BACKUP" = true ]; then
    info "Vérification du backup PostgreSQL..."
    
    if $COMPOSE_CMD ps postgres 2>/dev/null | grep -q "Up"; then
        BACKUP_FILE="backend/backups/postgres_backup_$(date +%Y%m%d_%H%M%S).sql"
        mkdir -p backend/backups
        
        info "Sauvegarde PostgreSQL en cours..."
        $COMPOSE_CMD exec -T postgres pg_dump -U postgres ovh_tracker > "$BACKUP_FILE" 2>/dev/null || true
        
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            success "Backup créé: $BACKUP_FILE"
        else
            warning "Backup vide ou échec (nouvelle installation?)"
            rm -f "$BACKUP_FILE"
        fi
    else
        info "PostgreSQL non démarré, backup ignoré"
    fi
fi
echo ""

# 2. Pull du code
info "Mise à jour du code depuis Git..."

if [ -d ".git" ]; then
    # Stash les modifications locales
    if ! git diff --quiet 2>/dev/null; then
        warning "Modifications locales détectées, sauvegarde temporaire..."
        git stash push -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)" || true
    fi
    
    # Pull
    git pull origin main || git pull origin master || {
        error "Échec du git pull"
        exit 1
    }
    
    success "Code mis à jour"
else
    warning "Pas de dépôt Git, mise à jour du code ignorée"
fi
echo ""

# 3. Arrêt des services
info "Arrêt des services Docker..."
$COMPOSE_CMD stop || true
success "Services arrêtés"
echo ""

# 4. Pull/Build des images
if [ "$REBUILD" = true ]; then
    info "Reconstruction des images Docker (--rebuild)..."
    $COMPOSE_CMD build --no-cache
else
    info "Mise à jour des images Docker..."
    $COMPOSE_CMD pull 2>/dev/null || true
    $COMPOSE_CMD build
fi
success "Images Docker prêtes"
echo ""

# 5. Redémarrage des services
info "Démarrage des services Docker..."
$COMPOSE_CMD up -d
success "Services démarrés"
echo ""

# 6. Attendre que PostgreSQL soit prêt
info "Attente que PostgreSQL soit prêt..."
for i in {1..30}; do
    if $COMPOSE_CMD exec -T postgres pg_isready -U postgres &>/dev/null; then
        success "PostgreSQL prêt"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# 7. Migration si demandée
if [ "$MIGRATE" = true ]; then
    info "Exécution de la migration DuckDB → PostgreSQL..."
    
    if [ -f "backend/data.duckdb" ]; then
        $COMPOSE_CMD exec api python scripts/migrate_to_postgres.py || {
            error "Échec de la migration"
            warning "Vous pouvez relancer avec: docker compose exec api python scripts/migrate_to_postgres.py"
        }
        success "Migration terminée"
    else
        warning "Pas de fichier DuckDB à migrer"
    fi
    echo ""
fi

# 8. Vérification de santé
info "Vérification de l'état des services..."
echo ""

$COMPOSE_CMD ps

echo ""

# Test de l'API
info "Test de l'API..."
sleep 3

API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")

if [ "$API_RESPONSE" = "200" ]; then
    success "API accessible (HTTP 200)"
else
    warning "API non accessible (HTTP $API_RESPONSE)"
    echo "   Vérifiez les logs avec: $COMPOSE_CMD logs api"
fi

# Test des jobs
JOBS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/jobs/status 2>/dev/null || echo "000")

if [ "$JOBS_RESPONSE" = "200" ]; then
    success "Endpoint /jobs/status accessible"
else
    warning "Endpoint /jobs/status non accessible (HTTP $JOBS_RESPONSE)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Mise à jour Docker terminée"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Commandes utiles:"
echo "  Logs API:      $COMPOSE_CMD logs -f api"
echo "  Logs Worker:   $COMPOSE_CMD logs -f worker"
echo "  Status:        $COMPOSE_CMD ps"
echo "  Restart:       $COMPOSE_CMD restart"
echo "  Stop:          $COMPOSE_CMD stop"
echo ""
