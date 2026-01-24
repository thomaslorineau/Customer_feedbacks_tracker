#!/bin/bash
# ============================================
# VibeCoding Docker Startup Script (Linux/Mac)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}VibeCoding Docker Manager${NC}"
echo -e "${CYAN}========================================${NC}"

# Check Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running. Please start Docker.${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Parse arguments
BUILD=false
MIGRATE=false
LOGS=false
STOP=false
DOWN=false
STATUS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            BUILD=true
            shift
            ;;
        --migrate|-m)
            MIGRATE=true
            shift
            ;;
        --logs|-l)
            LOGS=true
            shift
            ;;
        --stop|-s)
            STOP=true
            shift
            ;;
        --down|-d)
            DOWN=true
            shift
            ;;
        --status)
            STATUS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--build] [--migrate] [--logs] [--stop] [--down] [--status]"
            exit 1
            ;;
    esac
done

if $STOP; then
    echo -e "${YELLOW}Stopping containers...${NC}"
    docker compose stop
    exit 0
fi

if $DOWN; then
    echo -e "${YELLOW}Stopping and removing containers...${NC}"
    docker compose down
    exit 0
fi

if $STATUS; then
    echo -e "${GREEN}Container Status:${NC}"
    docker compose ps
    echo ""
    echo -e "${GREEN}Container Logs (last 10 lines each):${NC}"
    docker compose logs --tail=10
    exit 0
fi

if $LOGS; then
    echo -e "${YELLOW}Following logs (Ctrl+C to stop)...${NC}"
    docker compose logs -f
    exit 0
fi

# Build if requested
if $BUILD; then
    echo -e "${YELLOW}Building Docker images...${NC}"
    docker compose build --no-cache
fi

# Start services
echo -e "${GREEN}Starting Docker services...${NC}"
docker compose up -d

# Wait for PostgreSQL
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=0
until docker compose exec -T postgres pg_isready -U vibe_user -d vibe_tracker 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}ERROR: PostgreSQL failed to start${NC}"
        docker compose logs postgres
        exit 1
    fi
    echo "  Waiting... ($attempt/$max_attempts)"
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Wait for Redis
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
attempt=0
until [ "$(docker compose exec -T redis redis-cli ping 2>/dev/null)" = "PONG" ]; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo -e "${RED}ERROR: Redis failed to start${NC}"
        exit 1
    fi
    echo "  Waiting... ($attempt/$max_attempts)"
    sleep 1
done
echo -e "${GREEN}Redis is ready!${NC}"

# Run migration if requested
if $MIGRATE; then
    echo -e "${YELLOW}Running database migration...${NC}"
    if [ -f "$PROJECT_ROOT/backend/data.duckdb" ]; then
        echo -e "${CYAN}Found DuckDB database, migrating to PostgreSQL...${NC}"
        docker compose exec api python -m scripts.migrate_to_postgres --duckdb /app/data.duckdb
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Migration completed successfully!${NC}"
        else
            echo -e "${YELLOW}Migration had issues, check logs above${NC}"
        fi
    else
        echo -e "${YELLOW}No DuckDB database found, starting fresh${NC}"
    fi
fi

# Show status
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Docker Stack Status${NC}"
echo -e "${CYAN}========================================${NC}"
docker compose ps

echo ""
echo -e "${GREEN}Services:${NC}"
echo "  - API:        http://localhost:8000"
echo "  - API Docs:   http://localhost:8000/api/docs"
echo "  - Dashboard:  http://localhost:8000/dashboard"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis:      localhost:6379"

echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  ./start-docker.sh --logs      # Follow all logs"
echo "  ./start-docker.sh --stop      # Stop containers"
echo "  ./start-docker.sh --down      # Stop and remove containers"
echo "  ./start-docker.sh --status    # Show container status"
echo "  ./start-docker.sh --build     # Rebuild images"
echo "  ./start-docker.sh --migrate   # Migrate DuckDB to PostgreSQL"
