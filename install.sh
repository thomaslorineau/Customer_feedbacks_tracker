#!/bin/bash
# Script d'installation automatique pour OVH Customer Feedback Tracker
# Usage: ./install.sh

set -e  # Arrêter en cas d'erreur

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# En-tête
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Installation de OVH Customer Feedback Tracker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Étape 1 : Vérifier les prérequis
info "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    error "Python 3 n'est pas installé."
    echo "   Veuillez contacter votre administrateur système pour installer Python 3.11 ou 3.12"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    error "Python 3.11 ou 3.12 est requis. Version trouvée: $PYTHON_VERSION"
    echo "   Veuillez contacter votre administrateur système pour installer Python 3.11 ou 3.12"
    exit 1
fi

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -eq 13 ]; then
    warning "Python 3.13 peut avoir des problèmes de compatibilité. Python 3.11 ou 3.12 est recommandé."
fi

success "Python $PYTHON_VERSION trouvé"

# Vérifier Git
if ! command -v git &> /dev/null; then
    error "Git n'est pas installé."
    echo "   Veuillez contacter votre administrateur système pour installer Git"
    exit 1
fi

success "Git $(git --version | awk '{print $3}') trouvé"

# Vérifier pip
if ! python3 -m pip --version &> /dev/null; then
    error "pip n'est pas disponible."
    echo "   Veuillez contacter votre administrateur système pour installer pip"
    exit 1
fi

success "pip disponible"

echo ""

# Étape 2 : Déterminer le répertoire d'installation
info "Détermination du répertoire d'installation..."

# Si le script est dans le dépôt cloné, installer dans le répertoire parent
if [ -f "backend/requirements.txt" ]; then
    INSTALL_DIR=$(pwd)
    info "Installation dans le répertoire actuel: $INSTALL_DIR"
else
    # Sinon, installer dans ~/apps/complaints_tracker
    INSTALL_DIR="$HOME/apps/complaints_tracker"
    info "Installation dans: $INSTALL_DIR"
    
    # Créer le répertoire si nécessaire
    mkdir -p "$HOME/apps"
    
    # Si le répertoire existe déjà, demander confirmation
    if [ -d "$INSTALL_DIR" ]; then
        warning "Le répertoire $INSTALL_DIR existe déjà."
        read -p "Voulez-vous continuer ? Cela peut écraser des fichiers existants. (o/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Oo]$ ]]; then
            info "Installation annulée."
            exit 0
        fi
    fi
fi

echo ""

# Étape 3 : Cloner le dépôt (si nécessaire)
if [ ! -f "backend/requirements.txt" ]; then
    info "Téléchargement de l'application depuis GitHub..."
    
    if [ -d "$INSTALL_DIR" ]; then
        warning "Le répertoire $INSTALL_DIR existe déjà. Suppression..."
        rm -rf "$INSTALL_DIR"
    fi
    
    git clone https://github.com/thomaslorineau/complaints_tracker.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    success "Application téléchargée"
else
    cd "$INSTALL_DIR"
    info "Utilisation du répertoire existant: $INSTALL_DIR"
fi

echo ""

# Étape 4 : Créer l'environnement virtuel
info "Création de l'environnement virtuel Python..."

if [ -d "venv" ]; then
    warning "L'environnement virtuel existe déjà. Voulez-vous le recréer ?"
    read -p "Cela supprimera l'ancien environnement. (o/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        info "Suppression de l'ancien environnement virtuel..."
        rm -rf venv
        python3 -m venv venv
        success "Environnement virtuel recréé"
    else
        info "Utilisation de l'environnement virtuel existant"
    fi
else
    python3 -m venv venv
    success "Environnement virtuel créé"
fi

echo ""

# Étape 5 : Activer l'environnement et installer les dépendances
info "Installation des dépendances Python (cela peut prendre quelques minutes)..."

source venv/bin/activate

# Mettre à jour pip
info "Mise à jour de pip..."
python -m pip install --upgrade pip --quiet

# Installer les dépendances
info "Installation des packages requis..."
cd backend
python -m pip install -r requirements.txt

success "Dépendances installées"
echo ""

# Étape 6 : Rendre les scripts exécutables
info "Configuration des scripts de gestion..."

