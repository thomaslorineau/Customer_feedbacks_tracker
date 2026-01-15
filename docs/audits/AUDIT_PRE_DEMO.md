# 🔍 AUDIT COMPLET - PRÉPARATION DÉMO DÉVELOPPEURS SENIOR

**Date:** 2026-01-XX  
**Objectif:** Nettoyer et sécuriser le projet avant présentation  
**Statut:** ⏳ **EN ATTENTE DE VALIDATION**

---

## 📋 TABLE DES MATIÈRES

1. [Fichiers à supprimer](#1-fichiers-à-supprimer)
2. [Audit de sécurité](#2-audit-de-sécurité)
3. [Audit de code](#3-audit-de-code)
4. [Correctifs proposés](#4-correctifs-proposés)
5. [Tests E2E](#5-tests-e2e)

---

## 1. FICHIERS À SUPPRIMER

### 1.1 Tests obsolètes / temporaires (27 fichiers)

**Fichiers de test HackerNews (obsolètes - pas de scraper HN actif):**
- ❌ `backend/test_hn_api.py`
- ❌ `backend/test_hn_api_endpoint.py`
- ❌ `backend/test_hn_debug.py`
- ❌ `backend/test_hn_scraper.py`
- ❌ `backend/test_hn_simple.py`

**Fichiers de test Trustpilot (tests de debug):**
- ❌ `backend/test_api_trustpilot.py`
- ❌ `backend/test_check_db_trustpilot.py`
- ❌ `backend/test_find_real_reviews.py`
- ❌ `backend/test_find_review_urls.py`
- ❌ `backend/test_review_positions.py`
- ❌ `backend/test_trustpilot_direct.py`
- ❌ `backend/test_trustpilot_html.py`

**Fichiers de test généraux (obsolètes ou redondants):**
- ❌ `backend/test_api.py` (remplacé par scripts/ci_test_endpoints.py)
- ❌ `backend/test_check_unique_urls.py`
- ❌ `backend/test_complaint_scrapers.py` (ancien format)
- ❌ `backend/test_db.py` (tests basiques, redondants)
- ❌ `backend/test_direct_import.py`
- ❌ `backend/test_llm_config.py` (test unitaire simple)
- ❌ `backend/test_minimal.py`
- ❌ `backend/test_new_scrapers_e2e.py` (garder scripts/e2e_test_real_server.py à la place)
- ❌ `backend/test_port_8001.py`
- ❌ `backend/test_routes.py` (redondant)
- ❌ `backend/test_scrapers_qa.py` (ancien format)
- ❌ `test_google_news.py` (à la racine, obsolète)

**Scrapers non utilisés:**
- ❌ `backend/app/scraper/facebook.py` (non importé, non implémenté)
- ❌ `backend/app/scraper/linkedin.py` (non importé, non implémenté)

**Fichiers de debug:**
- ❌ `debug_server.py` (à la racine)
- ❌ `backend/backend.log` (fichier de log, doit être dans .gitignore)

### 1.2 Fichiers de configuration / scripts obsolètes

**Scripts de démarrage redondants:**
- ❌ `backend/minimal_app.py` (test minimal, non utilisé)
- ❌ `backend/run.py` (redondant avec start_server.ps1)
- ❌ `backend/run_safe.py` (redondant)
- ❌ `backend/run_scrape_x.py` (script de test ponctuel)
- ❌ `backend/simple_server.py` (redondant)
- ❌ `start_debug.bat` (debug uniquement)
- ❌ `startup_log.txt` (log temporaire)

**Fichiers de migration / fix temporaires:**
- ❌ `backend/app/fix_eu_countries.py` (script de migration ponctuel, déjà exécuté)
- ❌ `backend/app/migrate_add_country.py` (migration déjà appliquée)
- ❌ `populate_sample_data.py` (génération de données de test, non nécessaire en prod)

**Bases de données de test:**
- ❌ `backend/ovh_posts.db` (ancienne DB, remplacée par data.db)

### 1.3 Documentation obsolète / redondante

**Audits et rapports anciens (garder les plus récents):**
- ❓ `AUDIT.md` (garder si récent, sinon supprimer)
- ❓ `AUDIT_SCRAPERS.md` (garder - utile pour comprendre les scrapers)
- ❓ `CHANGES_APPLIED.md` (historique, peut être archivé)
- ❓ `EXECUTIVE_SUMMARY.md` (garder si récent)
- ❓ `FINAL_SUMMARY.md` (redondant ?)
- ❓ `FIXES_SCRAPERS.md` (garder - documentation des fixes)
- ❓ `IMPLEMENTATION.md` (garder si récent)
- ❓ `IMPROVEMENT_PLAN.md` (plan, peut être archivé)
- ❓ `PHASE1_COMPLETE.md` (historique)
- ❓ `PHASE2_COMPLETE.md` (historique)
- ❓ `SECURITY_AUDIT.md` (garder - référence)
- ❓ `SECURITY_AUDIT_PHASE2.md` (garder - référence)
- ❓ `SECURITY_OVERVIEW.md` (garder - référence)
- ❓ `STATUS.md` (garder si à jour)
- ❓ `URGENT_API_KEY.md` (alerte temporaire, peut être supprimé si résolu)

**Guides (garder les essentiels):**
- ✅ `README.md` (GARDER - essentiel)
- ✅ `GUIDE_TEST.md` (GARDER - utile)
- ✅ `GUIDE_API_KEYS.md` (GARDER - documentation)
- ✅ `QUICK_START.md` (GARDER - utile)
- ✅ `QUICK_START_LLM.md` (GARDER - documentation)
- ✅ `VERSIONING.md` (GARDER - documentation)
- ✅ `ARCHITECTURE.md` (GARDER - documentation)
- ✅ `backend/ANTI_BOT_GUIDE.md` (GARDER - documentation)
- ✅ `backend/GET_API_KEY.md` (GARDER - documentation)

### 1.4 Fichiers système / cache

**À ajouter au .gitignore (déjà ignorés mais vérifier):**
- ✅ `__pycache__/` (déjà dans .gitignore)
- ✅ `*.pyc` (déjà dans .gitignore)
- ✅ `*.log` (déjà dans .gitignore)
- ✅ `*.db` (déjà dans .gitignore)
- ✅ `backend/logs/` (déjà dans .gitignore)

**Fichiers à supprimer manuellement (pas dans Git):**
- ⚠️ Tous les dossiers `__pycache__/` (nettoyer avec `find . -type d -name __pycache__ -exec rm -r {} +`)
- ⚠️ Tous les fichiers `*.pyc` (nettoyer avec `find . -name "*.pyc" -delete`)

---

## 2. AUDIT DE SÉCURITÉ

### 2.1 ✅ Points positifs (déjà corrigés)

1. **CORS restreint** ✅
   - Configuration via variables d'environnement
   - Origines limitées (pas de `*`)

2. **Gestion des clés API** ✅
   - Variables d'environnement via `.env`
   - `.env` dans `.gitignore`
   - Masquage des clés dans les logs
   - Validation au démarrage

3. **Validation des entrées** ✅
   - Pydantic models avec contraintes
   - Limites sur `query` (max 100 chars) et `limit` (max 1000)

4. **Protection SQL** ✅
   - Utilisation de paramètres liés (pas de concaténation SQL)
   - Validation des données avant insertion

### 2.2 ⚠️ Points à améliorer

#### 2.2.1 Headers de sécurité HTTP manquants

**Problème:** Pas de headers de sécurité HTTP configurés

**Risque:** Exposition à des attaques XSS, clickjacking, etc.

**Correctif proposé:**
```python
# Ajouter dans main.py après création de l'app
from fastapi.middleware.trustedhost import TrustedHostMiddleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

#### 2.2.2 Rate limiting insuffisant

**Problème:** Pas de rate limiting global sur l'API

**Risque:** Attaques DoS, abus de l'API

**Correctif proposé:**
```python
# Ajouter un middleware de rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Appliquer sur les endpoints sensibles
@app.post("/scrape/x")
@limiter.limit("10/minute")  # 10 requêtes par minute par IP
async def scrape_x_endpoint(...):
    ...
```

#### 2.2.3 Validation des URLs externes

**Problème:** Pas de validation stricte des URLs dans les scrapers

**Risque:** SSRF (Server-Side Request Forgery)

**Correctif proposé:**
```python
# Ajouter une fonction de validation d'URL
from urllib.parse import urlparse

ALLOWED_DOMAINS = {
    'nitter.net', 'nitter.it', 'nitter.pussthecat.org',
    'reddit.com', 'github.com', 'stackoverflow.com',
    # ... autres domaines autorisés
}

def validate_url(url: str) -> bool:
    """Valide qu'une URL pointe vers un domaine autorisé."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS)
    except:
        return False
```

#### 2.2.4 Logs contenant des données sensibles

**Problème:** Risque de logging de données sensibles (tokens, clés API)

**Correctif proposé:**
```python
# Ajouter une fonction de sanitisation des logs
import re

def sanitize_log_message(message: str) -> str:
    """Supprime les données sensibles des messages de log."""
    # Masquer les clés API
    message = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***', message)
    message = re.sub(r'ghp_[a-zA-Z0-9]{20,}', 'ghp_***REDACTED***', message)
    # Masquer les tokens
    message = re.sub(r'token=[a-zA-Z0-9]+', 'token=***REDACTED***', message)
    return message
```

#### 2.2.5 Pas de timeout sur les requêtes HTTP externes

**Problème:** Les scrapers peuvent bloquer indéfiniment

**Risque:** DoS, ressources bloquées

**Correctif proposé:**
```python
# S'assurer que tous les appels HTTP ont un timeout
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)
```

---

## 3. AUDIT DE CODE

### 3.1 ✅ Points positifs

1. **Structure modulaire** ✅
   - Séparation claire backend/frontend
   - Modules scrapers bien organisés
   - Utilitaires séparés

2. **Gestion d'erreurs** ✅
   - Try/except sur les scrapers
   - Retour gracieux en cas d'erreur

3. **Type hints** ✅
   - Utilisation de Pydantic
   - Annotations de types

### 3.2 ⚠️ Points à améliorer

#### 3.2.1 Code mort / non utilisé

**Fichiers scrapers non utilisés:**
- ❌ `backend/app/scraper/facebook.py` (non importé dans main.py, non implémenté)
- ❌ `backend/app/scraper/linkedin.py` (non importé dans main.py, non implémenté)

**Action:** Supprimer ces fichiers (ils ne sont pas utilisés et ne sont que des stubs)

#### 3.2.2 Duplication de code

**Problème:** Logique de scraping similaire répétée

**Correctif proposé:** Créer une classe de base `BaseScraper` avec méthodes communes

#### 3.2.3 Gestion des dépendances

**Problème:** `requirements.txt` ne spécifie pas de versions

**Correctif proposé:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
# ... avec versions spécifiques
```

#### 3.2.4 Documentation des fonctions

**Problème:** Certaines fonctions manquent de docstrings

**Correctif proposé:** Ajouter des docstrings aux fonctions publiques

---

## 4. CORRECTIFS PROPOSÉS

### 4.1 Nettoyage (à valider)

**Action 1: Supprimer les fichiers de test obsolètes**
- [ ] Supprimer les 27 fichiers de test listés en section 1.1
- [ ] Supprimer les fichiers de debug (section 1.1)

**Action 2: Nettoyer les scripts redondants**
- [ ] Supprimer les scripts de démarrage redondants (section 1.2)
- [ ] Supprimer les fichiers de migration déjà appliqués (section 1.2)

**Action 3: Archiver la documentation obsolète**
- [ ] Créer un dossier `docs/archive/`
- [ ] Déplacer les fichiers MD historiques dans l'archive
- [ ] Garder uniquement la documentation active

**Action 4: Nettoyer les caches Python**
- [ ] Supprimer tous les `__pycache__/`
- [ ] Supprimer tous les `*.pyc`

### 4.2 Sécurité (à valider)

**Action 5: Ajouter les headers de sécurité HTTP**
- [ ] Implémenter le middleware de sécurité (section 2.2.1)

**Action 6: Implémenter le rate limiting**
- [ ] Ajouter `slowapi` aux requirements
- [ ] Configurer le rate limiting (section 2.2.2)

**Action 7: Valider les URLs externes**
- [ ] Implémenter la validation d'URL (section 2.2.3)

**Action 8: Sanitizer les logs**
- [ ] Implémenter la sanitisation des logs (section 2.2.4)

**Action 9: Ajouter des timeouts**
- [ ] Vérifier que tous les appels HTTP ont un timeout (section 2.2.5)

### 4.3 Code (à valider)

**Action 10: Supprimer les scrapers non utilisés**
- [ ] Supprimer `backend/app/scraper/facebook.py` (non utilisé, non implémenté)
- [ ] Supprimer `backend/app/scraper/linkedin.py` (non utilisé, non implémenté)

**Action 11: Améliorer requirements.txt**
- [ ] Ajouter les versions spécifiques des dépendances

**Action 12: Ajouter des docstrings**
- [ ] Documenter les fonctions publiques manquantes

---

## 5. TESTS E2E

### 5.1 Tests à exécuter après nettoyage

**Test 1: Démarrage du serveur**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
✅ Vérifier que le serveur démarre sans erreur

**Test 2: Endpoints API**
```bash
# Tester les endpoints principaux
curl http://localhost:8000/api/posts?limit=10
curl http://localhost:8000/api/stats
```
✅ Vérifier que les endpoints répondent

**Test 3: Scrapers**
```bash
# Tester un scraper
curl -X POST http://localhost:8000/scrape/x?query=OVH&limit=5
```
✅ Vérifier que le scraper fonctionne

**Test 4: Frontend**
- [ ] Ouvrir `http://localhost:8000/scraping`
- [ ] Vérifier que la page se charge
- [ ] Tester un scraper depuis l'interface
- [ ] Vérifier les logs

**Test 5: Dashboard**
- [ ] Ouvrir `http://localhost:8000/dashboard`
- [ ] Vérifier que les graphiques se chargent
- [ ] Tester les filtres

---

## ✅ VALIDATION REQUISE

**Avant d'appliquer les correctifs, merci de valider:**

1. [ ] **Section 1.1** - Fichiers de test à supprimer (27 fichiers)
2. [ ] **Section 1.2** - Scripts redondants à supprimer
3. [ ] **Section 1.3** - Documentation à archiver
4. [ ] **Section 4.2** - Correctifs de sécurité à appliquer
5. [ ] **Section 4.3** - Améliorations de code

**Une fois validé, je procéderai:**
1. Suppression des fichiers validés
2. Application des correctifs de sécurité
3. Améliorations de code
4. Exécution des tests E2E
5. Génération d'un rapport final

---

**Note:** Tous les fichiers supprimés seront listés dans un fichier `CLEANUP_LOG.md` pour traçabilité.

