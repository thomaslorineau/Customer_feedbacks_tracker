# Guide Redis - File d'attente de Jobs

## Vue d'ensemble

Redis est utilisé dans VibeCoding comme **file d'attente distribuée** pour gérer les jobs de scraping de manière asynchrone. Cela permet de découpler l'API du travail lourd et d'éviter les crashes du serveur.

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │────────▶│     API     │────────▶│    Redis    │
│  (Browser)  │         │  (FastAPI)  │         │  (Queue)    │
└─────────────┘         └─────────────┘         └──────┬──────┘
                                                        │
                                                        ▼
                                                ┌─────────────┐
                                                │   Worker    │
                                                │  (Scraping) │
                                                └─────────────┘
```

### Flux de traitement

1. **Frontend** → Envoie une requête de scraping à l'API
2. **API** → Crée un job et l'ajoute à la queue Redis
3. **Worker** → Récupère le job depuis Redis et le traite
4. **Worker** → Met à jour le statut du job dans Redis
5. **Frontend** → Interroge l'API pour connaître le statut du job

## Pourquoi Redis ?

### Avantages

- **Découplage** : L'API reste responsive même pendant le scraping
- **Scalabilité** : Plusieurs workers peuvent traiter les jobs en parallèle
- **Persistance** : Les jobs survivent aux redémarrages (avec AOF)
- **Priorité** : Support des jobs prioritaires
- **Monitoring** : Statistiques en temps réel

### Fallback In-Memory

Si Redis n'est pas disponible, l'application utilise automatiquement une **queue in-memory** :

- ✅ L'application continue de fonctionner
- ⚠️ Les jobs sont perdus en cas de redémarrage
- ⚠️ Pas de distribution entre plusieurs workers

## Configuration

### Variables d'environnement

```bash
# URL Redis (format standard)
REDIS_URL=redis://localhost:6379/0

# Ou avec authentification
REDIS_URL=redis://:password@localhost:6379/0

# Ou avec hostname Docker
REDIS_URL=redis://redis:6379/0
```

### Docker Compose

Redis est configuré dans `docker-compose.yml` :

```yaml
redis:
  image: redis:7-alpine
  container_name: vibe_redis
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Configuration importante :**
- `--appendonly yes` : Persistance des données (AOF)
- `--maxmemory 256mb` : Limite mémoire à 256 MB
- `--maxmemory-policy allkeys-lru` : Éviction LRU si mémoire pleine

## Structure des données Redis

### Clés utilisées

| Clé | Type | Description |
|-----|------|-------------|
| `vibe:jobs:queue` | Sorted Set | Queue des jobs en attente (avec priorité) |
| `vibe:jobs:processing` | Set | Jobs actuellement en traitement |
| `vibe:jobs:results` | List | Historique des jobs terminés (1000 derniers) |
| `vibe:job:{job_id}` | String | Données complètes d'un job (JSON) |

### Format d'un Job

```json
{
  "id": "uuid",
  "job_type": "scrape_source",
  "payload": {
    "source": "reddit",
    "query": "OVH",
    "limit": 50
  },
  "status": "pending",
  "priority": 0,
  "attempts": 0,
  "max_attempts": 3,
  "created_at": "2026-01-25T13:00:00",
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "result": null
}
```

## Types de Jobs

### 1. Scraping de source unique

```python
job_id = queue.enqueue(
    job_type="scrape_source",
    payload={
        "source": "reddit",
        "query": "OVH",
        "limit": 50
    },
    priority=0
)
```

### 2. Scraping de toutes les sources

```python
job_id = queue.enqueue(
    job_type="scrape_all",
    payload={
        "queries": ["OVH", "OVHcloud"],
        "limit": 50
    },
    priority=1  # Priorité plus élevée
)
```

### 3. Backup de base de données

```python
job_id = queue.enqueue(
    job_type="backup",
    payload={
        "backup_type": "hourly"  # ou "daily"
    },
    priority=2  # Priorité haute
)
```

### 4. Nettoyage

```python
job_id = queue.enqueue(
    job_type="cleanup",
    payload={},
    priority=0
)
```

## Priorités

Les jobs sont traités par ordre de priorité :

- **Priorité 2** : Jobs critiques (backups)
- **Priorité 1** : Jobs importants (scraping manuel)
- **Priorité 0** : Jobs normaux (scraping automatique)

## API Endpoints

### Créer un job

```http
POST /api/jobs/scrape
Content-Type: application/json

{
  "source": "reddit",
  "query": "OVH",
  "limit": 50
}
```

**Réponse :**
```json
{
  "job_id": "abc123...",
  "status": "pending"
}
```

### Statut d'un job

```http
GET /api/jobs/{job_id}
```

**Réponse :**
```json
{
  "id": "abc123...",
  "status": "running",
  "progress": 50,
  "result": null
}
```

### Statut de la queue

```http
GET /api/jobs/status
```

**Réponse :**
```json
{
  "pending": 5,
  "processing": 2,
  "completed_today": 42
}
```

## Monitoring

