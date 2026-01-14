#!/bin/bash
# Script de démarrage de l'application

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

# Vérifier que l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel introuvable. Exécutez d'abord: python3 -m venv venv"
    exit 1
fi

# Vérifier la configuration CORS
if [ ! -f "backend/.env" ]; then
    echo "⚠️  Fichier .env introuvable. Configuration CORS automatique..."
    if [ -f "configure_cors.sh" ]; then
        ./configure_cors.sh
    else
        echo "⚠️  Script configure_cors.sh non trouvé"
        echo "   Créez backend/.env manuellement avec CORS_ORIGINS"
    fi
fi

# Vérifier si le serveur tourne déjà
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Le serveur tourne déjà (PID: $PID)"
        echo "Pour redémarrer, exécutez d'abord: ./stop.sh"
        exit 1
    else
        # Nettoyer le fichier PID obsolète
        rm server.pid
    fi
fi

# Vérifier si un autre processus utilise le port
if command -v lsof > /dev/null 2>&1; then
    if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Le port $APP_PORT est déjà utilisé"
        lsof -Pi :$APP_PORT -sTCP:LISTEN
        exit 1
    fi
fi

# Démarrer le serveur en arrière-plan
echo "🚀 Démarrage du serveur..."

# Créer le répertoire backend si nécessaire
mkdir -p "$APP_DIR/backend"

# Utiliser setsid pour créer un nouveau groupe de processus et détacher du terminal
# Si setsid n'est pas disponible, utiliser nohup avec redirection complète
if command -v setsid > /dev/null 2>&1; then
    # setsid crée un nouveau groupe de processus, détachant complètement du terminal
    # Utiliser bash -c pour s'assurer que l'environnement virtuel est activé dans le sous-processus
    setsid bash -c "cd '$APP_DIR/backend' && source '$APP_DIR/venv/bin/activate' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus du shell actuel avec disown si disponible
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
else
    # Alternative avec nohup et redirection complète
    # Utiliser bash -c pour s'assurer que l'environnement virtuel est activé
    # exec remplace le processus bash par python, évitant les problèmes de signal
    nohup bash -c "cd '$APP_DIR/backend' && source '$APP_DIR/venv/bin/activate' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
fi

echo $PID > "$APP_DIR/backend/server.pid"

# Attendre un peu pour vérifier que le serveur démarre correctement
echo "⏳ Attente du démarrage du serveur..."
for i in {1..10}; do
    sleep 1
    if ps -p $PID > /dev/null 2>&1; then
        # Vérifier que le port est écouté
        if command -v lsof > /dev/null 2>&1; then
            if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
                # Vérifier que c'est bien sur 0.0.0.0
                LISTEN_ADDR=$(lsof -Pi :$APP_PORT -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | head -1)
                if echo "$LISTEN_ADDR" | grep -q "0.0.0.0\|::"; then
                    break
                fi
            fi
        elif command -v netstat > /dev/null 2>&1; then
            if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
                break
            fi
        elif command -v ss > /dev/null 2>&1; then
            if ss -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
                break
            fi
        fi
    else
        echo "❌ Le processus s'est arrêté immédiatement"
        echo "📋 Vérifiez les logs: tail -20 $APP_DIR/backend/server.log"
        rm -f "$APP_DIR/backend/server.pid"
        exit 1
    fi
    echo -n "."
done
echo ""

