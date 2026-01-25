# Guide de dépannage Docker

## Problème : Le serveur ne démarre plus après migration vibe -> ocft

### Symptômes
- `Unable to connect` dans le navigateur
- Containers Docker ne démarrent pas
- Erreurs de connexion à PostgreSQL

### Causes possibles

1. **Anciens containers en conflit** : Les containers avec les anciens noms (`vibe_*`) existent encore
2. **Volume PostgreSQL existant** : Le volume contient encore l'ancienne base `vibe_tracker`
3. **Réseau Docker en conflit** : L'ancien réseau `vibe_network` existe encore

## Solution étape par étape

### Étape 1 : Vérifier l'état des containers

```bash
docker compose ps -a
```

Vous devriez voir des containers avec les noms `ocft_*`. Si vous voyez encore des `vibe_*`, ils doivent être supprimés.

### Étape 2 : Arrêter tous les containers

```bash
docker compose down
```

### Étape 3 : Nettoyer les anciens containers

Utilisez le script de nettoyage :

```bash
# Linux/Mac
./scripts/cleanup-old-containers.sh

# Windows PowerShell
.\scripts\cleanup-old-containers.ps1
```

Ou manuellement :

```bash
# Lister les anciens containers
docker ps -a | grep vibe_

# Arrêter et supprimer
docker stop vibe_postgres vibe_redis vibe_api vibe_worker vibe_scheduler 2>/dev/null || true
docker rm vibe_postgres vibe_redis vibe_api vibe_worker vibe_scheduler 2>/dev/null || true
```

### Étape 4 : Migrer les données (si nécessaire)

Si vous avez des données dans l'ancienne base `vibe_tracker`, migrez-les :

```bash
# D'abord, démarrer temporairement les anciens containers pour accéder aux données
# OU utiliser le script de migration si les données sont encore accessibles

./scripts/migrate-vibe-to-ocft.sh
```

### Étape 5 : Supprimer les anciens volumes (OPTIONNEL)

⚠️ **ATTENTION** : Cela supprimera définitivement les données si elles n'ont pas été migrées !

```bash
# Lister les volumes
docker volume ls | grep vibe

# Supprimer (UNIQUEMENT si les données sont migrées)
docker volume rm <volume_name>
```

### Étape 6 : Recréer les containers avec les nouveaux noms

```bash
# Reconstruire les images
docker compose build --no-cache

# Démarrer les services
docker compose up -d
```

### Étape 7 : Vérifier que tout fonctionne

```bash
# Vérifier l'état des containers
docker compose ps

# Vérifier les logs
docker compose logs api

# Tester la connexion
curl http://localhost:11840/
```

## Problème : PostgreSQL ne démarre pas

### Symptômes
- Container `ocft_postgres` en erreur
- Healthcheck échoue
- Erreur "database does not exist"

### Solution

Le volume PostgreSQL existant contient peut-être encore l'ancienne configuration. Deux options :

#### Option A : Supprimer le volume et recréer (perte de données)

```bash
docker compose down -v
docker compose up -d postgres
```

#### Option B : Migrer les données d'abord

1. Démarrer temporairement l'ancien container PostgreSQL
2. Exporter les données
3. Supprimer le volume
4. Recréer avec les nouveaux noms
5. Importer les données

## Problème : Erreur "container name already in use"

### Solution

```bash
# Supprimer le container existant
docker rm -f ocft_postgres ocft_redis ocft_api ocft_worker ocft_scheduler

# Recréer
docker compose up -d
```

## Problème : Erreur de connexion à la base de données

### Vérifications

1. **Vérifier que PostgreSQL est démarré** :
   ```bash
   docker compose ps postgres
   ```

2. **Vérifier les logs PostgreSQL** :
   ```bash
   docker compose logs postgres
   ```

3. **Tester la connexion** :
   ```bash
   docker compose exec postgres psql -U ocft_user -d ocft_tracker -c "SELECT 1;"
   ```

4. **Vérifier DATABASE_URL** :
   ```bash
   docker compose exec api env | grep DATABASE_URL
   ```
   
   Doit être : `postgresql://ocft_user:...@postgres:5432/ocft_tracker`

## Problème : Port 11840 déjà utilisé

### Solution

```bash
# Trouver le processus qui utilise le port
sudo lsof -i :11840
# ou
netstat -tlnp | grep 11840

# Arrêter le processus ou changer le port dans docker-compose.yml
```

## Commandes utiles

```bash
# Voir tous les containers (y compris arrêtés)
docker ps -a

# Voir tous les volumes
docker volume ls

# Voir tous les réseaux
docker network ls

# Logs en temps réel
docker compose logs -f api

# Redémarrer un service spécifique
docker compose restart api

# Reconstruire et redémarrer
docker compose up -d --build api
```

## Migration complète (recommandée)

Pour une migration propre, suivez ces étapes dans l'ordre :

1. **Arrêter tous les containers** :
   ```bash
   docker compose down
   ```

2. **Nettoyer les anciens containers** :
   ```bash
   ./scripts/cleanup-old-containers.sh
   ```

3. **Migrer les données** (si nécessaire) :
   ```bash
   ./scripts/migrate-vibe-to-ocft.sh
   ```

4. **Reconstruire les images** :
   ```bash
   docker compose build --no-cache
   ```

5. **Démarrer les services** :
   ```bash
   docker compose up -d
   ```

6. **Vérifier** :
   ```bash
   docker compose ps
   docker compose logs api
   ```

## Support

Si le problème persiste après avoir suivi ces étapes, vérifiez :
- Les logs complets : `docker compose logs`
- L'état des containers : `docker compose ps`
- Les volumes Docker : `docker volume ls`
- La configuration réseau : `docker network ls`