### Via Redis CLI

```bash
# Se connecter au container Redis
docker compose exec redis redis-cli

# Voir la taille de la queue
ZCARD vibe:jobs:queue

# Voir les jobs en attente
ZRANGE vibe:jobs:queue 0 -1 WITHSCORES

# Voir les jobs en traitement
SMEMBERS vibe:jobs:processing

# Voir l'historique
LRANGE vibe:jobs:results 0 10

# Voir les détails d'un job
GET vibe:job:{job_id}

# Statistiques mémoire
INFO memory
```

### Via l'API

```http
GET /api/jobs/status
```

### Logs Docker

```bash
# Logs Redis
docker compose logs redis

# Logs Worker (traite les jobs)
docker compose logs worker

# Logs API (crée les jobs)
docker compose logs api
```

## Dépannage

### Redis ne démarre pas

**Symptôme :** Container Redis en erreur

**Solution :**
```bash
# Vérifier les logs
docker compose logs redis

# Redémarrer Redis
docker compose restart redis

# Vérifier la santé
docker compose exec redis redis-cli ping
# Devrait répondre: PONG
```

### Jobs bloqués en "processing"

**Symptôme :** Jobs restent en statut "processing" indéfiniment

**Cause :** Worker crashé ou timeout

**Solution :**
```bash
# Voir les jobs bloqués
docker compose exec redis redis-cli SMEMBERS vibe:jobs:processing

# Redémarrer le worker
docker compose restart worker

# Les jobs bloqués seront réessayés automatiquement
```

### Redis plein (OOM)

**Symptôme :** `OOM command not allowed when used memory > 'maxmemory'`

**Solution :**
```bash
# Vérifier l'utilisation mémoire
docker compose exec redis redis-cli INFO memory

# Nettoyer les anciens jobs (garder 100 derniers)
docker compose exec redis redis-cli LTRIM vibe:jobs:results 0 99

# Ou augmenter la limite dans docker-compose.yml
command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Fallback in-memory activé

**Symptôme :** Logs montrent "using in-memory queue"

**Cause :** Redis non disponible ou non connecté

**Vérification :**
```bash
# Vérifier que Redis est accessible depuis l'API
docker compose exec api python -c "
import os
os.environ['REDIS_URL'] = 'redis://redis:6379/0'
from app.job_queue import get_job_queue
queue = get_job_queue()
print('Queue type:', type(queue).__name__)
"
```

**Solution :**
```bash
# Vérifier que Redis est démarré
docker compose ps redis

# Vérifier la connectivité réseau
docker compose exec api ping redis

# Vérifier REDIS_URL dans l'API
docker compose exec api env | grep REDIS
```

## Performance

### Optimisations

1. **Limite mémoire** : 256 MB est suffisant pour ~10 000 jobs
2. **Expiration** : Jobs expirés après 7 jours
3. **Historique** : Garde seulement les 1000 derniers jobs terminés
4. **AOF** : Persistance activée pour la durabilité

### Métriques recommandées

- **Queue size** : < 100 jobs en attente (normal)
- **Processing** : < 10 jobs simultanés (selon nombre de workers)
- **Memory** : < 200 MB utilisés (sur 256 MB max)

## Sécurité

### En production

1. **Authentification** : Utiliser `requirepass` dans Redis
   ```yaml
   command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
   ```

2. **Réseau** : Ne pas exposer Redis sur Internet
   ```yaml
   ports:
     - "127.0.0.1:6379:6379"  # Localhost uniquement
   ```

3. **TLS** : Activer TLS pour les connexions distantes (optionnel)

## Migration depuis DuckDB

Redis a été introduit lors de la migration vers Docker. Avant, les jobs étaient traités de manière synchrone dans l'API, ce qui causait des crashes.

**Avant (sans Redis) :**
- Scraping synchrone → API bloque → Crash possible

**Après (avec Redis) :**
- Scraping asynchrone → API reste responsive → Stabilité

## Références

- **Code source** : `backend/app/job_queue.py`
- **Worker** : `backend/worker.py`
- **API endpoints** : `backend/app/routers/jobs.py`
- **Docker config** : `docker-compose.yml`

## FAQ

### Q: Puis-je utiliser Redis pour autre chose que les jobs ?

**R:** Oui, mais utilisez un préfixe différent pour éviter les conflits :
```python
# Exemple : cache
redis_client.set("cache:posts:all", json.dumps(posts), ex=300)
```

### Q: Que se passe-t-il si Redis crash ?

**R:** L'application bascule automatiquement sur la queue in-memory. Les jobs en cours sont perdus, mais l'API reste fonctionnelle.

### Q: Puis-je avoir plusieurs workers ?

**R:** Oui, lancez plusieurs containers worker :
```bash
docker compose up -d --scale worker=3
```

### Q: Comment sauvegarder Redis ?

**R:** Redis utilise AOF (Append-Only File) pour la persistance. Les données sont dans le volume Docker `redis_data`. Pour sauvegarder :
```bash
docker compose exec redis redis-cli BGSAVE
```
