#!/bin/bash
# ============================================
# Migration DuckDB -> PostgreSQL en Docker
# ============================================

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Migration DuckDB -> PostgreSQL (Docker)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Vérifier que docker-compose est disponible
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERREUR: docker-compose n'est pas installé${NC}"
    exit 1
fi

# Vérifier que les conteneurs sont démarrés
echo -e "${YELLOW}Vérification des conteneurs Docker...${NC}"
if ! docker-compose ps | grep -q "vibe_postgres.*Up"; then
    echo -e "${YELLOW}Démarrage des conteneurs...${NC}"
    docker-compose up -d postgres
    echo "Attente du démarrage de PostgreSQL..."
    sleep 10
fi

# Vérifier que PostgreSQL est prêt
echo -e "${YELLOW}Vérification de PostgreSQL...${NC}"
until docker-compose exec -T postgres pg_isready -U vibe_user -d vibe_tracker > /dev/null 2>&1; do
    echo "Attente de PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL est prêt${NC}"

# Chemin du fichier DuckDB
DUCKDB_FILE="${1:-backend/data.duckdb}"

if [ ! -f "$DUCKDB_FILE" ]; then
    echo -e "${RED}ERREUR: Fichier DuckDB non trouvé: $DUCKDB_FILE${NC}"
    echo "Usage: $0 [chemin/vers/data.duckdb]"
    exit 1
fi

echo ""
echo -e "${YELLOW}Fichier DuckDB: $DUCKDB_FILE${NC}"

# Vérifier le nombre de posts dans DuckDB (optionnel, nécessite duckdb installé localement)
if command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Vérification des données DuckDB...${NC}"
    POST_COUNT=$(python3 -c "
import duckdb
conn = duckdb.connect('$DUCKDB_FILE', read_only=True)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM posts')
print(cur.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")
    echo -e "${BLUE}  Posts à migrer: $POST_COUNT${NC}"
fi

echo ""
echo -e "${YELLOW}Copie du fichier DuckDB dans le conteneur API...${NC}"

# S'assurer que le conteneur API existe (ou créer un conteneur temporaire)
if ! docker-compose ps | grep -q "vibe_api.*Up"; then
    echo -e "${YELLOW}Le conteneur API n'est pas démarré, création d'un conteneur temporaire...${NC}"
    docker-compose build api
fi

# Copier le fichier DuckDB dans le conteneur
CONTAINER_NAME="vibe_api"
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker cp "$DUCKDB_FILE" "${CONTAINER_NAME}:/tmp/data.duckdb"
else
    # Créer un conteneur temporaire pour la migration
    echo -e "${YELLOW}Création d'un conteneur temporaire pour la migration...${NC}"
    docker-compose run --rm -v "$(pwd)/$DUCKDB_FILE:/tmp/data.duckdb:ro" api \
        python scripts/migrate_to_postgres.py \
        --duckdb /tmp/data.duckdb \
        --postgres "$DATABASE_URL"
    exit $?
fi

echo -e "${GREEN}✓ Fichier copié${NC}"

# Obtenir DATABASE_URL depuis docker-compose
echo ""
echo -e "${YELLOW}Récupération de la configuration...${NC}"
POSTGRES_PASSWORD=$(docker-compose exec -T postgres printenv POSTGRES_PASSWORD 2>/dev/null || echo "vibe_secure_password_2026")
DATABASE_URL="postgresql://vibe_user:${POSTGRES_PASSWORD}@postgres:5432/vibe_tracker"

echo -e "${BLUE}  DATABASE_URL: postgresql://vibe_user:***@postgres:5432/vibe_tracker${NC}"

# Exécuter la migration dans le conteneur
echo ""
echo -e "${YELLOW}Exécution de la migration...${NC}"
echo ""

docker-compose exec -e DATABASE_URL="$DATABASE_URL" api \
    python scripts/migrate_to_postgres.py \
    --duckdb /tmp/data.duckdb \
    --postgres "$DATABASE_URL"

MIGRATION_EXIT_CODE=$?

if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Migration réussie!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Vérification des données migrées...${NC}"
    
    # Vérifier le nombre de posts dans PostgreSQL
    docker-compose exec -T postgres psql -U vibe_user -d vibe_tracker -c "SELECT COUNT(*) as total_posts FROM posts;" | grep -E "total_posts|[0-9]+" | head -2
    
    echo ""
    echo -e "${BLUE}Prochaines étapes:${NC}"
    echo "  1. Vérifier que l'API fonctionne correctement"
    echo "  2. Tester quelques endpoints pour confirmer les données"
    echo "  3. (Optionnel) Supprimer le fichier DuckDB après vérification"
    echo ""
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Migration échouée (code: $MIGRATION_EXIT_CODE)${NC}"
    echo -e "${RED}========================================${NC}"
    exit $MIGRATION_EXIT_CODE
fi
