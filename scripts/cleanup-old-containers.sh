#!/bin/bash
# ============================================
# Script de nettoyage des anciens containers vibe_*
# ============================================

set -e

echo "=========================================="
echo "Nettoyage des anciens containers vibe_*"
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

# Lister les anciens containers
OLD_CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep "^vibe_" || true)

if [ -z "$OLD_CONTAINERS" ]; then
    echo -e "${GREEN}✓ Aucun ancien container détecté${NC}"
else
    echo -e "${YELLOW}Anciens containers détectés:${NC}"
    echo "$OLD_CONTAINERS" | while read -r container; do
        echo "  - $container"
    done
    echo ""
    
    echo "Voulez-vous arrêter et supprimer ces containers ? (o/N)"
    read -r response
    
    if [[ "$response" =~ ^[Oo]$ ]]; then
        echo ""
        echo -e "${BLUE}Arrêt des anciens containers...${NC}"
        echo "$OLD_CONTAINERS" | while read -r container; do
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
            echo "  ✓ Supprimé: $container"
        done
        echo -e "${GREEN}✓ Anciens containers supprimés${NC}"
    else
        echo "Nettoyage annulé"
    fi
fi

# Vérifier les anciens volumes
echo ""
echo -e "${YELLOW}Vérification des volumes...${NC}"
OLD_VOLUMES=$(docker volume ls --format "{{.Name}}" | grep "vibe\|customer_feedbacks" || true)

if [ -z "$OLD_VOLUMES" ]; then
    echo -e "${GREEN}✓ Aucun ancien volume détecté${NC}"
else
    echo -e "${YELLOW}Anciens volumes détectés:${NC}"
    echo "$OLD_VOLUMES" | while read -r volume; do
        echo "  - $volume"
    done
    echo ""
    echo "⚠️  Les volumes contiennent les données PostgreSQL."
    echo "   Ne les supprimez QUE si vous avez migré les données vers ocft_tracker"
    echo ""
    echo "Voulez-vous supprimer ces volumes ? (o/N)"
    read -r response
    
    if [[ "$response" =~ ^[Oo]$ ]]; then
        echo ""
        echo -e "${BLUE}Suppression des anciens volumes...${NC}"
        echo "$OLD_VOLUMES" | while read -r volume; do
            docker volume rm "$volume" 2>/dev/null || true
            echo "  ✓ Supprimé: $volume"
        done
        echo -e "${GREEN}✓ Anciens volumes supprimés${NC}"
    else
        echo "Suppression des volumes annulée"
    fi
fi

# Vérifier les anciens réseaux
echo ""
echo -e "${YELLOW}Vérification des réseaux...${NC}"
OLD_NETWORKS=$(docker network ls --format "{{.Name}}" | grep "vibe\|customer_feedbacks" || true)

if [ -z "$OLD_NETWORKS" ]; then
    echo -e "${GREEN}✓ Aucun ancien réseau détecté${NC}"
else
    echo -e "${YELLOW}Anciens réseaux détectés:${NC}"
    echo "$OLD_NETWORKS" | while read -r network; do
        echo "  - $network"
    done
    echo ""
    echo "Voulez-vous supprimer ces réseaux ? (o/N)"
    read -r response
    
    if [[ "$response" =~ ^[Oo]$ ]]; then
        echo ""
        echo -e "${BLUE}Suppression des anciens réseaux...${NC}"
        echo "$OLD_NETWORKS" | while read -r network; do
            docker network rm "$network" 2>/dev/null || true
            echo "  ✓ Supprimé: $network"
        done
        echo -e "${GREEN}✓ Anciens réseaux supprimés${NC}"
    else
        echo "Suppression des réseaux annulée"
    fi
fi

echo ""
echo -e "${GREEN}Nettoyage terminé${NC}"
echo ""
echo "Vous pouvez maintenant démarrer les nouveaux containers avec:"
echo "  docker compose down"
echo "  docker compose up -d"
