# Proposition : Système de Queue pour le Scraping

## 📋 Problème Actuel

### Symptômes
- Le bouton "Scrape New Data" fait planter la page après quelques minutes
- Les requêtes HTTP synchrones bloquent le navigateur
- 10 scrapers lancés en parallèle × plusieurs keywords = beaucoup de requêtes simultanées
- Pas de moyen de suivre la progression en temps réel
- Pas de possibilité d'annuler toutes les tâches facilement

### Causes Identifiées
1. **Frontend** : Tous les scrapers sont lancés en parallèle avec `Promise.all()` ou des promesses parallèles
2. **Backend** : Les endpoints `/scrape/*` sont synchrones et peuvent prendre plusieurs minutes chacun
3. **Pas de timeout** : Les requêtes peuvent rester bloquées indéfiniment
4. **Pas de queue** : Toutes les tâches sont exécutées simultanément sans limite

## 🎯 Objectifs

1. **Découpler le frontend du backend** : Le scraping doit tourner en arrière-plan
2. **Système de queue** : Gérer les tâches de manière asynchrone avec une file d'attente
3. **Monitoring en temps réel** : Afficher la progression dans les logs et dans l'UI
4. **Annulation globale** : Bouton "Cancel All" pour arrêter toutes les tâches en cours
5. **Persistance** : Les jobs doivent survivre aux redémarrages du serveur
6. **Logs détaillés** : Chaque étape doit être loggée pour le debugging

## 🏗️ Architecture Proposée

### 1. Backend : Système de Queue avec Celery ou ThreadPoolExecutor

#### Option A : Celery + Redis/RabbitMQ (Recommandé pour production)
```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI │────▶│   Celery    │
│             │     │  (API)   │     │   Worker    │
└─────────────┘     └──────────┘     └─────────────┘
                           │                 │
                           │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐
                    │   Redis/    │   │  Scrapers   │
                    │  RabbitMQ   │   │  (Tasks)    │
                    └─────────────┘   └─────────────┘
```

**Avantages :**
- ✅ Scalable (plusieurs workers)
- ✅ Persistance des jobs
- ✅ Retry automatique
- ✅ Monitoring avec Flower

**Inconvénients :**
- ❌ Dépendance externe (Redis/RabbitMQ)
- ❌ Plus complexe à déployer

#### Option B : ThreadPoolExecutor + Base de données (Plus simple)
```
┌─────────────┐     ┌──────────┐     ┌──────────────┐
│   Frontend  │────▶│  FastAPI │────▶│ ThreadPool   │
│             │     │  (API)   │     │  Executor    │
└─────────────┘     └──────────┘     └──────────────┘
                           │                 │
                           │                 │
                    ┌──────▼──────┐   ┌──────▼──────┐
                    │   SQLite    │   │  Scrapers   │
                    │  (Jobs DB)  │   │  (Tasks)    │
                    └─────────────┘   └─────────────┘
```

**Avantages :**
- ✅ Pas de dépendance externe
- ✅ Simple à déployer
- ✅ Utilise déjà SQLite

**Inconvénients :**
- ❌ Moins scalable
- ❌ Pas de retry automatique

**Recommandation : Option B** pour commencer (déjà un système de jobs dans `main.py`)

### 2. Structure des Jobs

```python
{
    "job_id": "uuid",
    "status": "pending|running|completed|failed|cancelled",
    "created_at": "timestamp",
    "started_at": "timestamp",
    "completed_at": "timestamp",
    "progress": {
        "total": 30,  # keywords × sources
        "completed": 5,
        "current_task": "Scraping X/Twitter for 'ovh vps'"
    },
    "results": [
        {"source": "x", "keyword": "ovh vps", "added": 10},
        {"source": "github", "keyword": "ovh vps", "added": 5}
    ],
    "errors": [],
    "logs": [
        {"timestamp": "...", "level": "info", "message": "..."}
    ]
}
```

### 3. Endpoints API

#### Créer un job de scraping
```http
POST /api/scrape/jobs
Content-Type: application/json

{
    "keywords": ["ovh vps", "ovh hosting"],
    "sources": ["x", "github", "stackoverflow", "news", "reddit", "trustpilot", "ovh-forum", "mastodon", "g2-crowd", "linkedin"],
    "limit": 50,
    "concurrency": 2  # Nombre de scrapers en parallèle
}

Response:
{
    "job_id": "uuid",
    "status": "pending",
    "message": "Job créé avec succès"
}
```

