#!/bin/bash
# docker_port_mapping.sh - Helper pour configurer le mapping de port Docker

echo "🐳 Configuration du mapping de port Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Vérifier si on est dans un conteneur Docker
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    echo "✅ Vous êtes dans un conteneur Docker"
    CONTAINER_NAME=$(hostname)
    echo "   Nom du conteneur: $CONTAINER_NAME"
    echo ""
    echo "⚠️  Pour rendre l'application accessible depuis l'extérieur,"
    echo "   le port doit être mappé depuis l'hôte Docker."
    echo ""
    echo "📋 Commandes à exécuter depuis l'HÔTE Docker (pas dans le conteneur) :"
    echo ""
    echo "1. Arrêter le conteneur actuel (si nécessaire) :"
    echo "   docker stop $CONTAINER_NAME"
    echo ""
    echo "2. Démarrer avec mapping de port (remplacez EXTERNAL_PORT par un port disponible, ex: 11840) :"
    echo "   docker run -d -p EXTERNAL_PORT:8000 --name $CONTAINER_NAME [votre-image]"
    echo ""
    echo "   Exemple avec le port 11840 :"
    echo "   docker run -d -p 11840:8000 --name $CONTAINER_NAME [votre-image]"
    echo ""
    echo "3. Ou si le conteneur existe déjà, utilisez docker commit puis recréez :"
    echo "   docker commit $CONTAINER_NAME ovh-tracker:latest"
    echo "   docker stop $CONTAINER_NAME"
    echo "   docker rm $CONTAINER_NAME"
    echo "   docker run -d -p 11840:8000 --name $CONTAINER_NAME ovh-tracker:latest"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 Ports couramment utilisés sur OVH : 11840, 11841, 11842, etc."
    echo "   Vérifiez les ports disponibles avec : docker ps"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "ℹ️  Vous n'êtes pas dans un conteneur Docker"
    echo "   Ce script est destiné à être exécuté dans un conteneur Docker"
fi
echo ""

