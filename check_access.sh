#!/bin/bash
# Script de diagnostic pour vérifier l'accessibilité de l'application

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo "🔍 Diagnostic d'accessibilité de l'application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
echo "2️⃣  Vérification du port 8000..."
PORT_LISTENING=false

if command -v lsof > /dev/null 2>&1; then
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORT_LISTENING=true
        PORT_INFO=$(lsof -Pi :8000 -sTCP:LISTEN)
        echo "   ✅ Port 8000 écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
elif command -v netstat > /dev/null 2>&1; then
    if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        PORT_LISTENING=true
        PORT_INFO=$(netstat -tlnp 2>/dev/null | grep ":8000 ")
        echo "   ✅ Port 8000 écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
elif command -v ss > /dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
        PORT_LISTENING=true
        PORT_INFO=$(ss -tlnp 2>/dev/null | grep ":8000 ")
        echo "   ✅ Port 8000 écouté"
        echo "   Détails:"
        echo "$PORT_INFO" | sed 's/^/      /'
    fi
fi

if [ "$PORT_LISTENING" = false ]; then
    echo "   ❌ Port 8000 non écouté"
    echo "   💡 Le serveur ne semble pas écouter sur le port 8000"
    echo "   📋 Vérifiez les logs: tail -f backend/server.log"
    exit 1
fi
echo ""

# 3. Vérifier sur quelle interface le port est écouté
echo "3️⃣  Interface d'écoute..."
if command -v lsof > /dev/null 2>&1; then
    LISTEN_ADDR=$(lsof -Pi :8000 -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | head -1)
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
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8000/ 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "307" ]; then
        echo "   ✅ Serveur répond (code HTTP: $HTTP_CODE)"
    else
        echo "   ❌ Serveur ne répond pas (code HTTP: $HTTP_CODE)"
        echo "   📋 Vérifiez les logs: tail -f backend/server.log"
    fi
elif command -v wget > /dev/null 2>&1; then
    if wget -q --spider --timeout=5 http://localhost:8000/ 2>/dev/null; then
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
    echo "      http://$IP:8000"
    echo ""
    
    # 6. Tester l'accès depuis l'IP
    echo "6️⃣  Test d'accès depuis l'IP ($IP)..."
    if command -v curl > /dev/null 2>&1; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://$IP:8000/ 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "307" ]; then
            echo "   ✅ Serveur accessible depuis l'IP (code HTTP: $HTTP_CODE)"
        else
            echo "   ❌ Serveur non accessible depuis l'IP (code HTTP: $HTTP_CODE)"
            echo "   💡 Vérifiez le firewall de la VM"
        fi
    elif command -v wget > /dev/null 2>&1; then
        if wget -q --spider --timeout=5 http://$IP:8000/ 2>/dev/null; then
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
    if firewall-cmd --list-ports 2>/dev/null | grep -q "8000"; then
        echo "   ✅ Port 8000 ouvert dans firewalld"
    else
        echo "   ⚠️  Port 8000 peut-être bloqué par firewalld"
        echo "   💡 Pour ouvrir (nécessite sudo):"
        echo "      sudo firewall-cmd --permanent --add-port=8000/tcp"
        echo "      sudo firewall-cmd --reload"
    fi
elif command -v ufw > /dev/null 2>&1; then
    if ufw status 2>/dev/null | grep -q "8000"; then
        echo "   ✅ Port 8000 ouvert dans ufw"
    else
        echo "   ⚠️  Port 8000 peut-être bloqué par ufw"
        echo "   💡 Pour ouvrir (nécessite sudo):"
        echo "      sudo ufw allow 8000/tcp"
    fi
else
    echo "   ℹ️  Aucun firewall détecté (ou nécessite sudo pour vérifier)"
fi
echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RÉSUMÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ -n "$IP" ]; then
    echo "🌐 URL à utiliser depuis un autre ordinateur sur le même réseau :"
    echo "   http://$IP:8000"
    echo ""
    echo "⚠️  Si l'accès ne fonctionne pas :"
    echo "   1. Vérifiez que les deux machines sont sur le même réseau"
    echo "   2. Vérifiez le firewall de la VM (voir ci-dessus)"
    echo "   3. Vérifiez les logs: tail -f backend/server.log"
    echo "   4. Testez depuis la VM: curl http://localhost:8000"
else
    echo "⚠️  IP non déterminée. Utilisez: hostname -I"
fi
echo ""

