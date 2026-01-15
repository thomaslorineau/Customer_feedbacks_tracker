#!/bin/bash
# configure_cors.sh - Configurer CORS pour l'accès réseau
# Ce script détecte automatiquement le hostname et l'IP pour configurer CORS

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR/backend"

echo "🔧 Configuration CORS pour l'accès réseau"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Détecter le hostname
HOSTNAME=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
if [ -z "$HOSTNAME" ] || [ "$HOSTNAME" = "localhost" ]; then
    HOSTNAME=""
fi

# Détecter l'IP locale
IP_LOCAL=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$IP_LOCAL" ]; then
    IP_LOCAL=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
fi

# Détecter l'IP publique (optionnel)
IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || curl -s --max-time 2 ipinfo.io/ip 2>/dev/null || echo "")

# Construire la liste CORS de base
CORS_ORIGINS="http://localhost:8000,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8000,http://127.0.0.1:3000"

# Ajouter le hostname si disponible
if [ -n "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$HOSTNAME:8000,http://$HOSTNAME:3000"
    echo "✅ Hostname détecté: $HOSTNAME"
fi

# Ajouter l'IP locale si disponible
if [ -n "$IP_LOCAL" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$IP_LOCAL:8000"
    echo "✅ IP locale détectée: $IP_LOCAL"
fi

# Ajouter l'IP publique si disponible
if [ -n "$IP_PUBLIC" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$IP_PUBLIC:8000"
    echo "✅ IP publique détectée: $IP_PUBLIC"
fi

echo ""

# Sauvegarder l'ancien .env s'il existe
if [ -f ".env" ]; then
    echo "📋 Sauvegarde de l'ancien fichier .env..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Créer le fichier .env
cat > .env << EOF
# Configuration CORS - Autoriser l'accès depuis le réseau local
# Généré automatiquement par configure_cors.sh
CORS_ORIGINS=$CORS_ORIGINS

# Configuration LLM (optionnel - l'application fonctionne sans)
# Décommentez et remplissez si vous avez une clé API
# OPENAI_API_KEY=votre_cle_api_openai
# OPENAI_MODEL=gpt-4o-mini

# Ou utiliser Anthropic
# ANTHROPIC_API_KEY=votre_cle_api_anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_MODEL=claude-3-haiku-20240307
EOF

echo "✅ Configuration CORS mise à jour dans backend/.env"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Origines CORS configurées :"
echo "$CORS_ORIGINS" | tr ',' '\n' | sed 's/^/   /'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Déterminer l'URL à utiliser
if [ -n "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ]; then
    URL="http://$HOSTNAME:8000"
elif [ -n "$IP_PUBLIC" ]; then
    URL="http://$IP_PUBLIC:8000"
elif [ -n "$IP_LOCAL" ]; then
    URL="http://$IP_LOCAL:8000"
else
    URL="http://localhost:8000"
fi

echo "🌐 URL recommandée pour accès réseau :"
echo "   $URL"
echo ""
echo "⚠️  Important : Redémarrez l'application pour appliquer les changements :"
echo "   cd $APP_DIR"
echo "   ./stop.sh"
echo "   ./start.sh"
echo ""


