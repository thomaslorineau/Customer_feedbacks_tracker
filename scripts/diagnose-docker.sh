#!/bin/bash
# ============================================
# Script de diagnostic Docker pour OCFT
# ============================================

set -e

echo "=========================================="
echo "Diagnostic Docker - OCFT"
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

# 1. Vérifier l'état des containers
echo -e "${BLUE}1. État des containers Docker:${NC}"
echo ""
docker compose ps -a
echo ""

# 2. Vérifier les containers en cours d'exécution
echo -e "${BLUE}2. Containers en cours d'exécution:${NC}"
RUNNING=$(docker compose ps --format json | jq -r 'select(.State == "running") | .Name' 2>/dev/null || docker compose ps | grep "Up" || echo "Aucun")
if [ -z "$RUNNING" ] || [ "$RUNNING" = "Aucun" ]; then
    echo -e "${RED}✗ Aucun container en cours d'exécution${NC}"
else
    echo -e "${GREEN}✓ Containers en cours d'exécution:${NC}"
    echo "$RUNNING"
fi
echo ""

# 3. Vérifier les ports exposés
echo -e "${BLUE}3. Ports exposés:${NC}"
docker compose ps --format "table {{.Name}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""

# 4. Vérifier les logs de l'API
echo -e "${BLUE}4. Dernières lignes des logs API (50 lignes):${NC}"
echo ""
docker compose logs api --tail=50 2>/dev/null || echo "Impossible de récupérer les logs"
echo ""

# 5. Vérifier la santé des containers
echo -e "${BLUE}5. Santé des containers:${NC}"
echo ""
for service in api postgres redis; do
    HEALTH=$(docker compose ps --format json | jq -r "select(.Service == \"$service\") | .Health" 2>/dev/null || docker compose ps | grep "$service" | awk '{print $NF}' || echo "unknown")
    if [ "$HEALTH" = "healthy" ]; then
        echo -e "  ${GREEN}✓ $service: $HEALTH${NC}"
    elif [ "$HEALTH" = "unhealthy" ]; then
        echo -e "  ${RED}✗ $service: $HEALTH${NC}"
    else
        echo -e "  ${YELLOW}? $service: $HEALTH${NC}"
    fi
done
echo ""

# 6. Vérifier les réseaux Docker
echo -e "${BLUE}6. Réseaux Docker:${NC}"
docker network ls | grep -E "ocft|customer_feedbacks" || echo "Aucun réseau trouvé"
echo ""

# 7. Vérifier les volumes
echo -e "${BLUE}7. Volumes Docker:${NC}"
docker volume ls | grep -E "ocft|customer_feedbacks|postgres|redis" || echo "Aucun volume trouvé"
echo ""

# 8. Tester la connexion PostgreSQL
echo -e "${BLUE}8. Test de connexion PostgreSQL:${NC}"
if docker compose exec -T postgres pg_isready -U ocft_user -d ocft_tracker 2>/dev/null; then
    echo -e "${GREEN}✓ PostgreSQL est accessible${NC}"
else
    echo -e "${RED}✗ PostgreSQL n'est pas accessible${NC}"
fi
echo ""

# 9. Vérifier les ports en écoute
echo -e "${BLUE}9. Ports en écoute sur le système:${NC}"
netstat -tlnp 2>/dev/null | grep ":11840\|:5432\|:6379" || ss -tlnp 2>/dev/null | grep ":11840\|:5432\|:6379" || echo "Impossible de vérifier les ports (nécessite les droits root)"
echo ""

# 10. Tester la connexion HTTP locale
echo -e "${BLUE}10. Test de connexion HTTP locale:${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:11840/health 2>/dev/null | grep -q "200\|404\|401"; then
    echo -e "${GREEN}✓ Le serveur répond sur localhost:11840${NC}"
else
    echo -e "${RED}✗ Le serveur ne répond pas sur localhost:11840${NC}"
    echo "  Tentative de connexion..."
    curl -v http://localhost:11840/ 2>&1 | head -20 || echo "Erreur de connexion"
fi
echo ""

# 11. Vérifier la configuration docker-compose
echo -e "${BLUE}11. Configuration des ports dans docker-compose.yml:${NC}"
if [ -f "docker-compose.yml" ]; then
    grep -A 5 "ports:" docker-compose.yml | head -10 || echo "Configuration non trouvée"
else
    echo -e "${RED}✗ docker-compose.yml introuvable${NC}"
fi
echo ""

# 12. Vérifier les variables d'environnement
echo -e "${BLUE}12. Variables d'environnement importantes:${NC}"
if [ -f ".env" ]; then
    grep -E "POSTGRES_|DATABASE_URL|CORS_ORIGINS" .env 2>/dev/null | sed 's/\(PASSWORD\|SECRET\)=.*/PASSWORD=***/' || echo "Variables non trouvées"
else
    echo "Fichier .env non trouvé (utilise les valeurs par défaut)"
fi
echo ""

# Résumé et recommandations
echo "=========================================="
echo -e "${BLUE}Résumé et recommandations:${NC}"
echo "=========================================="
echo ""

# Vérifier si les containers sont démarrés
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Les containers ne sont pas démarrés${NC}"
    echo "   Commande: docker compose up -d"
    echo ""
fi

# Vérifier si le port est exposé
if ! docker compose ps | grep -q "11840"; then
    echo -e "${YELLOW}⚠️  Le port 11840 n'est pas exposé${NC}"
    echo "   Vérifiez docker-compose.yml"
    echo ""
fi

# Vérifier si l'API est healthy
if docker compose ps | grep "api" | grep -q "unhealthy"; then
    echo -e "${RED}✗ Le container API est unhealthy${NC}"
    echo "   Consultez les logs: docker compose logs api"
    echo ""
fi

echo -e "${GREEN}Diagnostic terminé${NC}"
echo ""
echo "Commandes utiles:"
echo "  docker compose logs api -f          # Suivre les logs de l'API"
echo "  docker compose ps                    # Voir l'état des containers"
echo "  docker compose restart api          # Redémarrer l'API"
echo "  docker compose up -d --build        # Reconstruire et démarrer"
