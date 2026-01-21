# 🚀 PLAN D'AMÉLIORATION - OVH Complaints Tracker

**Date:** 15 Janvier 2026  
**Basé sur:** [SECURITY_AUDIT.md](SECURITY_AUDIT.md)  
**Priorité:** Phase 1 = CRITIQUE (faire immédiatement)

---

## 🎯 PHASE 1: SÉCURITÉ CRITIQUE (1-2 jours)

### 1.1 Restreindre CORS ✅ PRIORITÉ MAX

**Fichier:** `backend/app/main.py`

```python
# Remplacer lignes 32-38
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://127.0.0.1:5500",
        "file://",  # Pour développement local
        # TODO: Ajouter votre domaine de production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    max_age=600,
)
```

**Test:**
```bash
# Devrait échouer (domaine non autorisé)
curl -H "Origin: https://evil.com" http://localhost:8000/posts
```

---

### 1.2 Validation Pydantic sur Tous les Endpoints ✅

**Fichier:** `backend/app/main.py`

Ajouter après les imports:
```python
import re
from pydantic import BaseModel, Field, validator

class ScrapeRequest(BaseModel):
    """Validated scrape request with security checks."""
    query: str = Field(
        default="OVH",
        min_length=1,
        max_length=100,
        description="Search query (alphanumeric + spaces/dashes only)"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Number of results (max 500)"
    )
    
    @validator('query')
    def validate_query_security(cls, v):
        """Prevent injection attacks and path traversal."""
        # Allow only safe characters
        if not re.match(r'^[a-zA-Z0-9\s\-_\.àéèêëïôùûçÀÉÈÊËÏÔÙÛÇ]+$', v):
            raise ValueError(
                'Query contains invalid characters. '
                'Allowed: letters, numbers, spaces, hyphens, dots, accents'
            )
        # Block path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Query contains forbidden patterns')
        return v.strip()


class KeywordsPayload(BaseModel):
    """Validated keywords list."""
    keywords: List[str] = Field(..., min_items=1, max_items=10)
    
    @validator('keywords')
    def validate_keywords(cls, v):
        """Validate each keyword."""
        validated = []
        for keyword in v:
            keyword = str(keyword).strip()
            if not keyword:
                continue
            if len(keyword) > 100:
                raise ValueError('Each keyword must be <= 100 characters')
            if not re.match(r'^[a-zA-Z0-9\s\-_\.àéèêëïôùûçÀÉÈÊËÏÔÙÛÇ]+$', keyword):
                raise ValueError(f'Invalid keyword: {keyword}')
            validated.append(keyword)
        if len(validated) == 0:
            raise ValueError('At least one valid keyword required')
        return validated
```

Modifier TOUS les endpoints:
```python
@app.post("/scrape/x", response_model=ScrapeResult)
async def scrape_x_endpoint(request: ScrapeRequest):  # ← Ajouter request: ScrapeRequest
    """Scrape X/Twitter with validated inputs."""
    try:
        items = x_scraper.scrape_x(request.query, limit=request.limit)
        added = process_and_save_items(items)  # Helper function
        return ScrapeResult(added=added)
    except Exception as e:
        logger.error(f"X scraper failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Scraping failed. Please try again later."
        )
```

Répéter pour:
- `/scrape/stackoverflow`
- `/scrape/github`
- `/scrape/hackernews`
- `/scrape/news`
- `/scrape/trustpilot`

---

### 1.3 Rate Limiting ✅

**Installation:**
```bash
pip install slowapi
```

**Ajout dans requirements.txt:**
```
slowapi==0.1.9
```

**Configuration:** `backend/app/main.py`
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

# Après la création de l'app
limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Appliquer aux endpoints de scraping
@app.post("/scrape/x", response_model=ScrapeResult)
@limiter.limit("10/minute")  # Max 10 requêtes par minute
async def scrape_x_endpoint(request: Request, req: ScrapeRequest):
    # ... code existant
```

**Test:**
```python
# test_rate_limiting.py
import httpx
import time

for i in range(15):
    response = httpx.post('http://localhost:8000/scrape/x', json={"query": "test"})
    print(f"Request {i+1}: {response.status_code}")
    if response.status_code == 429:
        print("✅ Rate limiting works!")
        break
