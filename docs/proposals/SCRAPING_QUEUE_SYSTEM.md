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

### 4. Frontend : Amélioration de la Page Logs Existante

#### Page existante : `/logs` (`frontend/logs.html`)

**État actuel :**
- ✅ Affiche les logs de scraping depuis `/api/logs`
- ✅ Auto-refresh toutes les 5 secondes
- ✅ Filtres par source et niveau
- ✅ Statistiques (total, erreurs, warnings, success)
- ✅ Affichage des logs avec timestamps et sources

**Améliorations à apporter :**

1. **Section "Jobs en cours"** (nouvelle section en haut de la page)
   - Liste des jobs actifs avec leur progression
   - Barre de progression pour chaque job
   - Statut (pending, running, completed, failed, cancelled)
   - Bouton "Cancel" pour chaque job
   - Bouton "Cancel All" global
   - Lien vers les logs du job

2. **Intégration des logs de jobs**
   - Les logs des jobs apparaissent dans la liste des logs existante
   - Filtre par `job_id` pour voir les logs d'un job spécifique
   - Badge "Job #1234" sur les logs associés à un job

3. **Bouton "Scrape New Data" amélioré**
   - Crée un job au lieu de lancer directement
   - Notification toast : "Scraping démarré, job #1234 créé"
   - Option de redirection automatique vers `/logs` pour voir le job

#### Workflow utilisateur amélioré

```
1. Utilisateur clique sur "Scrape New Data" (page Feedbacks Collection)
   ↓
2. Frontend envoie POST /api/scrape/jobs
   ↓
3. Backend crée un job et retourne job_id
   ↓
4. Frontend affiche notification toast :
   "✅ Scraping démarré (Job #1234)"
   "📋 Voir les logs" [bouton]
   ↓
5. Option A : Utilisateur reste sur la page
   - Le scraping tourne en arrière-plan
   - Pas de blocage de la page
   ↓
6. Option B : Utilisateur clique sur "Voir les logs"
   - Redirection vers /logs
   - Section "Jobs en cours" affiche le job actif
   - Logs apparaissent en temps réel avec auto-refresh
   ↓
7. Sur la page /logs :
   - Section "Jobs en cours" en haut
   - Barre de progression visible
   - Bouton "Cancel" disponible
   - Logs du job apparaissent dans la liste
   ↓
8. Quand terminé :
   - Job passe en "completed"
   - Résultats affichés dans la section jobs
   - Logs complets disponibles dans la liste
   - Bouton "Retour à la collection" pour voir les nouveaux posts
```

#### Modifications de `frontend/logs.html`

**Ajouts à faire :**

1. **Nouvelle section "Active Jobs"** (avant les stats)
```html
<div class="active-jobs-section">
    <h2>🔄 Jobs en cours</h2>
    <div id="activeJobsContainer">
        <!-- Jobs actifs affichés ici -->
    </div>
    <button id="cancelAllBtn" class="danger" onclick="cancelAllJobs()" style="display:none;">
        ❌ Cancel All Jobs
    </button>
</div>
```

2. **Composant Job Card**
```html
<div class="job-card" data-job-id="...">
    <div class="job-header">
        <span class="job-id">Job #1234</span>
        <span class="job-status running">Running</span>
        <button onclick="cancelJob('...')">Cancel</button>
    </div>
    <div class="job-progress">
        <div class="progress-bar">
            <div class="progress-fill" style="width: 45%"></div>
        </div>
        <span class="progress-text">8/20 tasks completed</span>
    </div>
    <div class="job-current-task">
        Scraping X/Twitter for 'ovh vps'...
    </div>
    <div class="job-results">
        <span>✅ X: 10 posts</span>
        <span>✅ GitHub: 5 posts</span>
    </div>
</div>
```

3. **Filtre par job_id** (ajout dans les contrôles)
```html
<select id="jobFilter" onchange="loadLogs()">
    <option value="">Tous les jobs</option>
    <!-- Options générées dynamiquement -->
</select>
```

4. **Fonctions JavaScript à ajouter**
```javascript
// Charger les jobs actifs
async function loadActiveJobs() {
    const response = await fetch(`${API_BASE}/api/scrape/jobs?status=running`);
    const data = await response.json();
    displayActiveJobs(data.jobs);
}

// Afficher les jobs actifs
function displayActiveJobs(jobs) {
    // Afficher dans la section active-jobs-section
    // Afficher/masquer le bouton "Cancel All"
}

// Annuler un job
async function cancelJob(jobId) {
    await fetch(`${API_BASE}/api/scrape/jobs/${jobId}/cancel`, { method: 'POST' });
    loadActiveJobs();
}

// Annuler tous les jobs
async function cancelAllJobs() {
    await fetch(`${API_BASE}/api/scrape/jobs/cancel-all`, { method: 'POST' });
    loadActiveJobs();
}

// Polling pour les jobs actifs (toutes les 2 secondes)
setInterval(loadActiveJobs, 2000);
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

#### Fichiers à modifier

**`frontend/logs.html`** (améliorer la page existante)
- Ajouter la section "Active Jobs" en haut
- Ajouter les fonctions JavaScript pour gérer les jobs
- Intégrer les logs de jobs dans la liste existante
- Ajouter le filtre par job_id

**`frontend/index.html`** (modifier)
- Modifier `scrapeAllSources()` pour créer un job au lieu de lancer directement
- Afficher une notification toast avec lien vers `/logs`
- Ne plus bloquer la page pendant le scraping

**Modifications détaillées :**

1. **`frontend/logs.html`** - Ajouter après la ligne 475 (après le header) :
```html
<!-- Section Active Jobs -->
<div class="active-jobs-section" id="activeJobsSection" style="display:none;">
    <div style="background: var(--bg-card); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <h2 style="margin: 0; color: var(--accent-primary);">🔄 Jobs en cours</h2>
            <button id="cancelAllBtn" class="danger" onclick="cancelAllJobs()" style="display:none;">
                ❌ Cancel All
            </button>
        </div>
        <div id="activeJobsContainer">
            <!-- Jobs actifs affichés ici -->
        </div>
    </div>
