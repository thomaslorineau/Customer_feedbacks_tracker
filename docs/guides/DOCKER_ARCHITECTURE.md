# Docker Architecture Guide

## Overview

VibeCoding utilise une architecture Docker robuste pour la production :

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   nginx     │    │    API      │    │      Worker         │ │
│  │  (reverse   │───▶│  (FastAPI)  │    │  (Scraping jobs)    │ │
│  │   proxy)    │    │  4 workers  │    │                     │ │
│  └─────────────┘    └──────┬──────┘    └──────────┬──────────┘ │
│        :80                 │                      │             │
│        :443                │                      │             │
│                            │                      │             │
│                    ┌───────▼──────────────────────▼───────┐    │
│                    │              Redis                    │    │
│                    │         (Job Queue)                   │    │
│                    └───────────────────────────────────────┘    │
│                                    │                             │
│                    ┌───────────────▼───────────────────────┐    │
│                    │           PostgreSQL                   │    │
│                    │         (Database)                     │    │
│                    └───────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      Scheduler                               │ │
│  │  (Cron jobs: auto-scrape every 3h, backups)                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Pourquoi cette architecture ?

### Problème initial
- **Server crashes** : Le serveur uvicorn crashait pendant le scraping
- **Blocage** : Les scrapers bloquaient l'event loop async
- **DuckDB** : Ne supportait pas bien les accès concurrents (remplacé par PostgreSQL)

### Solution
1. **Workers isolés** : Le scraping tourne dans des processus séparés
2. **Redis Queue** : Découple l'API du travail lourd
3. **PostgreSQL** : Base de données robuste avec accès concurrent
4. **Multi-workers** : Gunicorn avec 4 workers Uvicorn

## Quick Start

### Windows (PowerShell)

```powershell
# Premier lancement (build + start)
.\scripts\start-docker.ps1 -Build

# Avec migration des données DuckDB
.\scripts\start-docker.ps1 -Build -Migrate

# Voir les logs
.\scripts\start-docker.ps1 -Logs

# Arrêter
.\scripts\start-docker.ps1 -Stop
```

### Linux/Mac

```bash
# Rendre le script exécutable
chmod +x scripts/start-docker.sh

# Premier lancement
./scripts/start-docker.sh --build

# Avec migration
./scripts/start-docker.sh --build --migrate

# Logs
./scripts/start-docker.sh --logs
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI avec Gunicorn (4 workers) |
| PostgreSQL | 5432 | Base de données |
| Redis | 6379 | Job queue |
| Worker | - | Processus de scraping |
| Scheduler | - | Cron jobs (auto-scrape, backups) |

## Endpoints API

### Jobs Asynchrones (nouveaux)

```http
# Status de la queue
GET /jobs/status

# Lancer un scrape async
POST /jobs/scrape
{
  "source": "trustpilot",
  "query": "OVH",
  "limit": 50,
  "priority": 0
}

# Vérifier le status d'un job
GET /jobs/{job_id}

# Annuler un job
DELETE /jobs/{job_id}

# Lister les jobs récents
GET /jobs/
```

## Configuration

### Variables d'environnement

Créer un fichier `.env` à la racine :

```bash
# Base de données
POSTGRES_PASSWORD=votre_mot_de_passe_securise
DATABASE_URL=postgresql://ocft_user:${POSTGRES_PASSWORD}@postgres:5432/ocft_tracker

# Redis
REDIS_URL=redis://redis:6379/0

# Mode
USE_POSTGRES=true
ENVIRONMENT=production

# Workers
WORKERS=4
WORKER_CONCURRENCY=2
```

### Mode Développement

Pour développer avec hot-reload mais utiliser PostgreSQL/Redis Docker :

```powershell
# Démarre uniquement Postgres + Redis
.\scripts\dev-docker.ps1 -Postgres

# Dans un autre terminal, lancer l'API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Dans un autre terminal, lancer le worker (optionnel)
python worker.py
```

## Migration DuckDB → PostgreSQL (TERMINÉE)

> **Note:** La migration complète vers PostgreSQL a été effectuée le 25 janvier 2026. Toutes les données (591 posts) ont été migrées avec succès.

Le script de migration est conservé pour référence dans `backend/scripts/migrate_to_postgres.py`.

## Maintenance

### Backups

```bash
# Backup manuel PostgreSQL
docker compose exec postgres pg_dump -U ocft_user ocft_tracker > backup.sql

# Restore
docker compose exec -T postgres psql -U ocft_user ocft_tracker < backup.sql
```

### Logs

```bash
# Tous les logs
docker compose logs -f

# Logs d'un service
docker compose logs -f api
docker compose logs -f worker

# Dernières 100 lignes
docker compose logs --tail=100 api
```

### Scaling Workers

```bash
# Lancer 3 instances du worker
docker compose up -d --scale worker=3
```

## Troubleshooting

### PostgreSQL ne démarre pas

```bash
# Vérifier les logs
docker compose logs postgres

# Réinitialiser les données (ATTENTION: supprime tout)
docker compose down -v
docker compose up -d
```

### Redis plein

```bash
# Vérifier la mémoire
docker compose exec redis redis-cli INFO memory

# Vider le cache
docker compose exec redis redis-cli FLUSHALL
```

### Worker bloqué

```bash
# Redémarrer le worker
docker compose restart worker

# Voir les jobs en cours
docker compose exec redis redis-cli LRANGE vibe:jobs:processing 0 -1
```

## Comparaison Modes

| Aspect | Local (PostgreSQL) | Docker (PostgreSQL) |
|--------|----------------|---------------------|
| Setup | Simple | Docker requis |
| Concurrence | Limitée | Excellente |
| Stabilité | Crashes possibles | Robuste |
| Scraping | Bloquant | Async via workers |
| Backups | Manuel | Automatiques |
| Dev | Rapide | Plus lourd |
| Production | Non recommandé | ✅ Recommandé |
