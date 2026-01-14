#!/bin/bash
# Script de diagnostic pour vérifier l'accessibilité de l'application

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Fonction pour lire le port configuré
get_app_port() {
    local port=8000  # Port par défaut
    if [ -f "backend/.app_config" ] && grep -q "APP_PORT=" backend/.app_config; then
        port=$(grep "APP_PORT=" backend/.app_config | cut -d= -f2 | tr -d ' ' | tr -d '\r')
    elif [ -f "backend/.env" ] && grep -q "APP_PORT=" backend/.env; then
        port=$(grep "APP_PORT=" backend/.env | cut -d= -f2 | tr -d ' ' | tr -d '\r')
    fi
    echo "$port"
}

APP_PORT=$(get_app_port)

echo "🔍 Diagnostic d'accessibilité de l'application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ℹ️  Port configuré : $APP_PORT"
echo ""

# 1. Vérifier que le processus tourne
echo "1️⃣  Vérification du processus..."
if [ -f "backend/server.pid" ]; then
    PID=$(cat backend/server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "   ✅ Processus actif (PID: $PID)"
    else
        echo "   ❌ Processus arrêté (PID: $PID)"
        echo "   💡 Exécutez: ./start.sh"
        exit 1
    fi
else
    echo "   ❌ Fichier PID introuvable"
    echo "   💡 Exécutez: ./start.sh"
    exit 1
fi
echo ""

# 2. Vérifier que le port est écouté
echo "2️⃣  Vérification du port $APP_PORT..."
PORT_LISTENING=false

if command -v lsof > /dev/null 2>&1; then
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORT_LISTENING=true
        PORT_INFO=$(lsof -Pi :$APP_PORT -sTCP:LISTEN)
        echo "   ✅ Port $APP_PORT écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
elif command -v netstat > /dev/null 2>&1; then
    if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
        PORT_LISTENING=true
        PORT_INFO=$(netstat -tlnp 2>/dev/null | grep ":$APP_PORT ")
        echo "   ✅ Port $APP_PORT écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
elif command -v ss > /dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
        PORT_LISTENING=true
        PORT_INFO=$(ss -tlnp 2>/dev/null | grep ":$APP_PORT ")
        echo "   ✅ Port $APP_PORT écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
fi

if [ "$PORT_LISTENING" = false ]; then
    echo "   ❌ Port $APP_PORT non écouté"
    echo "   💡 Le serveur ne semble pas écouter sur le port $APP_PORT"
    echo "   📋 Vérifiez les logs: tail -f backend/server.log"
    exit 1
fi
echo ""

# 3. Vérifier sur quelle interface le port est écouté
echo "3️⃣  Interface d'écoute..."
if command -v lsof > /dev/null 2>&1; then
    LISTEN_ADDR=$(lsof -Pi :$APP_PORT -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | head -1)
    if echo "$LISTEN_ADDR" | grep -q "0.0.0.0\|::"; then
        echo "   ✅ Port écouté sur toutes les interfaces (0.0.0.0)"
        echo "   ✅ Accessible depuis le réseau"
    elif echo "$LISTEN_ADDR" | grep -q "127.0.0.1"; then
        echo "   ⚠️  Port écouté seulement sur localhost (127.0.0.1)"
        echo "   ❌ NON accessible depuis le réseau"
        echo "   💡 Le serveur doit être démarré avec --host 0.0.0.0"
        echo "   💡 Redémarrez avec: ./stop.sh && ./start.sh"
    else
        echo "   ℹ️  Interface: $LISTEN_ADDR"
    fi
fi
echo ""

# 4. Tester l'accès local
echo "4️⃣  Test d'accès local (localhost)..."
if command -v curl > /dev/null 2>&1; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:$APP_PORT/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "307" ]; then
        echo "   ✅ Serveur répond (code HTTP: $HTTP_CODE)"
    else
        echo "   ❌ Serveur ne répond pas (code HTTP: $HTTP_CODE)"
        echo "   📋 Vérifiez les logs: tail -f backend/server.log"
    fi
