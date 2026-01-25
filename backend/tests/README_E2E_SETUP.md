# 🧪 Guide de Configuration des Tests E2E

## ⚠️ Prérequis

**IMPORTANT** : Les tests E2E nécessitent que le serveur soit démarré et accessible sur `http://127.0.0.1:8000`.

## 🚀 Démarrage du Serveur

Avant de lancer les tests E2E, vous devez démarrer le serveur :

```bash
# Depuis le répertoire backend
cd backend
.\start_server.ps1

# Ou manuellement :
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## ✅ Vérification que le Serveur est Accessible

Vérifiez que le serveur répond :

```bash
# PowerShell
Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet

# Ou avec curl
curl http://localhost:8000/api/version
```

## 🧪 Exécution des Tests E2E

Une fois le serveur démarré, vous pouvez lancer les tests :

```bash
# Tests E2E pour les jobs
python -m pytest backend/tests/test_e2e_jobs.py -v

# Tests E2E pour la barre de progression (nécessite Playwright)
python -m pytest backend/tests/test_e2e_progress_bar.py -v

# Tous les tests E2E
python -m pytest backend/tests/test_e2e_*.py -v
```

## 📝 Note sur les Tests E2E

Les tests E2E sont conçus pour tester l'application complète avec un serveur réel. Ils ne peuvent pas fonctionner sans un serveur en cours d'exécution.

Si vous voyez l'erreur `httpx.ConnectError: All connection attempts failed`, cela signifie que :
1. Le serveur n'est pas démarré
2. Le serveur n'écoute pas sur le port 8000
3. Un firewall bloque la connexion

## 🔧 Dépannage

### Le serveur ne démarre pas
- Vérifiez qu'aucun autre processus n'utilise le port 8000
- Vérifiez les logs du serveur pour les erreurs
- Assurez-vous que toutes les dépendances sont installées

### Les tests échouent avec des erreurs de connexion
- Vérifiez que le serveur est bien démarré : `Test-NetConnection -ComputerName localhost -Port 8000`
- Vérifiez que l'URL de base est correcte dans les tests (par défaut : `http://127.0.0.1:8000`)
- Vous pouvez changer l'URL avec la variable d'environnement : `API_BASE_URL=http://127.0.0.1:8001 python -m pytest backend/tests/test_e2e_jobs.py`

### Erreurs de base de données PostgreSQL
- Si vous voyez "File is already open", arrêtez tous les processus Python et redémarrez le serveur
- Les tests E2E utilisent la même base de données que le serveur, donc des conflits peuvent survenir

