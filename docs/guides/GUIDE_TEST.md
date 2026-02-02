# Guide de Test - OVH Complaints Tracker

Ce guide vous explique comment tester le projet étape par étape.

> **Note:** Ce projet a été développé **100% avec VibeCoding** (Cursor AI).

## Prérequis

- Python 3.11 ou supérieur
- Accès Internet (pour tester les scrapers)

## 1. Configuration de l'environnement

### Créer et activer l'environnement virtuel

```powershell
# Depuis la racine du projet (ovh-complaints-tracker)
cd ovh-complaints-tracker
py -3.11 -m venv .venv

# Activer l'environnement virtuel (PowerShell)
.venv\Scripts\Activate.ps1

# Si vous utilisez CMD
.venv\Scripts\activate.bat
```

### Installer les dépendances

```powershell
pip install --upgrade pip
pip install -r backend/requirements.txt
```

## 2. Test de la base de données

Tester que la base de données fonctionne correctement :

```powershell
cd backend
python test_db.py
```

**Résultat attendu :**
```
Initializing DB...
Inserting sample post...
Rows: [{'id': 1, 'source': 'test', 'author': 'tester', 'content': 'This is a test complaint about OVH domain issues', ...}]
```

## 3. Test du serveur API

### Lancer le serveur FastAPI

Depuis le dossier `backend/` :

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Le serveur devrait démarrer et afficher :
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Accéder à la documentation interactive

Ouvrez votre navigateur et allez à :
- **Documentation Swagger UI** : http://127.0.0.1:8000/docs
- **Documentation ReDoc** : http://127.0.0.1:8000/redoc

Vous pouvez tester les endpoints directement depuis l'interface Swagger !

## 4. Tester les endpoints API

### 4.1. Endpoint GET /posts

Récupérer les posts stockés dans la base de données :

**Via le navigateur :**
- http://127.0.0.1:8000/posts?limit=10

**Via PowerShell (Invoke-WebRequest) :**
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/posts?limit=10" | Select-Object -ExpandProperty Content
```

**Via curl (si disponible) :**
```bash
curl "http://127.0.0.1:8000/posts?limit=10"
```

### 4.2. Endpoint POST /scrape/x

Scraper des tweets de X (Twitter) :

**Via Swagger UI (recommandé) :**
- Allez sur http://127.0.0.1:8000/docs
- Trouvez l'endpoint `POST /scrape/x`
- Cliquez sur "Try it out"
- Entrez les paramètres :
  - `query`: "ovh domain" (ou votre recherche)
  - `limit`: 10
- Cliquez sur "Execute"

**Via PowerShell :**
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/x?query=ovh%20domain&limit=10" -Method POST
```

**Note :** Le scraper X peut échouer si snscrape est bloqué par Twitter. C'est normal.

### 4.3. Endpoint POST /scrape/reddit

Scraper des posts Reddit :

**Via Swagger UI :**
- http://127.0.0.1:8000/docs
- Endpoint `POST /scrape/reddit`
- Paramètres : `query="ovh domain"`, `limit=10`

