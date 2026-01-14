#!/bin/bash
# Script de vérification du statut

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR/backend"

echo "📊 Statut de l'application OVH Customer Feedback Tracker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Vérifier le fichier PID
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Serveur en cours d'exécution"
        echo "   PID: $PID"
        
        # Afficher les informations du processus
        if command -v ps > /dev/null 2>&1; then
            echo "   Processus:"
            ps -p $PID -o pid,user,cmd --no-headers | sed 's/^/   /'
        fi
        
        # Vérifier le port
        if command -v lsof > /dev/null 2>&1; then
            PORT_INFO=$(lsof -Pi :8000 -sTCP:LISTEN 2>/dev/null)
            if [ -n "$PORT_INFO" ]; then
                echo "   Port 8000: Écouté"
            fi
        elif command -v netstat > /dev/null 2>&1; then
            if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
                echo "   Port 8000: Écouté"
            fi
        elif command -v ss > /dev/null 2>&1; then
            if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
                echo "   Port 8000: Écouté"
            fi
        fi
        
        # Afficher l'IP
        if command -v hostname > /dev/null 2>&1; then
            IP=$(hostname -I 2>/dev/null | awk '{print $1}')
            if [ -z "$IP" ]; then
                IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
            fi
            if [ -n "$IP" ]; then
                echo "   Accès réseau: http://$IP:8000"
            fi
        fi
        echo "   Accès local: http://localhost:8000"
        echo "   Documentation: http://localhost:8000/docs"
        
        # Afficher la taille des logs
        if [ -f server.log ]; then
            LOG_SIZE=$(du -h server.log 2>/dev/null | cut -f1)
            echo "   Logs: $APP_DIR/backend/server.log ($LOG_SIZE)"
        fi
        
    else
        echo "❌ Serveur arrêté (fichier PID existe mais processus mort)"
        echo "   Nettoyage du fichier PID obsolète..."
        rm server.pid
    fi
else
    # Chercher le processus sans fichier PID
    PIDS=$(pgrep -f "uvicorn app.main:app")
    if [ -n "$PIDS" ]; then
        echo "⚠️  Serveur en cours d'exécution mais fichier PID manquant"
        echo "   PIDs trouvés: $PIDS"
        for PID in $PIDS; do
            if ps -p $PID > /dev/null 2>&1; then
                ps -p $PID -o pid,user,cmd --no-headers | sed 's/^/   /'
            fi
        done
    else
        echo "❌ Serveur arrêté"
    fi
fi

echo ""
echo "📋 Commandes utiles:"
echo "   Démarrage:  ./start.sh"
echo "   Arrêt:      ./stop.sh"
echo "   Statut:     ./status.sh"
echo "   Logs:       tail -f $APP_DIR/backend/server.log"