```

---

### 1.4 Protection des Clés API ✅

**Créer `.env`:**
```bash
# .env (NE JAMAIS COMMITTER)
TRUSTPILOT_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_optional
```

**Créer `.env.example`:**
```bash
# .env.example (à committer)
# Trustpilot API key (optional, for enhanced scraping)
TRUSTPILOT_API_KEY=

# GitHub Personal Access Token (optional, increases rate limits)
GITHUB_TOKEN=
```

**Ajouter à `.gitignore`:**
```gitignore
# Environment variables
.env
.env.local
.env.*.local
*.env

# Database
*.db
data.db

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
```

**Installer python-dotenv:**
```bash
pip install python-dotenv
```

**Charger dans `main.py`:**
```python
from dotenv import load_dotenv
import os

# Au tout début du fichier, avant les imports locaux
load_dotenv()  # Charge .env automatiquement
```

---

### 1.5 Masquer les Erreurs Système ✅

**Configurer le logging:** `backend/app/main.py`
```python
import logging
from logging.handlers import RotatingFileHandler

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/app.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**Remplacer tous les print() par logger:**
```python
# ❌ Avant
print(f"[X SCRAPER] Starting...")
print(f"[X SCRAPER ERROR] {e}")
import traceback
traceback.print_exc()

# ✅ Après
logger.info("[X SCRAPER] Starting...")
logger.error("X scraper failed", exc_info=True)  # Log détaillé en interne
raise HTTPException(500, "Scraping failed")  # Message générique pour l'utilisateur
```

**Créer dossier logs:**
```bash
mkdir -p logs
echo "logs/" >> .gitignore
```

---

## 🔧 PHASE 2: QUALITÉ DU CODE (2-3 jours)

### 2.1 Refactoriser Code Dupliqué ✅

**Créer `backend/app/utils/helpers.py`:**
```python
"""Helper functions to reduce code duplication."""
import logging
from typing import List, Dict
from ..analysis import sentiment
from .. import db

logger = logging.getLogger(__name__)


def process_and_save_items(items: List[Dict]) -> int:
    """
    Process sentiment analysis and save items to database.
    
    Args:
        items: List of scraped items (dict with source, author, content, etc.)
    
    Returns:
        Number of items successfully saved
    """
    if not items:
        return 0
    
    added = 0
    for item in items:
        try:
            # Skip sentiment analysis if already done by scraper
            if not item.get('sentiment_score'):
                analysis = sentiment.analyze(item.get('content') or '')
                item['sentiment_score'] = analysis['score']
                item['sentiment_label'] = analysis['label']
            
            # Insert into database
            db.insert_post({
                'source': item.get('source'),
                'author': item.get('author'),
                'content': item.get('content'),
                'url': item.get('url'),
                'created_at': item.get('created_at'),
                'sentiment_score': item.get('sentiment_score'),
                'sentiment_label': item.get('sentiment_label'),
                'language': item.get('language', 'unknown'),
            })
            added += 1
            
        except Exception as e:
            logger.error(f"Failed to save item from {item.get('source')}: {e}")
            continue
    
    logger.info(f"Saved {added}/{len(items)} items to database")
    return added


def create_scraper_endpoint(scraper_func):
    """
    Decorator to create standardized scraper endpoints.
    Reduces boilerplate code.
    """
    async def endpoint(request: ScrapeRequest):
        try:
            items = scraper_func(request.query, limit=request.limit)
            added = process_and_save_items(items)
            return ScrapeResult(added=added)
        except Exception as e:
            logger.error(f"Scraper {scraper_func.__name__} failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Scraping failed. Please try again later."
            )
    return endpoint
```

**Simplifier les endpoints dans `main.py`:**
```python
from .utils.helpers import process_and_save_items

@app.post("/scrape/x", response_model=ScrapeResult)
@limiter.limit("10/minute")
async def scrape_x_endpoint(request: Request, req: ScrapeRequest):
    """Scrape X/Twitter."""
    items = x_scraper.scrape_x(req.query, limit=req.limit)
    added = process_and_save_items(items)
    return ScrapeResult(added=added)

# Répéter pour les autres endpoints (moins de 10 lignes chacun!)
```