cd ..
# Rendre tous les scripts exécutables
info "Configuration des permissions des scripts..."
chmod +x start.sh stop.sh status.sh backup.sh check_access.sh configure_cors.sh update.sh install.sh 2>/dev/null || true

# Rendre aussi exécutables tous les scripts .sh dans le répertoire
find . -maxdepth 1 -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

success "Scripts configurés"
echo ""

# Étape 6b : Vérifier si on est dans Docker
info "Vérification de l'environnement Docker..."

IN_DOCKER=false
HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")

# Détection Docker améliorée : /.dockerenv, cgroup, ou hostname contenant "docker"
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null || [[ "$HOSTNAME_FULL" == *"docker"* ]] || [[ "$HOSTNAME_FULL" == *".sdev-docker"* ]]; then
    IN_DOCKER=true
    CONTAINER_NAME=$(hostname)
    success "Détecté : Environnement Docker"
    echo "   Hostname: $HOSTNAME_FULL"
    echo "   Conteneur: $CONTAINER_NAME"
    echo ""
    warning "⚠️  IMPORTANT : Configuration du port d'écoute"
    echo ""
    echo "Sur les serveurs Docker OVH, l'application doit écouter directement sur"
    echo "le port externe accessible (ex: 11840) plutôt que sur le port 8000."
    echo ""
    read -p "Port à utiliser (ex: 11840, laissez vide pour 8000 par défaut) : " EXTERNAL_PORT
    echo ""
    
    if [ -n "$EXTERNAL_PORT" ]; then
        info "Port configuré : $EXTERNAL_PORT"
        echo "APP_PORT=$EXTERNAL_PORT" > backend/.app_config
        success "Configuration sauvegardée dans backend/.app_config"
        echo ""
        info "L'application écoutera sur le port $EXTERNAL_PORT"
        echo "Redémarrez avec : ./stop.sh && ./start.sh"
    else
        info "Port par défaut 8000 conservé (pour développement local)"
        echo "APP_PORT=8000" > backend/.app_config
    fi
    echo ""
else
    info "Environnement standard (non-Docker détecté)"
fi

# Étape 6c : Proposer un alias host
info "Configuration d'un alias host (optionnel)..."

read -p "Souhaitez-vous configurer un alias host pour l'accès ? (o/N) : " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    read -p "Nom d'alias souhaité (ex: ovh-tracker) : " HOST_ALIAS
    if [ -n "$HOST_ALIAS" ]; then
        # Détecter l'IP
        VM_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -z "$VM_IP" ]; then
            VM_IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1)
        fi
        
        if [ -n "$VM_IP" ]; then
            echo "$VM_IP    $HOST_ALIAS.local" > .host_alias
            success "Alias configuré : $HOST_ALIAS.local -> $VM_IP"
            echo ""
            warning "⚠️  IMPORTANT : L'alias host fonctionne UNIQUEMENT pour l'IP locale ($VM_IP)"
            echo "   Il ne fonctionne PAS pour l'IP publique."
            echo ""
            info "Pour utiliser cet alias sur votre machine locale, ajoutez dans"
            echo "/etc/hosts (Linux/Mac) ou C:\\Windows\\System32\\drivers\\etc\\hosts (Windows) :"
            echo "   $VM_IP    $HOST_ALIAS.local"
            echo ""
            echo "Puis accédez à : http://$HOST_ALIAS.local:$APP_PORT"
            echo ""
            info "Pour l'accès depuis Internet (IP publique), utilisez directement :"
            IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || echo "")
            if [ -n "$IP_PUBLIC" ]; then
                echo "   http://$IP_PUBLIC:$APP_PORT"
            else
                echo "   http://IP_PUBLIQUE:$APP_PORT"
            fi
        else
            warning "Impossible de déterminer l'IP, alias non configuré"
        fi
    fi
    echo ""
fi

# Étape 6d : Configurer CORS automatiquement (intégré directement)
info "Configuration automatique de CORS pour l'accès réseau..."

# Détecter toutes les URLs possibles pour CORS
CORS_ORIGINS="http://localhost:8000,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8000"