</div>
```

2. **`frontend/logs.html`** - Ajouter dans les contrôles (ligne 456) :
```html
<select id="jobFilter" onchange="loadLogs()" style="display:none;">
    <option value="">Tous les jobs</option>
</select>
```

3. **`frontend/logs.html`** - Ajouter les fonctions JavaScript (avant la fermeture du script) :
```javascript
// Gestion des jobs actifs
let activeJobsInterval = null;

async function loadActiveJobs() {
    try {
        const response = await fetch(`${API_BASE}/api/scrape/jobs?status=running`);
        if (!response.ok) return;
        const data = await response.json();
        const jobs = data.jobs || [];
        
        if (jobs.length > 0) {
            document.getElementById('activeJobsSection').style.display = 'block';
            document.getElementById('cancelAllBtn').style.display = 'inline-block';
            displayActiveJobs(jobs);
        } else {
            document.getElementById('activeJobsSection').style.display = 'none';
            document.getElementById('cancelAllBtn').style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading active jobs:', error);
    }
}

function displayActiveJobs(jobs) {
    const container = document.getElementById('activeJobsContainer');
    container.innerHTML = jobs.map(job => {
        const progress = job.progress || { total: 0, completed: 0 };
        const percentage = progress.total > 0 ? (progress.completed / progress.total * 100) : 0;
        return `
            <div class="job-card" data-job-id="${job.job_id}" style="background: var(--bg-secondary); padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: bold; color: var(--accent-primary);">Job #${job.job_id.substring(0, 8)}</span>
                    <span class="job-status" style="padding: 4px 12px; border-radius: 4px; background: var(--info); color: white; font-size: 0.85em;">${job.status}</span>
                    <button onclick="cancelJob('${job.job_id}')" style="padding: 6px 12px; background: var(--error); color: white; border: none; border-radius: 4px; cursor: pointer;">Cancel</button>
                </div>
                <div class="job-progress" style="margin-bottom: 10px;">
                    <div style="background: rgba(0,0,0,0.3); height: 20px; border-radius: 10px; overflow: hidden;">
                        <div style="background: var(--accent-primary); height: 100%; width: ${percentage}%; transition: width 0.3s;"></div>
                    </div>
                    <span style="font-size: 0.9em; color: var(--text-secondary);">${progress.completed}/${progress.total} tasks</span>
                </div>
                ${job.progress?.current_task ? `<div style="font-size: 0.9em; color: var(--text-secondary);">${job.progress.current_task}</div>` : ''}
            </div>
        `;
    }).join('');
}

async function cancelJob(jobId) {
    if (!confirm(`Annuler le job #${jobId.substring(0, 8)} ?`)) return;
    try {
        await fetch(`${API_BASE}/api/scrape/jobs/${jobId}/cancel`, { method: 'POST' });
        loadActiveJobs();
    } catch (error) {
        alert(`Erreur: ${error.message}`);
    }
}

async function cancelAllJobs() {
    if (!confirm('Annuler tous les jobs en cours ?')) return;
    try {
        await fetch(`${API_BASE}/api/scrape/jobs/cancel-all`, { method: 'POST' });
        loadActiveJobs();
    } catch (error) {
        alert(`Erreur: ${error.message}`);
    }
}

// Charger les jobs actifs au chargement de la page
loadActiveJobs();

// Polling pour les jobs actifs (toutes les 2 secondes)
activeJobsInterval = setInterval(loadActiveJobs, 2000);
```

4. **`frontend/index.html`** - Modifier `scrapeAllSources()` :
```javascript
async function scrapeAllSources() {
    const keywords = loadKeywords();
    if (!keywords || keywords.length === 0) {
        showToast('Please add keywords before scraping', 'error');
        return;
    }
    
    try {
        // Créer un job au lieu de lancer directement
        const response = await fetch(`${API_BASE}/api/scrape/jobs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keywords: keywords,
                sources: ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin'],
                limit: 50,
                concurrency: 2
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to create scraping job');
        }
        
        const data = await response.json();
        const jobId = data.job_id;
        
        // Afficher notification avec lien vers les logs
        showToast(
            `✅ Scraping démarré (Job #${jobId.substring(0, 8)})`,
            'success',
            5000,
            () => window.location.href = '/logs'
        );
        
    } catch (error) {
        showToast(`Erreur: ${error.message}`, 'error');
    }
}
```

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

