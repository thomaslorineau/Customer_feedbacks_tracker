#!/bin/bash
# Script de démarrage de l'application

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Vérifier que l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel introuvable. Exécutez d'abord: python3 -m venv venv"
    exit 1
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
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Le port 8000 est déjà utilisé"
        lsof -Pi :8000 -sTCP:LISTEN
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
    setsid bash -c "cd '$APP_DIR/backend' && source '$APP_DIR/venv/bin/activate' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus du shell actuel avec disown si disponible
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
else
    # Alternative avec nohup et redirection complète
    # Utiliser bash -c pour s'assurer que l'environnement virtuel est activé
    # exec remplace le processus bash par python, évitant les problèmes de signal
    nohup bash -c "cd '$APP_DIR/backend' && source '$APP_DIR/venv/bin/activate' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
fi

echo $PID > "$APP_DIR/backend/server.pid"

# Attendre un peu pour vérifier que le serveur démarre correctement
sleep 3

# Vérifier que le processus tourne toujours
if ps -p $PID > /dev/null 2>&1; then
    # Vérifier aussi que le port est bien écouté
    sleep 1
    if command -v lsof > /dev/null 2>&1; then
        if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "⚠️  Le processus démarre mais le port n'est pas encore écouté, attente..."
            sleep 2
        fi
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
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 ACCÈS À L'APPLICATION"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "📍 Depuis cette VM :"
        echo "   http://localhost:8000"
        echo ""
        if [ -n "$IP" ]; then
            echo "📍 Depuis un autre ordinateur sur le même réseau :"
            echo "   http://$IP:8000"
            echo ""
            echo "💡 Partagez cette URL avec vos collègues :"
            echo "   http://$IP:8000"
        else
            echo "📍 Pour accéder depuis le réseau, trouvez l'IP avec :"
            echo "   hostname -I"
        fi
        echo ""
        echo "📚 Documentation API : http://localhost:8000/docs"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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