elif command -v wget > /dev/null 2>&1; then
    if wget -q --spider --timeout=5 http://localhost:$APP_PORT/ 2>/dev/null; then
        echo "   ✅ Serveur répond"
    else
        echo "   ❌ Serveur ne répond pas"
        echo "   📋 Vérifiez les logs: tail -f backend/server.log"
    fi
else
    echo "   ⚠️  curl ou wget non disponible, test d'accès impossible"
fi
echo ""

# 5. Trouver l'IP de la VM
echo "5️⃣  Adresse IP de la VM..."
IP=""
if command -v hostname > /dev/null 2>&1; then
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
if [ -z "$IP" ]; then
    IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
fi

if [ -n "$IP" ]; then
    echo "   IP trouvée: $IP"
    echo ""
    echo "   📍 URL d'accès depuis le réseau:"
    echo "      http://$IP:$APP_PORT"
    echo ""
    
    # 6. Tester l'accès depuis l'IP
    echo "6️⃣  Test d'accès depuis l'IP ($IP)..."
    if command -v curl > /dev/null 2>&1; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://$IP:$APP_PORT/ 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "307" ]; then
            echo "   ✅ Serveur accessible depuis l'IP (code HTTP: $HTTP_CODE)"
        else
            echo "   ❌ Serveur non accessible depuis l'IP (code HTTP: $HTTP_CODE)"
            echo "   💡 Vérifiez le firewall de la VM"
        fi
    elif command -v wget > /dev/null 2>&1; then
        if wget -q --spider --timeout=5 http://$IP:$APP_PORT/ 2>/dev/null; then
            echo "   ✅ Serveur accessible depuis l'IP"
        else
            echo "   ❌ Serveur non accessible depuis l'IP"
            echo "   💡 Vérifiez le firewall de la VM"
        fi
    else
        echo "   ⚠️  curl ou wget non disponible, test d'accès impossible"
    fi
else
    echo "   ⚠️  Impossible de déterminer l'IP de la VM"
    echo "   💡 Utilisez: hostname -I"
fi
echo ""

# 7. Vérifier le firewall
echo "7️⃣  Vérification du firewall..."
if command -v firewall-cmd > /dev/null 2>&1; then
    if firewall-cmd --list-ports 2>/dev/null | grep -q "$APP_PORT"; then
        echo "   ✅ Port $APP_PORT ouvert dans firewalld"
    else
        echo "   ⚠️  Port $APP_PORT peut-être bloqué par firewalld"
        echo "   💡 Pour ouvrir (nécessite sudo):"
        echo "      sudo firewall-cmd --permanent --add-port=$APP_PORT/tcp"
        echo "      sudo firewall-cmd --reload"
    fi
elif command -v ufw > /dev/null 2>&1; then
    if ufw status 2>/dev/null | grep -q "$APP_PORT"; then
        echo "   ✅ Port $APP_PORT ouvert dans ufw"
    else
        echo "   ⚠️  Port $APP_PORT peut-être bloqué par ufw"
        echo "   💡 Pour ouvrir (nécessite sudo):"
        echo "      sudo ufw allow $APP_PORT/tcp"
    fi
else
    echo "   ℹ️  Aucun firewall détecté (ou nécessite sudo pour vérifier)"
fi
echo ""

# 8. Vérifier si on est dans Docker et proposer remapping
echo "8️⃣  Vérification Docker..."
HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
IN_DOCKER=false

if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null || [[ "$HOSTNAME_FULL" == *"docker"* ]] || [[ "$HOSTNAME_FULL" == *".sdev-docker"* ]]; then
    IN_DOCKER=true
    echo "   ✅ Vous êtes dans un conteneur Docker"
    CONTAINER_NAME=$(hostname)
    echo "   Nom du conteneur: $CONTAINER_NAME"
    echo "   Hostname: $HOSTNAME_FULL"
    echo ""
    echo "   ℹ️  L'application écoute sur le port $APP_PORT dans le conteneur"
    echo "   💡 Assurez-vous que ce port est accessible depuis l'extérieur"
    
    # Si on est dans Docker et que le port n'est pas configuré, proposer de le configurer
    if [ ! -f "backend/.app_config" ]; then
        echo ""
        echo "   ⚠️  Port non configuré (utilise le port par défaut 8000)"
        echo "   💡 Pour configurer le port (ex: 11840), exécutez :"
        echo "      echo 'APP_PORT=11840' > backend/.app_config"
        echo "      ./stop.sh && ./start.sh"
    fi
