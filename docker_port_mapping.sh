#!/bin/bash
# docker_port_mapping.sh - Helper pour configurer le mapping de port Docker

echo "🐳 Configuration du mapping de port Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Détecter l'environnement
IN_CONTAINER=false
ON_DOCKER_HOST=false
CONTAINER_NAME=""
HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")

# Vérifier si on est dans un conteneur Docker
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_CONTAINER=true
    CONTAINER_NAME=$(hostname)
fi

# Vérifier si on est sur un hôte Docker (peut avoir docker command)
if command -v docker > /dev/null 2>&1; then
    ON_DOCKER_HOST=true
fi

# Vérifier aussi par le hostname
if [[ "$HOSTNAME_FULL" == *"docker"* ]] || [[ "$HOSTNAME_FULL" == *".sdev-docker"* ]]; then
    ON_DOCKER_HOST=true
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME=$(hostname)
    fi
fi

if [ "$IN_CONTAINER" = true ]; then
    echo "✅ Vous êtes dans un conteneur Docker"
    echo "   Nom du conteneur: $CONTAINER_NAME"
    echo ""
    echo "⚠️  Pour rendre l'application accessible depuis l'extérieur,"
    echo "   le port doit être mappé depuis l'hôte Docker."
    echo ""
    echo "📋 Commandes à exécuter depuis l'HÔTE Docker :"
    echo ""
    echo "1. Trouver le nom/ID du conteneur :"
    echo "   docker ps"
    echo ""
    echo "2. Arrêter le conteneur actuel :"
    echo "   docker stop $CONTAINER_NAME"
    echo ""
    echo "3. Créer une image du conteneur :"
    echo "   docker commit $CONTAINER_NAME ovh-tracker:latest"
    echo ""
    echo "4. Supprimer l'ancien conteneur :"
    echo "   docker rm $CONTAINER_NAME"
    echo ""
    echo "5. Recréer avec mapping de port (remplacez 11840 par votre port) :"
    echo "   docker run -d -p 11840:8000 --name $CONTAINER_NAME ovh-tracker:latest"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 Ports couramment utilisés sur OVH : 11840, 11841, 11842, etc."
    echo "   Vérifiez les ports disponibles avec : docker ps"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
elif [ "$ON_DOCKER_HOST" = true ]; then
    echo "ℹ️  Vous êtes sur un serveur Docker (hôte ou conteneur)"
    echo "   Hostname: $HOSTNAME_FULL"
    echo ""
    
    # Vérifier si docker est disponible
    if command -v docker > /dev/null 2>&1; then
        echo "✅ Docker est disponible"
        echo ""
        echo "📋 Vérification des conteneurs en cours :"
        echo ""
        docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" 2>/dev/null || echo "   Impossible d'exécuter docker ps"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📋 Pour mapper le port d'un conteneur existant :"
        echo ""
        echo "1. Trouver le conteneur qui exécute l'application :"
        echo "   docker ps"
        echo ""
        echo "2. Arrêter le conteneur :"
        echo "   docker stop [NOM_DU_CONTENEUR]"
        echo ""
        echo "3. Créer une image :"
        echo "   docker commit [NOM_DU_CONTENEUR] ovh-tracker:latest"
        echo ""
        echo "4. Supprimer l'ancien conteneur :"
        echo "   docker rm [NOM_DU_CONTENEUR]"
        echo ""
        echo "5. Recréer avec mapping de port (exemple avec port 11840) :"
        echo "   docker run -d -p 11840:8000 --name [NOM_DU_CONTENEUR] ovh-tracker:latest"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "💡 Ports couramment utilisés sur OVH : 11840, 11841, 11842, etc."
        echo ""
        echo "⚠️  Si l'application tourne directement (pas dans Docker),"
        echo "   vous n'avez pas besoin de mapping de port."
        echo "   Utilisez simplement l'IP ou hostname avec le port 8000."
    else
        echo "⚠️  Docker n'est pas disponible dans ce contexte"
        echo ""
        echo "Si vous êtes dans un conteneur, le mapping doit être configuré"
        echo "depuis l'hôte Docker qui gère ce conteneur."
    fi
else
    echo "ℹ️  Environnement standard (non-Docker détecté)"
    echo ""
    echo "Si vous êtes dans un conteneur Docker mais que la détection a échoué,"
    echo "vous pouvez quand même utiliser ces instructions :"
    echo ""
    echo "📋 Pour mapper le port depuis l'hôte Docker :"
    echo ""
    echo "1. Trouver le conteneur :"
    echo "   docker ps"
    echo ""
    echo "2. Arrêter et recréer avec mapping (exemple port 11840) :"
    echo "   docker stop [NOM_CONTENEUR]"
    echo "   docker commit [NOM_CONTENEUR] ovh-tracker:latest"
    echo "   docker rm [NOM_CONTENEUR]"
    echo "   docker run -d -p 11840:8000 --name [NOM_CONTENEUR] ovh-tracker:latest"
fi
echo ""

