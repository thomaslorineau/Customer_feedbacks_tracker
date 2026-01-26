#!/bin/bash
# Script pour nettoyer l'espace disque Docker

set -e

echo "=== Nettoyage de l'espace disque Docker ==="

echo "1. Arrêt des conteneurs..."
docker compose down || true

echo "2. Suppression des conteneurs arrêtés..."
docker container prune -f

echo "3. Suppression des images non utilisées..."
docker image prune -a -f

echo "4. Suppression des volumes non utilisés..."
docker volume prune -f

echo "5. Nettoyage système Docker (cache, réseaux, etc.)..."
docker system prune -a -f --volumes

echo "6. Nettoyage des logs Docker (si possible)..."
# Limiter la taille des logs pour les conteneurs existants
docker ps -q | xargs -r docker inspect --format='{{.LogPath}}' 2>/dev/null | xargs -r sudo truncate -s 0 2>/dev/null || echo "Impossible de nettoyer les logs (besoin de sudo)"

echo ""
echo "=== Espace disque après nettoyage ==="
df -h
docker system df

echo ""
echo "Nettoyage terminé !"