# Vérifier que le processus tourne toujours
if ps -p $PID > /dev/null 2>&1; then
    # Vérifier que le port est bien écouté sur 0.0.0.0
    PORT_OK=false
    if command -v lsof > /dev/null 2>&1; then
        LISTEN_ADDR=$(lsof -Pi :$APP_PORT -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | head -1)
        if echo "$LISTEN_ADDR" | grep -q "0.0.0.0\|::"; then
            PORT_OK=true
        elif echo "$LISTEN_ADDR" | grep -q "127.0.0.1"; then
            echo "⚠️  ATTENTION: Le serveur écoute seulement sur localhost (127.0.0.1)"
            echo "   Il ne sera PAS accessible depuis le réseau"
            echo "   Le serveur devrait écouter sur 0.0.0.0"
        fi
    else
        # Si lsof n'est pas disponible, on suppose que c'est OK
        PORT_OK=true
    fi
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Serveur démarré avec succès (PID: $PID)"
        echo "📋 Logs: tail -f $APP_DIR/backend/server.log"
        echo ""
        
        # Afficher l'IP et le port
        IP=""
        if command -v hostname > /dev/null 2>&1; then
            IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        fi
        if [ -z "$IP" ]; then
            IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
        fi
        
        # Vérifier si un alias host a été configuré
        HOST_ALIAS=""
        HOST_ALIAS_IP=""
        HOST_ALIAS_LINE=""
        if [ -f "$APP_DIR/.host_alias" ]; then
            HOST_ALIAS_LINE=$(cat "$APP_DIR/.host_alias")
            HOST_ALIAS_IP=$(echo "$HOST_ALIAS_LINE" | awk '{print $1}')
            HOST_ALIAS=$(echo "$HOST_ALIAS_LINE" | awk '{print $2}')
        fi
        
        # Détecter le hostname
        HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 ACCÈS À L'APPLICATION"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "📍 Depuis cette VM :"
        echo "   http://localhost:$APP_PORT"
        echo ""
        
        # Priorité : alias configuré > hostname > IP
        if [ -n "$HOST_ALIAS" ] && [ -n "$HOST_ALIAS_IP" ] && [ "$HOST_ALIAS_IP" = "$IP" ]; then
            echo "📍 Depuis un autre ordinateur sur le même réseau local (alias) :"
            echo "   http://$HOST_ALIAS:$APP_PORT"
            echo ""
            echo "💡 Partagez cette URL avec vos collègues :"
            echo "   http://$HOST_ALIAS:$APP_PORT"
            echo ""
            echo "⚠️  Important : Vos collègues doivent ajouter dans /etc/hosts (Linux/Mac) ou"
            echo "   C:\\Windows\\System32\\drivers\\etc\\hosts (Windows) :"
            echo "   $HOST_ALIAS_LINE"
        elif [ -n "$HOSTNAME_FULL" ] && [ "$HOSTNAME_FULL" != "localhost" ] && [[ "$HOSTNAME_FULL" != *"docker"* ]]; then
            echo "📍 Depuis un autre ordinateur sur le même réseau local (hostname) :"
            echo "   http://$HOSTNAME_FULL:$APP_PORT"
            echo ""
            echo "💡 Partagez cette URL avec vos collègues :"
            echo "   http://$HOSTNAME_FULL:$APP_PORT"
        elif [ -n "$IP" ]; then
            echo "📍 Depuis un autre ordinateur sur le même réseau local :"
            echo "   http://$IP:$APP_PORT"
            echo ""
            echo "💡 Partagez cette URL avec vos collègues :"
            echo "   http://$IP:$APP_PORT"
        else
            echo "📍 Pour accéder depuis le réseau, trouvez l'IP avec :"
            echo "   hostname -I"
        fi
        echo ""
        echo "📚 Documentation API : http://localhost:$APP_PORT/docs"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "⚠️  Si l'accès ne fonctionne pas depuis un autre ordinateur :"
        echo "   1. Vérifiez que les deux machines sont sur le même réseau"
        echo "   2. Vérifiez le firewall de la VM"
        echo "   3. Exécutez le diagnostic: ./check_access.sh"
        echo "   4. Vérifiez les logs: tail -f $APP_DIR/backend/server.log"
    else
        echo "❌ Le processus s'est arrêté immédiatement"
        echo "📋 Vérifiez les logs: tail -f $APP_DIR/backend/server.log"
        rm -f server.pid
        exit 1
    fi
else
    echo "❌ Échec du démarrage du serveur"
    echo "📋 Vérifiez les logs: tail -f $APP_DIR/backend/server.log"
    rm -f server.pid
    exit 1
fi

