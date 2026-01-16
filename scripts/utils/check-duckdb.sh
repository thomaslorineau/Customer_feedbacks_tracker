#!/bin/bash
# Script pour vérifier si DuckDB est installé et utilisé
# Usage: bash scripts/utils/check-duckdb.sh

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
echo "🔍 Vérification DuckDB"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Obtenir le répertoire du script et remonter à la racine
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$APP_DIR"

# 1. Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    error "Environnement virtuel introuvable"
    echo "   Exécutez d'abord: ./install.sh"
    exit 1
fi

info "Activation de l'environnement virtuel..."
source venv/bin/activate

# 2. Vérifier si DuckDB est installé
info "Vérification de l'installation DuckDB..."
if python -c "import duckdb" 2>/dev/null; then
    DUCKDB_VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null || echo "inconnue")
    success "DuckDB installé (version $DUCKDB_VERSION)"
else
    error "DuckDB n'est PAS installé"
    echo ""
    echo "💡 Pour installer DuckDB:"
    echo "   bash scripts/utils/install-duckdb.sh"
    exit 1
fi

# 3. Vérifier la variable d'environnement
echo ""
info "Vérification de la configuration..."
ENV_VAR=$(echo $USE_DUCKDB)
if [ "$ENV_VAR" = "true" ]; then
    success "USE_DUCKDB=true est défini"
else
    warning "USE_DUCKDB n'est pas défini ou n'est pas 'true'"
    echo "   Définissez-le avec: export USE_DUCKDB=true"
fi

# 4. Vérifier le fichier de base de données
echo ""
info "Vérification des fichiers de base de données..."
if [ -f "backend/data.duckdb" ]; then
    success "Fichier data.duckdb existe"
    DB_SIZE=$(du -h backend/data.duckdb 2>/dev/null | cut -f1)
    info "   Taille: $DB_SIZE"
else
    warning "Fichier data.duckdb n'existe pas"
    echo "   Il sera créé au premier démarrage si USE_DUCKDB=true"
fi

# 5. Test de connexion avec l'application
echo ""
info "Test de connexion avec l'application..."
export ENVIRONMENT=production
export USE_DUCKDB=true

python3 -c "
import os
import sys
os.environ['ENVIRONMENT'] = 'production'
os.environ['USE_DUCKDB'] = 'true'
sys.path.insert(0, 'backend')
try:
    from app.db import get_db_connection
    conn, is_duckdb = get_db_connection()
    if is_duckdb:
        print('✅ L\'application utilise DuckDB')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM posts' if 'posts' in [row[0] for row in cursor.execute('SHOW TABLES').fetchall()] else 'SELECT 1')
        conn.close()
    else:
        print('❌ L\'application utilise SQLite (fallback)')
        conn.close()
except Exception as e:
    print(f'❌ Erreur: {e}')
" 2>&1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


