# Guide de dépannage rapide - Docker ne démarre pas

## Problème : "Unable to connect" sur gw.lab.core.ovh.net:11840

### Solution rapide (5 minutes)

Sur votre serveur distant, exécutez ces commandes dans l'ordre :

```bash
# 1. Récupérer les dernières modifications
git pull

# 2. Arrêter tous les containers
docker compose down

# 3. Vérifier et nettoyer les anciens containers
chmod +x scripts/cleanup-old-containers.sh
./scripts/cleanup-old-containers.sh
# Répondez "o" pour supprimer les anciens containers vibe_*

# 4. Vérifier les données dans l'ancien volume (si nécessaire)
chmod +x scripts/check-old-data.sh
./scripts/check-old-data.sh

# 5. Reconstruire les images Docker (IMPORTANT)
docker compose build --no-cache

# 6. Démarrer les containers
docker compose up -d

# 7. Vérifier l'état
docker compose ps

# 8. Consulter les logs si problème
docker compose logs api --tail=50
```

### Diagnostic détaillé

Si le problème persiste, utilisez le script de diagnostic :

```bash
chmod +x scripts/diagnose-docker.sh
./scripts/diagnose-docker.sh
```

Ce script va :
- Vérifier l'état de tous les containers
- Vérifier les ports exposés
- Afficher les logs de l'API
- Tester la connexion PostgreSQL
- Tester la connexion HTTP locale
- Donner des recommandations spécifiques

### Problèmes courants et solutions

#### 1. Containers ne démarrent pas

```bash
# Vérifier les logs
docker compose logs api
docker compose logs postgres
docker compose logs redis

# Redémarrer un service spécifique
docker compose restart api
```

#### 2. Port 11840 non accessible

```bash
# Vérifier que le port est bien exposé
docker compose ps | grep 11840

# Vérifier les ports en écoute (nécessite root)
netstat -tlnp | grep 11840
# OU
ss -tlnp | grep 11840

# Vérifier le firewall
sudo iptables -L -n | grep 11840
```

#### 3. PostgreSQL ne démarre pas

```bash
# Vérifier les logs PostgreSQL
docker compose logs postgres

# Vérifier la santé
docker compose exec postgres pg_isready -U ocft_user -d ocft_tracker

# Réinitialiser si nécessaire (ATTENTION: supprime les données)
docker compose down -v
docker compose up -d postgres
```

#### 4. API unhealthy

```bash
# Vérifier les logs détaillés
docker compose logs api --tail=100

# Vérifier la connexion à PostgreSQL depuis l'API
docker compose exec api python -c "from app.database import get_pg_connection; print('OK')"

# Redémarrer l'API
docker compose restart api
```

#### 5. Anciens containers en conflit

```bash
# Lister tous les containers
docker ps -a | grep -E "vibe_|ocft_"

# Supprimer les anciens containers manuellement
docker stop vibe_api vibe_postgres vibe_redis 2>/dev/null || true
docker rm vibe_api vibe_postgres vibe_redis 2>/dev/null || true

# Utiliser le script de nettoyage
./scripts/cleanup-old-containers.sh
```

### Vérification finale

Une fois les containers démarrés :

```bash
# 1. Vérifier que tous les containers sont "Up"
docker compose ps

# 2. Tester la connexion locale
curl http://localhost:11840/health

# 3. Tester depuis l'extérieur (depuis votre machine)
curl http://gw.lab.core.ovh.net:11840/health

# 4. Vérifier les logs en temps réel
docker compose logs -f api
```

### Si rien ne fonctionne

1. **Sauvegarder les données** (si importantes) :
```bash
docker compose exec postgres pg_dump -U ocft_user ocft_tracker > backup.sql
```

2. **Tout nettoyer et repartir à zéro** :
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

3. **Vérifier les permissions** :
```bash
ls -la docker-compose.yml
ls -la backend/
ls -la frontend/
```

### Commandes utiles

```bash
# Voir tous les containers Docker (même arrêtés)
docker ps -a

# Voir tous les volumes
docker volume ls

# Voir tous les réseaux
docker network ls

# Nettoyer les ressources Docker non utilisées
docker system prune -a

# Reconstruire un service spécifique
docker compose build api
docker compose up -d api
```
