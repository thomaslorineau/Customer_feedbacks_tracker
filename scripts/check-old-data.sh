#!/bin/bash
# ============================================
# Script pour vérifier les données dans l'ancien volume PostgreSQL
# ============================================

set -e

echo "=========================================="
echo "Vérification des données dans l'ancien volume"
echo "=========================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Vérifier que Docker est disponible
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Erreur: Docker n'est pas installé${NC}"
    exit 1
fi

# Arrêter le container PostgreSQL actuel
echo -e "${YELLOW}Arrêt du container PostgreSQL actuel...${NC}"
docker compose stop postgres 2>/dev/null || true

# Créer un container temporaire avec l'ancienne configuration pour accéder aux données
echo -e "${YELLOW}Création d'un container temporaire pour accéder à l'ancien volume...${NC}"

# Trouver le volume
OLD_VOLUME=$(docker volume ls --format "{{.Name}}" | grep "postgres_data" | head -1)

if [ -z "$OLD_VOLUME" ]; then
    echo -e "${RED}Erreur: Volume PostgreSQL introuvable${NC}"
    exit 1
fi

echo "Volume trouvé: $OLD_VOLUME"

# Créer un container temporaire avec l'ancienne config
docker run -d --name temp_postgres_check \
    -v "$OLD_VOLUME:/var/lib/postgresql/data" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=temp_check_password \
    postgres:15-alpine > /dev/null 2>&1

# Attendre que PostgreSQL démarre
echo -e "${YELLOW}Attente du démarrage de PostgreSQL...${NC}"
sleep 5

# Vérifier les bases de données
echo ""
echo -e "${BLUE}Bases de données trouvées:${NC}"
docker exec temp_postgres_check psql -U postgres -c "\l" 2>/dev/null || echo "Erreur lors de la lecture des bases"

# Vérifier si vibe_tracker existe
echo ""
echo -e "${BLUE}Vérification de vibe_tracker...${NC}"
VIBE_EXISTS=$(docker exec temp_postgres_check psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='vibe_tracker'" 2>/dev/null || echo "0")

if [ "$VIBE_EXISTS" = "1" ]; then
    echo -e "${GREEN}✓ Base vibe_tracker trouvée${NC}"
    
    # Compter les posts
    POST_COUNT=$(docker exec temp_postgres_check psql -U postgres -d vibe_tracker -tAc "SELECT COUNT(*) FROM posts" 2>/dev/null || echo "0")
    echo "  Nombre de posts: $POST_COUNT"
    
    # Vérifier l'utilisateur
    echo ""
    echo -e "${BLUE}Utilisateurs trouvés:${NC}"
    docker exec temp_postgres_check psql -U postgres -d vibe_tracker -c "\du" 2>/dev/null || echo "Erreur"
    
    if [ "$POST_COUNT" -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Des données existent dans vibe_tracker ($POST_COUNT posts)${NC}"
        echo "   Utilisez le script migrate-vibe-to-ocft.sh pour migrer les données"
    else
        echo -e "${GREEN}✓ Aucune donnée dans vibe_tracker${NC}"
    fi
else
    echo -e "${YELLOW}Base vibe_tracker n'existe pas${NC}"
fi

# Vérifier ocft_tracker
echo ""
echo -e "${BLUE}Vérification de ocft_tracker...${NC}"
OCFT_EXISTS=$(docker exec temp_postgres_check psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='ocft_tracker'" 2>/dev/null || echo "0")

if [ "$OCFT_EXISTS" = "1" ]; then
    echo -e "${GREEN}✓ Base ocft_tracker trouvée${NC}"
    POST_COUNT=$(docker exec temp_postgres_check psql -U postgres -d ocft_tracker -tAc "SELECT COUNT(*) FROM posts" 2>/dev/null || echo "0")
    echo "  Nombre de posts: $POST_COUNT"
else
    echo -e "${YELLOW}Base ocft_tracker n'existe pas encore${NC}"
fi

# Nettoyer
echo ""
echo -e "${YELLOW}Nettoyage du container temporaire...${NC}"
docker stop temp_postgres_check > /dev/null 2>&1
docker rm temp_postgres_check > /dev/null 2>&1

echo ""
echo -e "${GREEN}Vérification terminée${NC}"
