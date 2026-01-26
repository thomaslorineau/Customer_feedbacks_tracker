#!/bin/bash
# Script pour vérifier l'espace disque et nettoyer si nécessaire

echo "=== Espace disque disponible ==="
df -h

echo ""
echo "=== Taille des volumes Docker ==="
docker system df

echo ""
echo "=== Images Docker ==="
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

echo ""
echo "=== Conteneurs arrêtés ==="
docker ps -a --filter "status=exited" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}"

echo ""
echo "=== Volumes Docker non utilisés ==="
docker volume ls

echo ""
echo "=== Logs Docker (taille) ==="
du -sh /var/lib/docker/containers/* 2>/dev/null | sort -h | tail -10 || echo "Impossible d'accéder aux logs Docker"
