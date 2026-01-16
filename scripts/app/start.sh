#!/bin/bash
# Script de démarrage de l'application

# Obtenir le répertoire du script (scripts/app/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Remonter à la racine du projet (2 niveaux: scripts/app -> scripts -> racine)
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_DIR"

# S'assurer que tous les scripts sont exécutables
find . -maxdepth 1 -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# Fonction pour obtenir le hostname depuis une IP (reverse DNS)
get_hostname_from_ip() {
    local ip=$1
    local hostname=""
    
    # Essayer différentes méthodes de reverse DNS
    if command -v host > /dev/null 2>&1; then
        hostname=$(host "$ip" 2>/dev/null | grep "domain name pointer" | awk '{print $5}' | sed 's/\.$//' || echo "")
    elif command -v nslookup > /dev/null 2>&1; then
        hostname=$(nslookup "$ip" 2>/dev/null | grep "name" | awk '{print $4}' | head -1 || echo "")
    elif command -v dig > /dev/null 2>&1; then
        hostname=$(dig +short -x "$ip" 2>/dev/null | sed 's/\.$//' || echo "")
    fi
    
    echo "$hostname"
}

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
    if [ -f "scripts/install/configure_cors.sh" ]; then
        bash scripts/install/configure_cors.sh
    elif [ -f "configure_cors.sh" ]; then
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
        echo "Pour redémarrer, exécutez d'abord: bash scripts/start/stop.sh ou ./stop.sh"
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

# Vérifications préalables avant démarrage
echo "🔍 Vérifications préalables..."
echo "   APP_DIR: $APP_DIR"
echo "   APP_PORT: $APP_PORT"
echo "   Venv: $APP_DIR/venv"

# Vérifier que l'environnement virtuel existe et est valide
if [ ! -f "$APP_DIR/venv/bin/activate" ]; then
    echo "❌ Erreur: Environnement virtuel invalide"
    echo "   Fichier manquant: $APP_DIR/venv/bin/activate"
    echo "   Exécutez: python3 -m venv venv"
    exit 1
fi

# Vérifier que Python est disponible dans le venv
if [ ! -f "$APP_DIR/venv/bin/python" ]; then
    echo "❌ Erreur: Python non trouvé dans l'environnement virtuel"
    echo "   Fichier manquant: $APP_DIR/venv/bin/python"
    exit 1
fi

# Vérifier que uvicorn est installé
if ! "$APP_DIR/venv/bin/python" -c "import uvicorn" 2>/dev/null; then
    echo "❌ Erreur: uvicorn n'est pas installé"
    echo "   Installez avec: source venv/bin/activate && pip install uvicorn"
    exit 1
fi

# Vérifier que le module app.main existe
if [ ! -f "$APP_DIR/backend/app/main.py" ]; then
    echo "❌ Erreur: Module app.main introuvable"
    echo "   Fichier manquant: $APP_DIR/backend/app/main.py"
    exit 1
fi

echo "✅ Vérifications OK"
echo ""

# Démarrer le serveur en arrière-plan
echo "🚀 Démarrage du serveur..."
echo "   Commande: cd $APP_DIR/backend && source $APP_DIR/venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT"
echo "   Logs: $APP_DIR/backend/server.log"
echo ""

# Créer le répertoire backend si nécessaire
mkdir -p "$APP_DIR/backend"

# Créer le fichier de log s'il n'existe pas
touch "$APP_DIR/backend/server.log"

# Utiliser setsid pour créer un nouveau groupe de processus et détacher du terminal
# Si setsid n'est pas disponible, utiliser nohup avec redirection complète
START_CMD="cd '$APP_DIR/backend' && source '$APP_DIR/venv/bin/activate' && exec python -m uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT"

if command -v setsid > /dev/null 2>&1; then
    # setsid crée un nouveau groupe de processus, détachant complètement du terminal
    # Utiliser bash -c pour s'assurer que l'environnement virtuel est activé dans le sous-processus
    setsid bash -c "$START_CMD" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus du shell actuel avec disown si disponible
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
else
    # Alternative avec nohup et redirection complète
    # Utiliser bash -c pour s'assurer que l'environnement virtuel est activé
    # exec remplace le processus bash par python, évitant les problèmes de signal
    nohup bash -c "$START_CMD" > "$APP_DIR/backend/server.log" 2>&1 < /dev/null &
    PID=$!
    # Détacher le processus
    if command -v disown > /dev/null 2>&1; then
        disown $PID 2>/dev/null || true
    fi
fi