#### Obtenir le statut d'un job
```http
GET /api/scrape/jobs/{job_id}

Response:
{
    "job_id": "uuid",
    "status": "running",
    "progress": {
        "total": 20,
        "completed": 8,
        "current_task": "Scraping X/Twitter for 'ovh vps'"
    },
    "results": [...],
    "logs": [...]
}
```

#### Annuler un job
```http
POST /api/scrape/jobs/{job_id}/cancel

Response:
{
    "job_id": "uuid",
    "status": "cancelled",
    "message": "Job annulé avec succès"
}
```

#### Annuler tous les jobs
```http
POST /api/scrape/jobs/cancel-all

Response:
{
    "cancelled_count": 3,
    "message": "3 jobs annulés"
}
```

#### Lister tous les jobs
```http
GET /api/scrape/jobs?status=running&limit=10

Response:
{
    "jobs": [
        {
            "job_id": "uuid",
            "status": "running",
            "progress": {...}
        }
    ],
    "total": 10
}
```

#### Stream des logs en temps réel (SSE)
```http
GET /api/scrape/jobs/{job_id}/logs/stream

Response: Server-Sent Events (SSE)
data: {"timestamp": "...", "level": "info", "message": "Starting scraper..."}
data: {"timestamp": "...", "level": "success", "message": "Added 10 posts"}
```

### 4. Frontend : Interface Utilisateur

#### Composants à modifier/créer

1. **Bouton "Scrape New Data"** → Crée un job et redirige vers la page de monitoring
2. **Page de monitoring des jobs** (`/jobs` ou `/scraping-jobs`)
   - Liste des jobs en cours/terminés
   - Barre de progression pour chaque job
   - Logs en temps réel (SSE ou polling)
   - Bouton "Cancel" pour chaque job
   - Bouton "Cancel All" global
3. **Notification toast** : "Scraping démarré, job #1234 créé"

#### Workflow utilisateur

```
1. Utilisateur clique sur "Scrape New Data"
   ↓
2. Frontend envoie POST /api/scrape/jobs
   ↓
3. Backend crée un job et retourne job_id
   ↓
4. Frontend affiche notification + redirige vers /jobs/{job_id}
   ↓
5. Page de monitoring :
   - Affiche la progression en temps réel (polling ou SSE)
   - Affiche les logs en temps réel
   - Bouton "Cancel" disponible
   ↓
6. Quand terminé :
   - Affiche les résultats
   - Bouton "Retour à la collection" pour voir les nouveaux posts
```

### 5. Implémentation Backend

#### Fichiers à créer/modifier

**`backend/app/jobs/queue_manager.py`**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time
from typing import Dict, List, Optional
import uuid

class ScrapingQueueManager:
    def __init__(self, max_workers: int = 3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.jobs: Dict[str, Dict] = {}
        self.lock = Lock()
    
    def create_job(self, keywords: List[str], sources: List[str], limit: int = 50) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "status": "pending",
            "keywords": keywords,
            "sources": sources,
            "limit": limit,
            "created_at": time.time(),
            "progress": {"total": len(keywords) * len(sources), "completed": 0},
            "results": [],
            "errors": [],
            "logs": [],
            "cancelled": False
        }
        with self.lock:
            self.jobs[job_id] = job
        # Sauvegarder dans la DB
        db.create_job_record(job_id)
        # Démarrer le traitement
        self.executor.submit(self._process_job, job_id)
        return job_id
    
    def _process_job(self, job_id: str):
        # Implémentation du traitement
        pass
    
    def cancel_job(self, job_id: str) -> bool:
        # Annuler un job
        pass
    
    def cancel_all(self) -> int:
        # Annuler tous les jobs
        pass
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        # Récupérer un job
        pass
```

**`backend/app/routers/scraping_jobs.py`**
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/scrape/jobs", tags=["scraping-jobs"])

class JobRequest(BaseModel):
    keywords: List[str]
    sources: List[str] = None
    limit: int = 50
    concurrency: int = 2

@router.post("")
async def create_scraping_job(request: JobRequest):
    # Créer un job
    pass

@router.get("/{job_id}")
async def get_job_status(job_id: str):
    # Récupérer le statut
    pass

@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    # Annuler un job
    pass

@router.post("/cancel-all")
async def cancel_all_jobs():
    # Annuler tous les jobs
    pass

@router.get("")
async def list_jobs(status: str = None, limit: int = 10):
    # Lister les jobs
    pass
```