---

### 2.2 Ajouter Index sur la Base de Données ✅

**Modifier `backend/app/db.py`:**
```python
def init_db():
    """Initialize database with optimized indexes."""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            author TEXT,
            content TEXT,
            url TEXT,
            created_at TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            language TEXT DEFAULT 'unknown'
        )
    ''')
    
    # Add indexes for faster queries
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_source 
        ON posts(source)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_sentiment 
        ON posts(sentiment_label)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_created 
        ON posts(created_at DESC)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_language 
        ON posts(language)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_posts_source_date 
        ON posts(source, created_at DESC)
    ''')
    
    # Other tables...
    c.execute('''CREATE TABLE IF NOT EXISTS saved_queries ...''')
    c.execute('''CREATE TABLE IF NOT EXISTS jobs ...''')
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized with optimized indexes")
```

**Test de performance:**
```python
# test_db_performance.py
import time
import sqlite3

conn = sqlite3.connect('data.db')
c = conn.cursor()

# Test query performance
start = time.time()
c.execute("SELECT * FROM posts WHERE source = 'Trustpilot' ORDER BY created_at DESC LIMIT 100")
results = c.fetchall()
elapsed = time.time() - start

print(f"Query returned {len(results)} rows in {elapsed:.3f}s")
# Avec index: < 0.001s
# Sans index: > 0.1s (100x plus lent!)
```

---

### 2.3 Tests de Sécurité ✅

**Créer `tests/test_security.py`:**
```python
"""Security tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestInputValidation:
    """Test input validation prevents injection attacks."""
    
    def test_rejects_sql_injection_attempt(self):
        """Should reject SQL injection in query."""
        response = client.post("/scrape/x", json={
            "query": "'; DROP TABLE posts; --",
            "limit": 50
        })
        assert response.status_code == 422
        assert "invalid characters" in response.json()['detail'][0]['msg'].lower()
    
    def test_rejects_path_traversal(self):
        """Should reject path traversal attempts."""
        response = client.post("/scrape/x", json={
            "query": "../../etc/passwd",
            "limit": 50
        })
        assert response.status_code == 422
    
    def test_enforces_limit_maximum(self):
        """Should reject limit > 500."""
        response = client.post("/scrape/x", json={
            "query": "test",
            "limit": 999999
        })
        assert response.status_code == 422
    
    def test_rejects_xss_attempt(self):
        """Should reject XSS in query."""
        response = client.post("/scrape/x", json={
            "query": "<script>alert('xss')</script>",
            "limit": 50
        })
        assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting works correctly."""
    
    def test_rate_limit_enforced(self):
        """Should return 429 after exceeding rate limit."""
        # Make 15 requests (limit is 10/minute)
        responses = []
        for i in range(15):
            response = client.post("/scrape/x", json={
                "query": "test",
                "limit": 1
            })
            responses.append(response.status_code)
        
        # At least one should be 429
        assert 429 in responses


class TestCORS:
    """Test CORS configuration."""
    
    def test_blocks_unauthorized_origin(self):
        """Should block requests from unauthorized domains."""
        response = client.get(
            "/posts",
            headers={"Origin": "https://evil.com"}
        )
        # CORS error should occur
        assert "access-control-allow-origin" not in response.headers or \
               "https://evil.com" not in response.headers.get("access-control-allow-origin", "")
    
    def test_allows_localhost(self):
        """Should allow requests from localhost."""
        response = client.get(
            "/posts",
            headers={"Origin": "http://localhost:5500"}
        )
        assert response.status_code == 200


class TestErrorHandling:
    """Test error messages don't leak sensitive info."""
    
    def test_no_stack_traces_in_response(self):
        """Should not expose stack traces to users."""
        # Force an error
        response = client.post("/scrape/x", json={
            "query": "test_error_trigger_xyz_123",
            "limit": 1
        })
        
        # Check response doesn't contain file paths or internal details
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert ".py" not in response_text
        assert "backend/app" not in response_text
```

**Exécuter les tests:**
```bash
pytest tests/test_security.py -v
```

