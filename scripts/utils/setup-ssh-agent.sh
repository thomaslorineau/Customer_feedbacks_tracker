#!/bin/bash
# Script pour configurer SSH Agent et ajouter la clé SSH (Ubuntu/WSL)
# Usage: bash scripts/utils/setup-ssh-agent.sh

echo "🔐 Configuration SSH Agent"
echo "================================"

# Démarrer ssh-agent si pas déjà démarré
if [ -z "$SSH_AUTH_SOCK" ]; then
    echo ""
    echo "Démarrage de ssh-agent..."
    eval "$(ssh-agent -s)"
    echo "✅ ssh-agent démarré"
else
    echo "✅ ssh-agent déjà actif"
fi

# Ajouter la clé SSH
SSH_KEY="$HOME/.ssh/id_rsa_windows"
if [ -f "$SSH_KEY" ]; then
    echo ""
    echo "Ajout de la clé SSH: $SSH_KEY"
    echo "Entrez votre passphrase (elle sera mémorisée pour cette session):"
    ssh-add "$SSH_KEY"
    
    if [ $? -eq 0 ]; then
        echo "✅ Clé SSH ajoutée avec succès!"
        echo ""
        echo "Vous pouvez maintenant faire git push sans retaper la passphrase"
    else
        echo "❌ Erreur lors de l'ajout de la clé"
    fi
else
    echo "⚠️  Clé SSH non trouvée: $SSH_KEY"
    echo "Vérifiez le chemin de votre clé SSH"
fi

echo ""
echo "================================"