**Via PowerShell :**
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/reddit?query=ovh%20domain&limit=10" -Method POST
```

### 4.4. Endpoint POST /generate-improvement-ideas

Générer des idées d'amélioration produit avec LLM :

**Via Swagger UI :**
- http://127.0.0.1:8000/docs
- Endpoint `POST /generate-improvement-ideas`
- Body: `{"posts": [...], "max_ideas": 5}`

**Via PowerShell :**
```powershell
$body = @{
    posts = @(
        @{
            content = "OVH support is too slow"
            sentiment_label = "negative"
            source = "Twitter"
        }
    )
    max_ideas = 5
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://127.0.0.1:8000/generate-improvement-ideas" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Note :** Nécessite une clé API LLM (OVH_API_KEY). Sinon, utilise un fallback basé sur des règles.

### 4.5. Endpoint POST /admin/cleanup-duplicates

Nettoyer les doublons dans la base de données :

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/admin/cleanup-duplicates" -Method POST
```

**Résultat attendu :**
```json
{"deleted": 5, "message": "Successfully removed 5 duplicate posts from database"}
```

## 5. Test du frontend

### Lancer un serveur HTTP simple

Ouvrez un nouveau terminal (gardez le serveur API en cours d'exécution) :

```powershell
cd frontend
python -m http.server 8080
```

### Accéder au dashboard

Ouvrez votre navigateur :
- http://localhost:8080

Le dashboard affichera :
- Des données mock si l'API n'est pas accessible
- Les vrais posts si l'API est accessible (http://127.0.0.1:8000)

### Fonctionnalités à tester dans le frontend

1. **Filtrage par source** : Sélectionnez X, Reddit, GitHub, Stack Overflow, etc.
2. **Filtrage par sentiment** : Positive, Negative, Neutral
3. **Filtrage par produit** : Domain, VPS, Hosting, Cloud, etc.
4. **Recherche** : Tapez du texte dans la barre de recherche (recherche dans contenu, auteur, URL)
5. **Timeline & Histogram** : Cliquez sur "📈 View Timeline & Histogram" pour voir les graphiques
6. **Backlog** : Cliquez sur "📋 Backlog" pour ouvrir le panneau latéral
   - Ajoutez des commentaires sous chaque post
   - Basculez entre vue carte et vue liste
   - Générez des idées d'amélioration avec "💡 Generate Ideas"
7. **Boutons de scraping** : 
   - "🆕 Scrape New Data" : Lance tous les scrapers
   - Boutons individuels : Scrape X, Reddit, GitHub, etc.
8. **Preview** : Cliquez sur "👁️ Preview" pour voir le contenu complet d'un post
9. **Light/Dark Mode** : Utilisez le bouton 🌓 pour changer de thème

## 6. Test du scraper X (standalone)

Tester le scraper X indépendamment de l'API :

```powershell
cd backend
python run_scrape_x.py
```

**Note :** Cela peut prendre du temps et peut échouer si snscrape est bloqué.

## 7. Vérification de l'état du projet

### Endpoints disponibles

- ✅ `GET /posts` : Récupérer les posts (fonctionne)
- ✅ `POST /scrape/x` : Scraper X/Twitter (peut être bloqué par Twitter)
- ✅ `POST /scrape/reddit` : Scraper Reddit (fonctionne avec limite de taux)
- ✅ `POST /scrape/github` : Scraper GitHub Issues
- ✅ `POST /scrape/stackoverflow` : Scraper Stack Overflow
- ✅ `POST /scrape/trustpilot` : Scraper Trustpilot reviews
- ✅ `POST /generate-improvement-ideas` : Générer des idées avec LLM
- ✅ `POST /admin/cleanup-duplicates` : Nettoyer les doublons
- ✅ `POST /admin/cleanup-hackernews-posts` : Supprimer les posts Hacker News

### Base de données

La base de données PostgreSQL est initialisée automatiquement lors du premier démarrage de l'API via `app.database.init_db()`.

> **Note :** L'application utilise PostgreSQL depuis janvier 2026 (migration complète depuis DuckDB). Voir [Migration PostgreSQL](../MIGRATION_POSTGRESQL.md) pour plus de détails.

### Fonctionnalités

- ✅ Base de données DuckDB avec index
- ✅ Analyse de sentiment (VADER)
- ✅ Détection automatique de doublons (URL + contenu+auteur+source)
- ✅ Scraper X (Nitter instances)
- ✅ Scraper Reddit (RSS feeds)
- ✅ Scraper GitHub, Stack Overflow, Trustpilot
- ✅ Frontend dashboard avec filtres avancés
- ✅ Backlog sidebar avec commentaires
- ✅ Génération d'idées avec LLM (OVH AI Endpoints)
- ✅ Timeline & Histogram avec pie chart
- ✅ Product labeling automatique
- ✅ Light/Dark mode
- ✅ Post preview modal

## Dépannage

### Erreur "Module not found"

Assurez-vous que l'environnement virtuel est activé et que les dépendances sont installées :
```powershell
pip install -r backend/requirements.txt
```

### Erreur de port déjà utilisé

Si le port 8000 est déjà utilisé, changez-le :
```powershell
python -m uvicorn app.main:app --reload --port 8001
```
N'oubliez pas de mettre à jour l'URL dans le frontend (`index.html`) si vous changez le port.

### Le scraper X ne fonctionne pas

C'est normal. Twitter bloque souvent snscrape. Les alternatives :
- Utiliser l'API Twitter officielle (requiert un token)
- Utiliser des données de test

### Le scraper Reddit ne retourne pas de résultats

- Vérifiez votre connexion Internet
- Reddit peut limiter les requêtes (rate limiting)
- Essayez avec des credentials Reddit (voir README.md)

## 8. Test de la détection de doublons

Vérifier que les posts dupliqués ne sont pas insérés :

```powershell
cd backend
python -c "
from app import db
db.init_db()
# Insert first post
result1 = db.insert_post({
    'source': 'test',
    'author': 'testuser',
    'content': 'Test content',
    'url': 'https://example.com/post1',
    'created_at': '2026-01-13T10:00:00',
    'sentiment_score': -0.5,
    'sentiment_label': 'negative'
})
print(f'First insert: {result1}')  # Should be True

# Try to insert same URL again
result2 = db.insert_post({
    'source': 'test',
    'author': 'testuser2',
    'content': 'Different content',
    'url': 'https://example.com/post1',  # Same URL
    'created_at': '2026-01-13T11:00:00',
    'sentiment_score': -0.3,
    'sentiment_label': 'negative'
})
print(f'Duplicate insert: {result2}')  # Should be False
"
```

**Résultat attendu :**
```
First insert: True
Duplicate insert: False
```

## 9. Test des jobs en arrière-plan

Tester le système de jobs pour le scraping de keywords multiples :

### 9.1. Démarrer un job

```powershell
$body = @{
    keywords = @("OVH", "domain")
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/keywords?limit=10&concurrency=2&delay=0.5" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Résultat attendu :**
```json
{"job_id": "uuid-123-456-789"}
```

### 9.2. Vérifier le statut du job

```powershell
$jobId = "uuid-123-456-789"  # Remplacer par l'ID retourné
Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/jobs/$jobId" | Select-Object -ExpandProperty Content
```

**Résultat attendu :**
```json
{
  "id": "uuid-123-456-789",
  "status": "running",
  "progress": {"total": 12, "completed": 5},
  "results": [{"added": 3}, {"added": 2}],
  "errors": []
}
```

### 9.3. Annuler un job

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/jobs/$jobId/cancel" -Method POST
```

## 10. Test des index de base de données

Vérifier que les index sont créés correctement :

```powershell
cd backend
python -c "
from app.db import get_db_connection

conn, is_duckdb = get_db_connection()
c = conn.cursor()
c.execute(\"SELECT indexname FROM pg_indexes WHERE tablename='posts'\")
indexes = c.fetchall()
print('Indexes on posts table:')
for idx in indexes:
    print(f'  - {idx[0]}')
conn.close()
"
```

> **Note :** L'application utilise PostgreSQL. La syntaxe pour vérifier les index utilise `pg_indexes`.

**Résultat attendu :**
```
Indexes on posts table:
  - idx_posts_source
  - idx_posts_sentiment_label
  - idx_posts_created_at
  - idx_posts_language
  - idx_posts_url
```

## 11. Test de performance

Tester les performances avec un grand nombre de posts :

```powershell
cd backend
python -c "
import time
from app import db

db.init_db()

# Insert 1000 test posts
start = time.time()
for i in range(1000):
    db.insert_post({
        'source': 'test',
        'author': f'user{i}',
        'content': f'Test content {i}',
        'url': f'https://example.com/post{i}',
        'created_at': '2026-01-13T10:00:00',
        'sentiment_score': -0.5,
        'sentiment_label': 'negative'
    })

insert_time = time.time() - start
print(f'Inserted 1000 posts in {insert_time:.2f}s')

# Test query performance
start = time.time()
posts = db.get_posts(limit=100, offset=0, language=None)
query_time = time.time() - start
print(f'Queried 100 posts in {query_time:.4f}s')
print(f'Average: {query_time/100*1000:.2f}ms per post')
"
```

**Résultat attendu :**
- Insertion : < 5 secondes pour 1000 posts
- Requête : < 0.1 seconde pour 100 posts

## 12. Test d'intégration complet

Scénario de test end-to-end :

```powershell
# 1. Démarrer le serveur (dans un terminal)
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 2. Dans un autre terminal, exécuter le test
cd backend
python -c "
import httpx
import time

API_BASE = 'http://127.0.0.1:8000'

# Test 1: Scraper Trustpilot
print('1. Testing Trustpilot scraper...')
r = httpx.post(f'{API_BASE}/scrape/trustpilot?limit=5', timeout=30)
print(f'   Status: {r.status_code}, Added: {r.json()[\"added\"]}')

# Test 2: Vérifier les posts
print('2. Checking posts...')
r = httpx.get(f'{API_BASE}/posts?limit=10')
posts = r.json()
print(f'   Found {len(posts)} posts')

# Test 3: Démarrer un job
print('3. Starting background job...')
r = httpx.post(f'{API_BASE}/scrape/keywords?limit=5&concurrency=1&delay=0.1',
               json={'keywords': ['OVH']}, timeout=5)
job_id = r.json()['job_id']
print(f'   Job ID: {job_id}')

# Test 4: Vérifier le statut du job
print('4. Checking job status...')
time.sleep(2)
r = httpx.get(f'{API_BASE}/scrape/jobs/{job_id}')
status = r.json()
print(f'   Status: {status[\"status\"]}, Progress: {status[\"progress\"]}')

print('\\n✅ Integration test completed!')
"
```

## Prochaines étapes

Après avoir testé le projet, vous pouvez :
1. Améliorer les scrapers
2. Ajouter de nouvelles fonctionnalités
3. Améliorer le frontend
4. Ajouter des tests unitaires
5. Tester les performances avec de plus gros volumes de données
6. Vérifier la détection de doublons avec des données réelles


