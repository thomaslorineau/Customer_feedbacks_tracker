#!/bin/bash
# ============================================
# Script de migration vibe -> ocft
# Migre les données de vibe_tracker vers ocft_tracker
# ============================================

set -e

echo "=========================================="
echo "Migration vibe -> ocft"
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

# Vérifier que les containers existent
if ! docker ps -a --format "{{.Names}}" | grep -q "^ocft_postgres$"; then
    echo -e "${RED}Erreur: Container ocft_postgres introuvable${NC}"
    echo "   Assurez-vous que docker-compose.yml a été mis à jour et que les containers sont créés"
    exit 1
fi

# Vérifier que PostgreSQL est prêt
echo -e "${YELLOW}Vérification de PostgreSQL...${NC}"
if ! docker compose exec -T postgres pg_isready -U ocft_user -d ocft_tracker > /dev/null 2>&1; then
    echo -e "${RED}Erreur: PostgreSQL n'est pas prêt${NC}"
    echo "   Démarrez les containers avec: docker compose up -d postgres"
    exit 1
fi

# Vérifier si vibe_tracker existe encore (ancienne base)
OLD_DB_EXISTS=$(docker compose exec -T postgres psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='vibe_tracker'" 2>/dev/null || echo "0")

if [ "$OLD_DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}Ancienne base de données 'vibe_tracker' détectée${NC}"
    echo ""
    echo "Voulez-vous migrer les données de vibe_tracker vers ocft_tracker ? (o/N)"
    read -r response
    
    if [[ "$response" =~ ^[Oo]$ ]]; then
        echo ""
        echo -e "${BLUE}Migration des données...${NC}"
        
        # Compter les posts dans l'ancienne base
        OLD_COUNT=$(docker compose exec -T postgres psql -U vibe_user -d vibe_tracker -tAc "SELECT COUNT(*) FROM posts" 2>/dev/null || echo "0")
        echo "  Posts dans vibe_tracker: $OLD_COUNT"
        
        # Compter les posts dans la nouvelle base
        NEW_COUNT=$(docker compose exec -T postgres psql -U ocft_user -d ocft_tracker -tAc "SELECT COUNT(*) FROM posts" 2>/dev/null || echo "0")
        echo "  Posts dans ocft_tracker: $NEW_COUNT"
        
        if [ "$OLD_COUNT" -gt 0 ] && [ "$NEW_COUNT" -eq 0 ]; then
            echo ""
            echo -e "${YELLOW}Export des données depuis vibe_tracker...${NC}"
            docker compose exec -T postgres pg_dump -U vibe_user -d vibe_tracker --data-only --table=posts > /tmp/vibe_posts_export.sql 2>/dev/null || {
                echo -e "${RED}Erreur lors de l'export${NC}"
                exit 1
            }
            
            echo -e "${YELLOW}Import des données dans ocft_tracker...${NC}"
            docker compose exec -T postgres psql -U ocft_user -d ocft_tracker < /tmp/vibe_posts_export.sql 2>/dev/null || {
                echo -e "${RED}Erreur lors de l'import${NC}"
                exit 1
            }
            
            # Vérifier le résultat
            FINAL_COUNT=$(docker compose exec -T postgres psql -U ocft_user -d ocft_tracker -tAc "SELECT COUNT(*) FROM posts" 2>/dev/null || echo "0")
            echo ""
            echo -e "${GREEN}✓ Migration terminée: $FINAL_COUNT posts dans ocft_tracker${NC}"
            
            # Nettoyer
            rm -f /tmp/vibe_posts_export.sql
            
            echo ""
            echo "Voulez-vous supprimer l'ancienne base de données 'vibe_tracker' ? (o/N)"
            read -r delete_response
            if [[ "$delete_response" =~ ^[Oo]$ ]]; then
                echo -e "${YELLOW}Suppression de vibe_tracker...${NC}"
                docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS vibe_tracker;" 2>/dev/null || true
                echo -e "${GREEN}✓ Ancienne base supprimée${NC}"
            fi
        elif [ "$NEW_COUNT" -gt 0 ]; then
            echo -e "${YELLOW}⚠ La nouvelle base contient déjà des données ($NEW_COUNT posts)${NC}"
            echo "   Migration ignorée pour éviter les doublons"
        else
            echo -e "${YELLOW}⚠ Aucune donnée à migrer${NC}"
        fi
    else
        echo "Migration annulée"
    fi
else
    echo -e "${GREEN}✓ Aucune ancienne base de données détectée${NC}"
fi

echo ""
echo -e "${GREEN}Migration terminée${NC}"
echo ""
echo "Pour vérifier:"
echo "  docker compose exec postgres psql -U ocft_user -d ocft_tracker -c 'SELECT COUNT(*) FROM posts;'"