# Ajouter le hostname si disponible
if [ -n "$HOSTNAME_FULL" ] && [ "$HOSTNAME_FULL" != "localhost" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$HOSTNAME_FULL:8000,http://$HOSTNAME_FULL:3000"
fi

# Ajouter l'IP locale
if [ -n "$VM_IP" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$VM_IP:8000,http://$VM_IP:3000"
fi

# Ajouter l'IP publique si disponible
IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || curl -s --max-time 2 ipinfo.io/ip 2>/dev/null || echo "")
if [ -n "$IP_PUBLIC" ]; then
    CORS_ORIGINS="$CORS_ORIGINS,http://$IP_PUBLIC:8000"
    # Si on a un port externe Docker, l'ajouter aussi
    if [ -f ".docker_external_port" ]; then
        EXTERNAL_PORT=$(cat .docker_external_port)
        CORS_ORIGINS="$CORS_ORIGINS,http://$IP_PUBLIC:$EXTERNAL_PORT"
    fi
fi

# Ajouter l'alias si configuré
if [ -f ".host_alias" ]; then
    HOST_ALIAS=$(cat .host_alias | awk '{print $2}')
    if [ -n "$HOST_ALIAS" ]; then
        CORS_ORIGINS="$CORS_ORIGINS,http://$HOST_ALIAS:8000"
    fi
fi

# Créer/mettre à jour le fichier .env avec CORS
cd backend
if [ -f ".env" ]; then
    # Mettre à jour CORS_ORIGINS si existe, sinon ajouter
    if grep -q "^CORS_ORIGINS=" .env; then
        sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$CORS_ORIGINS|" .env
    else
        echo "CORS_ORIGINS=$CORS_ORIGINS" >> .env
    fi
else
    cat > .env << EOF
# Configuration CORS - Autoriser l'accès depuis le réseau local
CORS_ORIGINS=$CORS_ORIGINS

# Configuration LLM (optionnel - l'application fonctionne sans)
# OPENAI_API_KEY=votre_cle_api_openai
# OPENAI_MODEL=gpt-4o-mini
EOF
fi
cd ..

success "CORS configuré automatiquement"
echo ""

# Étape 7 : Récupérer toutes les informations réseau
info "Collecte des informations réseau..."

# Trouver l'IP locale
VM_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
if [ -z "$VM_IP" ]; then
    VM_IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1 || echo "")
fi

# Trouver l'IP publique
if [ -z "$IP_PUBLIC" ]; then
    IP_PUBLIC=$(curl -s --max-time 2 ifconfig.me 2>/dev/null || curl -s --max-time 2 ipinfo.io/ip 2>/dev/null || echo "")
fi

# Hostname
if [ -z "$HOSTNAME_FULL" ]; then
    HOSTNAME_FULL=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
fi

echo ""

# Étape 8 : Test de l'installation
info "Test de l'installation..."

if python -c "from app.main import app" 2>/dev/null; then
    success "Installation testée avec succès"
else
    warning "Le test d'installation a échoué, mais cela peut être normal"
fi

echo ""

# Résumé final avec toutes les informations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Installation terminée avec succès !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Afficher les instructions Docker si applicable
if [ -f ".docker_external_port" ]; then
    EXTERNAL_PORT=$(cat .docker_external_port)
    CONTAINER_NAME=$(hostname)
    warning "⚠️  ACTION REQUISE : Configuration du mapping de port Docker"
    echo ""
    echo "   Le conteneur doit être redémarré avec le mapping de port."
    echo "   Depuis l'HÔTE Docker, exécutez :"
    echo ""
    echo "   docker stop $CONTAINER_NAME"
    echo "   docker commit $CONTAINER_NAME ovh-tracker:latest"
    echo "   docker rm $CONTAINER_NAME"
    echo "   docker run -d -p $EXTERNAL_PORT:8000 --name $CONTAINER_NAME ovh-tracker:latest"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 URLS D'ACCÈS À L'APPLICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# URL locale
echo "📍 Depuis cette machine (localhost) :"
echo "   http://localhost:$APP_PORT"
echo ""