else
    echo "   ℹ️  Vous n'êtes pas dans un conteneur Docker"
fi
echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RÉSUMÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Détecter le hostname
HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")

# Vérifier si un alias host a été configuré
HOST_ALIAS=""
HOST_ALIAS_IP=""
if [ -f ".host_alias" ]; then
    HOST_ALIAS_LINE=$(cat .host_alias)
    HOST_ALIAS_IP=$(echo "$HOST_ALIAS_LINE" | awk '{print $1}')
    HOST_ALIAS=$(echo "$HOST_ALIAS_LINE" | awk '{print $2}')
fi

if [ -n "$IP" ]; then
    # Priorité : alias configuré > hostname > IP publique > IP locale
    if [ -n "$HOST_ALIAS" ] && [ -n "$HOST_ALIAS_IP" ] && [ "$HOST_ALIAS_IP" = "$IP" ]; then
        URL="http://$HOST_ALIAS:$APP_PORT"
        echo "🌐 URL recommandée (alias configuré) :"
        echo "   $URL"
        echo "   💡 Ajoutez dans /etc/hosts (Linux/Mac) ou C:\\Windows\\System32\\drivers\\etc\\hosts (Windows) :"
        echo "      $HOST_ALIAS_LINE"
        echo ""
    elif [ -n "$HOSTNAME_FULL" ] && [ "$HOSTNAME_FULL" != "localhost" ] && [[ "$HOSTNAME_FULL" != *"docker"* ]]; then
        URL="http://$HOSTNAME_FULL:$APP_PORT"
        echo "🌐 URL recommandée (hostname) :"
        echo "   $URL"
        echo ""
    fi
    
    # Vérifier si on est dans Docker
    if [ "$IN_DOCKER" = true ]; then
        echo "⚠️  Vous êtes dans un conteneur Docker"
        echo "   L'application écoute sur le port $APP_PORT"
        echo "   Utilisez l'IP publique avec le port $APP_PORT :"
        IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || echo "")
        if [ -n "$IP_PUBLIC" ]; then
            echo "   http://$IP_PUBLIC:$APP_PORT"
        else
            echo "   http://IP_PUBLIQUE:$APP_PORT"
        fi
        echo ""
    else
        echo "🌐 URL à utiliser depuis un autre ordinateur sur le même réseau :"
        if [ -n "$HOST_ALIAS" ] && [ -n "$HOST_ALIAS_IP" ] && [ "$HOST_ALIAS_IP" = "$IP" ]; then
            echo "   http://$HOST_ALIAS:$APP_PORT (alias configuré)"
            echo "   💡 N'oubliez pas d'ajouter dans /etc/hosts : $HOST_ALIAS_LINE"
        fi
        if [ -n "$HOSTNAME_FULL" ] && [ "$HOSTNAME_FULL" != "localhost" ]; then
            echo "   http://$HOSTNAME_FULL:$APP_PORT (hostname)"
        fi
        echo "   http://$IP:$APP_PORT (IP locale)"
    fi
    echo ""
    echo "⚠️  Si l'accès ne fonctionne pas :"
    echo "   1. Vérifiez que les deux machines sont sur le même réseau"
    echo "   2. Vérifiez le firewall de la VM (voir ci-dessus)"
    echo "   3. Vérifiez les logs: tail -f backend/server.log"
    echo "   4. Testez depuis la VM: curl http://localhost:$APP_PORT"
else
    echo "⚠️  IP non déterminée. Utilisez: hostname -I"
fi
echo ""

