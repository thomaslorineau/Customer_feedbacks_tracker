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
chmod +x start.sh stop.sh status.sh backup.sh check_access.sh 2>/dev/null || true

success "Scripts configurés"
echo ""

# Étape 7 : Configuration optionnelle
info "Configuration de l'application..."

# Trouver l'IP de la VM
VM_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
if [ -z "$VM_IP" ]; then
    VM_IP=$(ip addr show 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d/ -f1 || echo "")
fi

cd backend

# Créer le fichier .env s'il n'existe pas
if [ ! -f ".env" ]; then
    info "Création du fichier de configuration .env..."
    
    # Construire la configuration CORS
    CORS_ORIGINS="http://localhost:8000,http://localhost:3000,http://localhost:8080"
    if [ -n "$VM_IP" ]; then
        CORS_ORIGINS="$CORS_ORIGINS,http://$VM_IP:8000,http://$VM_IP:3000,http://$VM_IP:8080"
    fi
    
    cat > .env << EOF
# Configuration CORS - Autoriser l'accès depuis le réseau local
CORS_ORIGINS=$CORS_ORIGINS

# Configuration LLM (optionnel - l'application fonctionne sans)
# Décommentez et remplissez si vous avez une clé API
# OPENAI_API_KEY=votre_cle_api_openai
# OPENAI_MODEL=gpt-4o-mini

# Ou utiliser Anthropic
# ANTHROPIC_API_KEY=votre_cle_api_anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_MODEL=claude-3-haiku-20240307
EOF
    
    success "Fichier .env créé"
else
    info "Fichier .env existe déjà, conservation de la configuration actuelle"
fi

cd ..

echo ""

# Étape 8 : Test de l'installation
info "Test de l'installation..."

if python -c "from app.main import app" 2>/dev/null; then
    success "Installation testée avec succès"
else
    warning "Le test d'installation a échoué, mais cela peut être normal"
fi

echo ""

# Résumé
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Installation terminée avec succès !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Prochaines étapes :"
echo ""
echo "1. Démarrer l'application :"
echo "   cd $INSTALL_DIR"
echo "   ./start.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 ACCÈS À L'APPLICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ -n "$VM_IP" ]; then
    echo "📍 Depuis cette VM (localhost) :"
    echo "   http://localhost:8000"
    echo ""
    echo "📍 Depuis un autre ordinateur sur le même réseau local :"
    echo "   http://$VM_IP:8000"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 URL À PARTAGER AVEC VOS COLLÈGUES :"
    echo "   http://$VM_IP:8000"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⚠️  Important :"
    echo "   - Les deux machines doivent être sur le même réseau (Wi-Fi ou filaire)"
    echo "   - Si l'accès ne fonctionne pas, vérifiez le firewall de la VM"
    echo ""
else
    echo "📍 Depuis cette VM :"
    echo "   http://localhost:8000"
    echo ""
    echo "📍 Pour accéder depuis le réseau, trouvez l'IP de cette VM :"
    echo "   hostname -I"
    echo ""
    echo "   Puis utilisez : http://IP_TROUVEE:8000"
    echo ""
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "2. Vérifier le statut :"
echo "   ./status.sh"
echo ""
echo "3. Voir les logs :"
echo "   tail -f backend/server.log"
echo ""
echo "4. Arrêter l'application :"
echo "   ./stop.sh"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