---

## 🎨 PHASE 3: PRODUCTION-READY (3-5 jours)

### 3.1 Configuration HTTPS/SSL

**Pour production avec nginx:**
```nginx
# /etc/nginx/sites-available/ovh-tracker
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Ou avec Caddy (plus simple):**
```
# Caddyfile
your-domain.com {
    reverse_proxy localhost:8000
}
```

---

### 3.2 Monitoring & Alerting

**Installer Sentry pour monitoring d'erreurs:**
```bash
pip install sentry-sdk[fastapi]
```

**Configurer dans `main.py`:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment="production",
)
```

---

### 3.3 CI/CD avec Checks de Sécurité

**Créer `.github/workflows/security.yml`:**
```yaml
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install bandit safety
      
      - name: Run Bandit (security scanner)
        run: bandit -r backend/ -f json -o bandit-report.json
      
      - name: Run Safety (dependency checker)
        run: safety check --json
      
      - name: Run tests
        run: pytest tests/ --cov=backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

### 3.4 Scanner de Vulnérabilités

**Installation:**
```bash
pip install bandit safety
```

**Exécuter:**
```bash
# Scan du code
bandit -r backend/ -ll

# Vérifier les dépendances
safety check --file requirements.txt

# Générer rapport
bandit -r backend/ -f html -o security-report.html
```

---

## 📋 CHECKLIST D'IMPLÉMENTATION

### Phase 1 (CRITIQUE - 1-2 jours)
- [ ] 1.1 Restreindre CORS
- [ ] 1.2 Validation Pydantic sur tous endpoints
- [ ] 1.3 Rate limiting avec slowapi
- [ ] 1.4 Créer .env + .gitignore
- [ ] 1.5 Masquer erreurs système

### Phase 2 (IMPORTANT - 2-3 jours)
- [ ] 2.1 Refactoriser code dupliqué
- [ ] 2.2 Ajouter index DB
- [ ] 2.3 Tests de sécurité
- [ ] 2.4 Standardiser logging
- [ ] 2.5 Documentation OpenAPI

### Phase 3 (PRODUCTION - 3-5 jours)
- [ ] 3.1 Configuration HTTPS/SSL
- [ ] 3.2 Monitoring (Sentry)
- [ ] 3.3 CI/CD avec security checks
- [ ] 3.4 Scanner de vulnérabilités
- [ ] 3.5 Backup automatique DB

---

## 🧪 TESTS APRÈS CHAQUE PHASE

### Après Phase 1:
```bash
# Test CORS
curl -H "Origin: https://evil.com" http://localhost:8000/posts

# Test validation
curl -X POST http://localhost:8000/scrape/x \
  -H "Content-Type: application/json" \
  -d '{"query":"'; DROP TABLE posts; --","limit":50}'

# Test rate limiting
for i in {1..15}; do curl -X POST http://localhost:8000/scrape/x; done
```

### Après Phase 2:
```bash
pytest tests/ --cov=backend --cov-report=html
bandit -r backend/
safety check
```

### Après Phase 3:
```bash
# Test HTTPS
curl https://your-domain.com/posts

# Test monitoring
# Déclencher une erreur et vérifier Sentry
```

---

## 📊 RÉSULTATS ATTENDUS

| Métrique | Avant | Après Phase 1 | Après Phase 3 |
|----------|-------|---------------|---------------|
| **Score Sécurité** | 55/100 | 85/100 | 95/100 |
| **Vulnérabilités Critiques** | 5 | 0 | 0 |
| **Code Dupliqué** | 300 lignes | 50 lignes | 0 lignes |
| **Couverture Tests** | 15% | 40% | 80% |
| **Temps Requête DB** | 100ms | 10ms | 5ms |

---

## 🆘 SUPPORT

En cas de problème pendant l'implémentation:

1. Vérifier les logs: `tail -f logs/app.log`
2. Tester individuellement: `pytest tests/test_security.py::test_name -v`
3. Scanner sécurité: `bandit -r backend/`
4. Vérifier dépendances: `safety check`

---

**Prochaine étape:** Commencer par Phase 1, point 1.1 (CORS) 🚀
