#!/bin/bash
# Script de démarrage de l'application

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Activer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel introuvable. Exécutez d'abord: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# Aller dans le répertoire backend
cd backend

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
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Le port 8000 est déjà utilisé"
        lsof -Pi :8000 -sTCP:LISTEN
        exit 1
    fi
fi

# Démarrer le serveur
echo "🚀 Démarrage du serveur..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
PID=$!
echo $PID > server.pid

# Attendre un peu pour vérifier que le serveur démarre correctement
sleep 2

if ps -p $PID > /dev/null 2>&1; then
    echo "✅ Serveur démarré avec succès (PID: $PID)"
    echo "📋 Logs: tail -f $APP_DIR/backend/server.log"
    
    # Afficher l'IP et le port
    if command -v hostname > /dev/null 2>&1; then
        IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -z "$IP" ]; then
            IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
        fi
        if [ -n "$IP" ]; then
            echo "🌐 Accès: http://$IP:8000"
        fi
    fi
    echo "🌐 Accès local: http://localhost:8000"
    echo "📚 Documentation API: http://localhost:8000/docs"
else
    echo "❌ Échec du démarrage du serveur"
    echo "📋 Vérifiez les logs: tail -f $APP_DIR/backend/server.log"
    rm -f server.pid
    exit 1
fi

