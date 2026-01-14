#!/bin/bash
# Script d'arrêt de l'application

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

# Collecter tous les PIDs à arrêter
PIDS_TO_KILL=""

# 1. Vérifier le fichier PID
if [ -f "backend/server.pid" ]; then
    PID=$(cat backend/server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        PIDS_TO_KILL="$PIDS_TO_KILL $PID"
    else
        rm -f backend/server.pid
    fi
fi

# 2. Chercher par processus uvicorn
PIDS_UVICORN=$(pgrep -f "uvicorn app.main:app" 2>/dev/null || echo "")
if [ -n "$PIDS_UVICORN" ]; then
    for PID in $PIDS_UVICORN; do
        PIDS_TO_KILL="$PIDS_TO_KILL $PID"
    done
fi

# 3. Chercher par port (plus robuste)
if command -v lsof > /dev/null 2>&1; then
    PIDS_PORT=$(lsof -ti :$APP_PORT 2>/dev/null || echo "")
    if [ -n "$PIDS_PORT" ]; then
        for PID in $PIDS_PORT; do
            PIDS_TO_KILL="$PIDS_TO_KILL $PID"
        done
    fi
elif command -v ss > /dev/null 2>&1; then
    PIDS_PORT=$(ss -tlnp 2>/dev/null | grep ":$APP_PORT " | grep -oP 'pid=\K[0-9]+' | sort -u || echo "")
    if [ -n "$PIDS_PORT" ]; then
        for PID in $PIDS_PORT; do
            PIDS_TO_KILL="$PIDS_TO_KILL $PID"
        done
    fi
elif command -v netstat > /dev/null 2>&1; then
    PIDS_PORT=$(netstat -tlnp 2>/dev/null | grep ":$APP_PORT " | grep -oP '[0-9]+/python' | cut -d/ -f1 | sort -u || echo "")
    if [ -n "$PIDS_PORT" ]; then
        for PID in $PIDS_PORT; do
            PIDS_TO_KILL="$PIDS_TO_KILL $PID"
        done
    fi
fi

# 4. Chercher les processus Python dans le répertoire backend
PIDS_PYTHON=$(pgrep -f "python.*app.main" 2>/dev/null || echo "")
if [ -n "$PIDS_PYTHON" ]; then
    for PID in $PIDS_PYTHON; do
        # Vérifier que le processus est bien lié à notre application
        if ps -p $PID -o cmd= 2>/dev/null | grep -q "app.main"; then
            PIDS_TO_KILL="$PIDS_TO_KILL $PID"
        fi
    done
fi

# Nettoyer les doublons et les PIDs invalides
PIDS_TO_KILL=$(echo $PIDS_TO_KILL | tr ' ' '\n' | sort -u | tr '\n' ' ')

if [ -z "$PIDS_TO_KILL" ]; then
    echo "ℹ️  Aucun processus trouvé sur le port $APP_PORT"
    rm -f backend/server.pid
    exit 0
fi

echo "🛑 Arrêt du serveur (port $APP_PORT)..."
echo "   Processus trouvés: $PIDS_TO_KILL"

# Arrêter tous les processus
for PID in $PIDS_TO_KILL; do
    if ps -p $PID > /dev/null 2>&1; then
        echo "   Arrêt du processus $PID..."
        kill $PID 2>/dev/null || true
    fi
done

# Attendre que les processus se terminent
sleep 2

# Forcer l'arrêt si nécessaire
FORCE_KILLED=false
for PID in $PIDS_TO_KILL; do
    if ps -p $PID > /dev/null 2>&1; then
        echo "   ⚠️  Arrêt forcé du processus $PID..."
        kill -9 $PID 2>/dev/null || true
        FORCE_KILLED=true
    fi
done

# Attendre encore un peu si on a dû forcer
if [ "$FORCE_KILLED" = true ]; then
    sleep 1
fi

# Vérifier qu'il ne reste plus de processus
REMAINING_PIDS=""
if command -v lsof > /dev/null 2>&1; then
    REMAINING_PIDS=$(lsof -ti :$APP_PORT 2>/dev/null || echo "")
fi

if [ -n "$REMAINING_PIDS" ]; then
    echo "   ⚠️  Processus restants détectés, arrêt forcé..."
    for PID in $REMAINING_PIDS; do
        kill -9 $PID 2>/dev/null || true
    done
    sleep 1
fi

# Nettoyer le fichier PID
rm -f backend/server.pid

echo "✅ Serveur arrêté"