### 6. Implémentation Frontend

#### Fichiers à créer/modifier

**`frontend/jobs/index.html`** (nouvelle page)
- Liste des jobs
- Monitoring en temps réel
- Boutons d'annulation

**`frontend/js/jobs.js`** (nouveau fichier)
```javascript
class JobMonitor {
    constructor(jobId) {
        this.jobId = jobId;
        this.eventSource = null;
    }
    
    startMonitoring() {
        // Polling ou SSE pour les logs
        this.pollStatus();
    }
    
    async pollStatus() {
        const response = await fetch(`/api/scrape/jobs/${this.jobId}`);
        const job = await response.json();
        this.updateUI(job);
        if (job.status === 'running') {
            setTimeout(() => this.pollStatus(), 2000);
        }
    }
    
    cancel() {
        fetch(`/api/scrape/jobs/${this.jobId}/cancel`, { method: 'POST' });
    }
}
```

**`frontend/index.html`** (modifier)
- Modifier `scrapeAllSources()` pour créer un job au lieu de lancer directement
- Rediriger vers la page de monitoring

### 7. Logs et Monitoring

#### Logs dans la base de données
```sql
CREATE TABLE scraping_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    level TEXT NOT NULL,  -- info, success, warning, error
    message TEXT NOT NULL,
    source TEXT,
    keyword TEXT
);
```

#### Logs dans les fichiers
- Continuer à utiliser `log_scraping()` pour les logs fichiers
- Ajouter les logs dans la DB pour l'UI

### 8. Avantages de cette Architecture

1. ✅ **Non-bloquant** : Le frontend n'attend plus les réponses
2. ✅ **Monitoring** : Progression visible en temps réel
3. ✅ **Annulation** : Possibilité d'annuler à tout moment
4. ✅ **Persistance** : Les jobs survivent aux redémarrages
5. ✅ **Scalabilité** : Facile d'ajouter plus de workers
6. ✅ **Logs** : Tous les logs sont disponibles dans l'UI
7. ✅ **Résilience** : Les erreurs n'interrompent pas tout le processus

### 9. Plan d'Implémentation

#### Phase 1 : Backend (Base)
1. Créer `ScrapingQueueManager` avec ThreadPoolExecutor
2. Créer les endpoints `/api/scrape/jobs/*`
3. Intégrer avec le système de jobs existant dans `main.py`
4. Ajouter la persistance dans SQLite

#### Phase 2 : Frontend (Base)
1. Modifier `scrapeAllSources()` pour créer un job
2. Créer la page `/jobs` pour le monitoring
3. Implémenter le polling pour les mises à jour
4. Ajouter les boutons d'annulation

#### Phase 3 : Améliorations
1. Ajouter SSE pour les logs en temps réel
2. Ajouter des statistiques (temps moyen, taux de succès)
3. Ajouter la possibilité de relancer un job échoué
4. Ajouter des notifications (email, webhook)

### 10. Migration depuis l'Ancien Système

- Garder les endpoints `/scrape/*` existants pour compatibilité
- Ajouter les nouveaux endpoints `/api/scrape/jobs/*`
- Migrer progressivement le frontend vers le nouveau système
- Une fois migré, déprécier les anciens endpoints

## 📝 Notes Techniques

- **ThreadPoolExecutor** : Limite le nombre de scrapers simultanés (évite la surcharge)
- **Polling vs SSE** : Commencer par polling (plus simple), migrer vers SSE si nécessaire
- **Timeout** : Ajouter des timeouts sur chaque requête HTTP dans les scrapers
- **Retry** : Implémenter un système de retry pour les échecs temporaires
- **Rate limiting** : Respecter les limites des APIs externes

## 🔄 Alternatives Considérées

1. **WebSockets** : Plus complexe que SSE, pas nécessaire pour ce cas d'usage
2. **Celery** : Trop complexe pour commencer, peut être ajouté plus tard si besoin
3. **Background Tasks FastAPI** : Limité, pas de persistance ni de monitoring facile

## ✅ Conclusion

Cette architecture propose une solution progressive :
- **Court terme** : ThreadPoolExecutor + SQLite (simple, fonctionne immédiatement)
- **Long terme** : Migration vers Celery si besoin de plus de scalabilité

Le système reste compatible avec l'existant tout en ajoutant les fonctionnalités demandées.

