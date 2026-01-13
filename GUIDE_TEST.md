# Guide de Test - OVH Complaints Tracker

Ce guide vous explique comment tester le projet étape par étape.

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

### 4.4. Endpoints LinkedIn et Facebook

Ces endpoints retournent toujours 0 posts car ils ne sont pas implémentés (documentés dans le code).

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/scrape/linkedin?query=test&limit=10" -Method POST
# Résultat attendu : {"added": 0}
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

1. **Filtrage par source** : Sélectionnez X, Reddit, LinkedIn, ou Facebook
2. **Filtrage par sentiment** : Positive, Negative, Neutral
3. **Recherche** : Tapez du texte dans la barre de recherche
4. **Boutons de scraping** : 
   - "Scrape X" : Lance le scraping X
   - "Scrape Reddit" : Lance le scraping Reddit
   - "Refresh" : Rafraîchit la liste des posts

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
- ⚠️ `POST /scrape/linkedin` : Non implémenté (retourne 0)
- ⚠️ `POST /scrape/facebook` : Non implémenté (retourne 0)

### Base de données

La base de données SQLite est créée automatiquement dans `backend/data.db` lors du premier démarrage de l'API.

### Fonctionnalités

- ✅ Base de données SQLite
- ✅ Analyse de sentiment (VADER)
- ✅ Scraper X (snscrape)
- ✅ Scraper Reddit (PRAW/JSON fallback)
- ✅ Frontend dashboard
- ⚠️ Scraper LinkedIn (non implémenté)
- ⚠️ Scraper Facebook (non implémenté)

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

## Prochaines étapes

Après avoir testé le projet, vous pouvez :
1. Améliorer les scrapers
2. Ajouter de nouvelles fonctionnalités
3. Améliorer le frontend
4. Ajouter des tests unitaires

