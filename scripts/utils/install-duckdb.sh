#!/bin/bash
# Script pour installer et vérifier DuckDB
# Usage: bash scripts/utils/install-duckdb.sh

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Diagnostic et installation DuckDB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Obtenir le répertoire du script et remonter à la racine
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_DIR"

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    error "Environnement virtuel introuvable"
    echo "   Exécutez d'abord: ./install.sh"
    exit 1
fi

info "Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier Python
if ! command -v python &> /dev/null; then
    error "Python non trouvé dans l'environnement virtuel"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
info "Python: $PYTHON_VERSION"

# Vérifier si DuckDB est installé
info "Vérification de DuckDB..."
if python -c "import duckdb" 2>/dev/null; then
    DUCKDB_VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null || echo "inconnue")
    success "DuckDB est déjà installé (version $DUCKDB_VERSION)"
    exit 0
fi

warning "DuckDB n'est pas installé"
echo ""

# Installer DuckDB
info "Installation de DuckDB 0.10.0..."
if python -m pip install duckdb==0.10.0; then
    # Vérifier l'installation
    if python -c "import duckdb" 2>/dev/null; then
        DUCKDB_VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null || echo "inconnue")
        success "DuckDB installé avec succès (version $DUCKDB_VERSION)"
        
        # Tester la connexion
        info "Test de connexion DuckDB..."
        python -c "
import duckdb
conn = duckdb.connect(':memory:')
cursor = conn.cursor()
cursor.execute('SELECT 1')
result = cursor.fetchone()
conn.close()
print('✅ Connexion DuckDB fonctionnelle')
" 2>/dev/null && success "Test de connexion réussi" || warning "Test de connexion échoué"
        
    else
        error "DuckDB installé mais import échoué"
        exit 1
    fi
else
    error "Échec de l'installation de DuckDB"
    echo ""
    echo "💡 Solutions possibles:"
    echo "   1. Vérifiez votre connexion Internet"
    echo "   2. Mettez à jour pip: python -m pip install --upgrade pip"
    echo "   3. Installez les dépendances système si nécessaire"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "DuckDB est maintenant installé et fonctionnel !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "Pour vérifier que l'application utilise DuckDB:"
echo "   export ENVIRONMENT=production"
echo "   export USE_DUCKDB=true"
echo "   python3 -c \"import sys; sys.path.insert(0, 'backend'); from app.db import get_db_connection; conn, is_duckdb = get_db_connection(); print('DuckDB' if is_duckdb else 'SQLite'); conn.close()\""

