#!/bin/bash
# Script de mise à jour rapide pour Linux
# Usage: bash quick-update.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Mise à jour rapide"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Mettre à jour le code
echo "📥 Mise à jour du code..."
if git pull origin master 2>/dev/null || git pull github master 2>/dev/null; then
    echo "✅ Code mis à jour"
else
    echo "⚠️  Erreur lors du pull (peut-être déjà à jour)"
fi
echo ""

# 2. Activer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel introuvable"
    echo "   Exécutez d'abord: ./install.sh"
    exit 1
fi

echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate
echo ""

# 3. Installer DuckDB
echo "📦 Installation de DuckDB..."
if python -c "import duckdb" 2>/dev/null; then
    VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null)
    echo "✅ DuckDB déjà installé (version $VERSION)"
else
    if pip install duckdb==0.10.0; then
        echo "✅ DuckDB installé"
    else
        echo "❌ Erreur lors de l'installation de DuckDB"
        exit 1
    fi
fi
echo ""

# 4. Vérifier l'installation
echo "🔍 Vérification..."
if python -c "import duckdb" 2>/dev/null; then
    VERSION=$(python -c "import duckdb; print(duckdb.__version__)" 2>/dev/null)
    echo "✅ DuckDB version $VERSION installé"
else
    echo "❌ DuckDB non disponible"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Mise à jour terminée !"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Prochaines étapes:"
echo "   1. Configurez les variables d'environnement:"
echo "      export ENVIRONMENT=production"
echo "      export USE_DUCKDB=true"
echo ""
echo "   2. Redémarrez l'application:"
echo "      bash scripts/app/restart.sh"
echo ""

