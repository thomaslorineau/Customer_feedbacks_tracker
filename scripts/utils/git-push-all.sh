#!/bin/bash
# Script pour push develop et master avec SSH Agent (Ubuntu/WSL)
# Usage: bash scripts/utils/git-push-all.sh

echo "📤 Push Git avec SSH Agent"
echo "================================"

# Vérifier si la clé est déjà dans ssh-agent
if ! ssh-add -l &>/dev/null; then
    echo ""
    echo "⚠️  Aucune clé SSH dans l'agent"
    echo "Exécutez d'abord: bash scripts/utils/setup-ssh-agent.sh"
    echo "OU ajoutez manuellement: ssh-add ~/.ssh/id_rsa_windows"
    exit 1
fi

echo "✅ Clé SSH détectée dans l'agent"

# Push develop
echo ""
echo "📤 Push develop..."
git checkout develop
git push origin develop

if [ $? -eq 0 ]; then
    echo "✅ develop pushé"
else
    echo "❌ Erreur lors du push develop"
    exit 1
fi

# Push master
echo ""
echo "📤 Push master..."
git checkout master
git push origin master

if [ $? -eq 0 ]; then
    echo "✅ master pushé"
else
    echo "❌ Erreur lors du push master"
    exit 1
fi

echo ""
echo "✅ Tous les pushs réussis!"
echo "================================"