echo "   PID: $PID"
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
        echo ""
        echo "❌ Le processus s'est arrêté immédiatement (PID: $PID)"
        echo ""
        echo "🔍 Diagnostic détaillé:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Vérifier le code de sortie si disponible
        wait $PID 2>/dev/null
        EXIT_CODE=$?
        echo "   Code de sortie: $EXIT_CODE"
        
        # Afficher les dernières lignes des logs
        if [ -f "$APP_DIR/backend/server.log" ]; then
            LOG_SIZE=$(wc -l < "$APP_DIR/backend/server.log" 2>/dev/null || echo "0")
            if [ "$LOG_SIZE" -gt 0 ]; then
                echo ""
                echo "   📋 Dernières lignes des logs ($APP_DIR/backend/server.log):"
                echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                tail -30 "$APP_DIR/backend/server.log" | sed 's/^/   /'
                echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            else
                echo "   ⚠️  Le fichier de log est vide"
            fi
        else
            echo "   ⚠️  Fichier de log introuvable: $APP_DIR/backend/server.log"
        fi
        
        # Vérifications supplémentaires
        echo ""
        echo "   🔍 Vérifications supplémentaires:"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Vérifier Python
        if [ -f "$APP_DIR/venv/bin/python" ]; then
            PYTHON_VERSION=$("$APP_DIR/venv/bin/python" --version 2>&1)
            echo "   ✅ Python: $PYTHON_VERSION"
        else
            echo "   ❌ Python: introuvable dans $APP_DIR/venv/bin/python"
        fi
        
        # Vérifier uvicorn
        if "$APP_DIR/venv/bin/python" -c "import uvicorn" 2>/dev/null; then
            UVICORN_VERSION=$("$APP_DIR/venv/bin/python" -c "import uvicorn; print(uvicorn.__version__)" 2>/dev/null || echo "inconnue")
            echo "   ✅ uvicorn: $UVICORN_VERSION"
        else
            echo "   ❌ uvicorn: non installé"
        fi
        
        # Vérifier le module app
        if [ -f "$APP_DIR/backend/app/main.py" ]; then
            echo "   ✅ Module app.main: trouvé"
        else
            echo "   ❌ Module app.main: introuvable ($APP_DIR/backend/app/main.py)"
        fi
        
        # Vérifier les variables d'environnement
        echo ""
        echo "   📋 Variables d'environnement:"
        echo "      ENVIRONMENT: ${ENVIRONMENT:-non défini}"
        echo "      USE_DUCKDB: ${USE_DUCKDB:-non défini}"
        echo "      APP_PORT: ${APP_PORT:-non défini}"
        
        # Tester la commande manuellement
        echo ""
        echo "   💡 Pour tester manuellement, exécutez:"
        echo "      cd $APP_DIR/backend"
        echo "      source $APP_DIR/venv/bin/activate"
        echo "      python -m uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT"
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
            echo "📍 Depuis un autre ordinateur sur le RÉSEAU LOCAL (alias) :"
            echo "   http://$HOST_ALIAS:$APP_PORT"
            echo ""
            echo "   ⚠️  IMPORTANT : L'alias fonctionne UNIQUEMENT pour l'IP locale ($IP)"
            echo "   Vos collègues doivent ajouter dans /etc/hosts (Linux/Mac) ou"
            echo "   C:\\Windows\\System32\\drivers\\etc\\hosts (Windows) :"
            echo "   $HOST_ALIAS_LINE"
            echo ""
            # Afficher aussi l'IP publique si disponible
            IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || echo "")
            if [ -n "$IP_PUBLIC" ]; then
                HOSTNAME_PUBLIC=$(get_hostname_from_ip "$IP_PUBLIC")
                if [ -n "$HOSTNAME_PUBLIC" ] && [ "$HOSTNAME_PUBLIC" != "$IP_PUBLIC" ]; then
                    echo "📍 Depuis Internet (HOSTNAME) :"
                    echo "   http://$HOSTNAME_PUBLIC:$APP_PORT"
                    echo ""
                    echo "   Ou directement par IP :"
                    echo "   http://$IP_PUBLIC:$APP_PORT"
                    echo ""
                    echo "💡 URL à partager pour accès Internet :"
                    echo "   http://$HOSTNAME_PUBLIC:$APP_PORT"
                else
                    echo "📍 Depuis Internet (IP PUBLIQUE - pas d'alias possible) :"
                    echo "   http://$IP_PUBLIC:$APP_PORT"
                    echo ""
                    echo "💡 URL à partager pour accès Internet :"
                    echo "   http://$IP_PUBLIC:$APP_PORT"
                fi
            fi
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
        echo "   3. Exécutez le diagnostic: bash scripts/install/check_access.sh"
        echo "   4. Vérifiez les logs: tail -f $APP_DIR/backend/server.log"
    else
        echo ""
        echo "❌ Le processus s'est arrêté après le démarrage (PID: $PID)"
        echo ""
        echo "🔍 Diagnostic détaillé:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Afficher les dernières lignes des logs
        if [ -f "$APP_DIR/backend/server.log" ]; then
            LOG_SIZE=$(wc -l < "$APP_DIR/backend/server.log" 2>/dev/null || echo "0")
            if [ "$LOG_SIZE" -gt 0 ]; then
                echo "   📋 Dernières lignes des logs:"
                echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                tail -30 "$APP_DIR/backend/server.log" | sed 's/^/   /'
                echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            else
                echo "   ⚠️  Le fichier de log est vide"
            fi
        else
            echo "   ⚠️  Fichier de log introuvable"
        fi
        
        echo ""
        echo "   💡 Pour voir les logs en temps réel:"
        echo "      tail -f $APP_DIR/backend/server.log"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        rm -f "$APP_DIR/backend/server.pid"
        exit 1
    fi
else
    echo ""
    echo "❌ Échec du démarrage du serveur (processus non trouvé)"
    echo ""
    echo "🔍 Diagnostic détaillé:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Afficher les dernières lignes des logs
    if [ -f "$APP_DIR/backend/server.log" ]; then
        LOG_SIZE=$(wc -l < "$APP_DIR/backend/server.log" 2>/dev/null || echo "0")
        if [ "$LOG_SIZE" -gt 0 ]; then
            echo "   📋 Dernières lignes des logs:"
            echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            tail -30 "$APP_DIR/backend/server.log" | sed 's/^/   /'
            echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        else
            echo "   ⚠️  Le fichier de log est vide"
        fi
    else
        echo "   ⚠️  Fichier de log introuvable: $APP_DIR/backend/server.log"
    fi
    
    echo ""
    echo "   💡 Pour voir les logs en temps réel:"
    echo "      tail -f $APP_DIR/backend/server.log"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    rm -f "$APP_DIR/backend/server.pid"
    exit 1
fi

