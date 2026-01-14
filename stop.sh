#!/bin/bash
# Script d'arrêt de l'application

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR/backend"

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Arrêt du serveur (PID: $PID)..."
        kill $PID
        
        # Attendre que le processus se termine
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Si le processus est toujours en vie, forcer l'arrêt
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️  Arrêt forcé du processus..."
            kill -9 $PID
        fi
        
        rm server.pid
        echo "✅ Serveur arrêté"
    else
        echo "⚠️  Le serveur ne tourne pas (fichier PID obsolète)"
        rm server.pid
    fi
else
    echo "🔍 Fichier PID introuvable, recherche du processus..."
    # Chercher tous les processus uvicorn pour cette application
    PIDS=$(pgrep -f "uvicorn app.main:app")
    if [ -n "$PIDS" ]; then
        echo "🛑 Arrêt des processus trouvés: $PIDS"
        for PID in $PIDS; do
            kill $PID 2>/dev/null
        done
        sleep 2
        # Forcer l'arrêt si nécessaire
        for PID in $PIDS; do
            if ps -p $PID > /dev/null 2>&1; then
                kill -9 $PID 2>/dev/null
            fi
        done
        echo "✅ Processus arrêtés"
    else
        echo "ℹ️  Aucun processus trouvé"
    fi
fi

