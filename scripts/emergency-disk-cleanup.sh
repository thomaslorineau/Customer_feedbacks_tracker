#!/bin/bash
# Script d'urgence pour libérer de l'espace disque rapidement

set -e

echo "=== URGENCE : Libération d'espace disque ==="
echo ""

# 1. Vérifier l'espace actuel
echo "1. Espace disque actuel :"
df -h | grep -E "Filesystem|/$|/home"
echo ""

# 2. Arrêter tous les conteneurs Docker
echo "2. Arrêt des conteneurs Docker..."
cd ~/projects/Customer_feedbacks_tracker 2>/dev/null || cd /home/tlorinea/projects/Customer_feedbacks_tracker
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || echo "Pas de docker-compose.yml trouvé"
echo ""

# 3. Nettoyer Docker (sans supprimer les volumes utilisés)
echo "3. Nettoyage Docker..."
docker container prune -f 2>/dev/null || echo "Erreur container prune"
docker image prune -a -f 2>/dev/null || echo "Erreur image prune"
docker system prune -f 2>/dev/null || echo "Erreur system prune"
echo ""

# 4. Nettoyer les logs Docker volumineux
echo "4. Nettoyage des logs Docker..."
if [ -d /var/lib/docker/containers ]; then
    sudo find /var/lib/docker/containers -name "*.log" -size +100M -exec sudo truncate -s 0 {} \; 2>/dev/null || echo "Impossible de nettoyer les logs (besoin sudo)"
fi
echo ""

# 5. Nettoyer les fichiers temporaires
echo "5. Nettoyage des fichiers temporaires..."
sudo rm -rf /tmp/* 2>/dev/null || rm -rf /tmp/* 2>/dev/null || echo "Impossible de nettoyer /tmp"
sudo rm -rf /var/tmp/* 2>/dev/null || rm -rf /var/tmp/* 2>/dev/null || echo "Impossible de nettoyer /var/tmp"
echo ""

# 6. Nettoyer les packages apt (si applicable)
echo "6. Nettoyage des packages apt..."
sudo apt-get clean 2>/dev/null || echo "apt-get non disponible"
sudo apt-get autoremove -y 2>/dev/null || echo "apt-get non disponible"
echo ""

# 7. Trouver les gros fichiers
echo "7. Recherche des 10 plus gros fichiers/dossiers dans /home :"
du -h /home/tlorinea 2>/dev/null | sort -rh | head -10 || echo "Impossible de scanner /home"
echo ""

# 8. Nettoyer les fichiers .git/objects si nécessaire (ATTENTION)
echo "8. Vérification de la taille des repos Git..."
find ~/projects -name ".git" -type d -exec du -sh {} \; 2>/dev/null | sort -rh | head -5
echo ""

# 9. Afficher l'espace libéré
echo "9. Espace disque après nettoyage :"
df -h | grep -E "Filesystem|/$|/home"
echo ""

# 10. Afficher l'espace Docker
echo "10. Espace Docker :"
docker system df 2>/dev/null || echo "Docker non disponible"
echo ""

echo "=== Nettoyage terminé ==="
echo ""
echo "Si l'espace est toujours insuffisant, vérifiez :"
echo "  - Les logs système : sudo journalctl --vacuum-time=3d"
echo "  - Les snapshots LVM (si applicable)"
echo "  - Les anciennes sauvegardes"
echo "  - Les fichiers de log volumineux dans /var/log"