# Priorité d'affichage : alias > hostname > IP publique > IP locale
URL_TO_SHARE=""
SHARE_METHOD=""

        # 1. Alias configuré (uniquement pour IP locale)
        if [ -f ".host_alias" ]; then
            HOST_ALIAS_LINE=$(cat .host_alias)
            HOST_ALIAS_IP=$(echo "$HOST_ALIAS_LINE" | awk '{print $1}')
            HOST_ALIAS=$(echo "$HOST_ALIAS_LINE" | awk '{print $2}')
            if [ -n "$HOST_ALIAS" ] && [ "$HOST_ALIAS_IP" = "$VM_IP" ]; then
                echo "📍 Depuis un autre ordinateur sur le RÉSEAU LOCAL (ALIAS) :"
                echo "   http://$HOST_ALIAS:$APP_PORT"
                echo ""
                echo "   ⚠️  IMPORTANT : L'alias fonctionne UNIQUEMENT pour l'IP locale ($VM_IP)"
                echo "   Pour utiliser l'alias, ajoutez dans /etc/hosts (Linux/Mac) ou"
                echo "   C:\\Windows\\System32\\drivers\\etc\\hosts (Windows) :"
                echo "   $HOST_ALIAS_LINE"
                echo ""
                echo "   ⚠️  Pour l'accès depuis Internet, utilisez l'IP publique (voir ci-dessous)"
                echo ""
                URL_TO_SHARE="http://$HOST_ALIAS:$APP_PORT"
                SHARE_METHOD="alias"
            fi
        fi

        # 2. Hostname (si pas d'alias ou en complément)
        if [ -z "$URL_TO_SHARE" ] && [ -n "$HOSTNAME_FULL" ] && [ "$HOSTNAME_FULL" != "localhost" ] && [[ "$HOSTNAME_FULL" != *"docker"* ]]; then
            echo "📍 Depuis un autre ordinateur (HOSTNAME) :"
            echo "   http://$HOSTNAME_FULL:$APP_PORT"
            echo ""
            URL_TO_SHARE="http://$HOSTNAME_FULL:$APP_PORT"
            SHARE_METHOD="hostname"
        fi

        # 3. IP publique
        if [ -n "$IP_PUBLIC" ]; then
            echo "📍 Depuis Internet (IP PUBLIQUE) :"
            echo "   http://$IP_PUBLIC:$APP_PORT"
            echo ""
            if [ -z "$URL_TO_SHARE" ]; then
                URL_TO_SHARE="http://$IP_PUBLIC:$APP_PORT"
                SHARE_METHOD="ip_public"
            fi
        fi

        # 4. IP locale
        if [ -n "$VM_IP" ]; then
            echo "📍 Depuis le réseau local (IP INTERNE) :"
            echo "   http://$VM_IP:$APP_PORT"
            echo ""
            if [ -z "$URL_TO_SHARE" ]; then
                URL_TO_SHARE="http://$VM_IP:$APP_PORT"
                SHARE_METHOD="ip_local"
            fi
        fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -n "$URL_TO_SHARE" ]; then
    echo "💡 URL À PARTAGER AVEC VOS COLLÈGUES :"
    echo "   $URL_TO_SHARE"
    if [ "$SHARE_METHOD" = "alias" ]; then
        echo ""
        echo "   ⚠️  N'oubliez pas : vos collègues doivent ajouter l'alias dans /etc/hosts"
    elif [ "$SHARE_METHOD" = "ip_public_docker" ] || [ "$SHARE_METHOD" = "ip_public" ]; then
        echo ""
        echo "   ⚠️  Vérifiez que le port est ouvert dans le firewall"
    elif [ "$SHARE_METHOD" = "ip_local" ]; then
        echo ""
        echo "   ⚠️  Les deux machines doivent être sur le même réseau local"
    fi
else
    echo "⚠️  Impossible de déterminer l'URL d'accès réseau"
    echo "   Utilisez : ./check_access.sh pour plus d'informations"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Prochaines étapes :"
echo ""
echo "1. Démarrer l'application :"
echo "   cd $INSTALL_DIR"
echo "   ./start.sh"
echo ""
echo "2. Vérifier l'accessibilité :"
echo "   ./check_access.sh"
echo ""
echo "3. Vérifier le statut :"
echo "   ./status.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Lancer le diagnostic d'accessibilité
echo ""
info "Lancement du diagnostic d'accessibilité..."
echo ""
if [ -f "check_access.sh" ]; then
    ./check_access.sh
else
    warning "Script check_access.sh non trouvé"
fi

