# 🔄 PLAN DE REFACTORISATION - OVH Customer Feedbacks Tracker

**Date:** 18 Janvier 2026  
**Version actuelle:** 1.0.1  
**Objectif:** Refactoriser `main.py` (4415 lignes) en modules routers

---

## 📊 ÉTAT ACTUEL

### Fichier `main.py`
- **Taille:** 4415 lignes
- **Endpoints:** 61 endpoints définis
- **Routers existants:** `auth.py`, `config.py` (déjà inclus)
- **Routers vides:** `scraping.py`, `dashboard.py`, `admin.py`, `email.py`

### Problèmes identifiés
- ❌ Fichier monolithique difficile à maintenir
- ❌ Imports dupliqués (corrigés)
- ❌ Code dupliqué entre endpoints
- ❌ Difficulté à tester les endpoints individuellement
- ❌ Violation du principe de responsabilité unique

---

## 🎯 OBJECTIFS DE LA REFACTORISATION

1. **Modularité:** Séparer les endpoints par domaine fonctionnel
2. **Maintenabilité:** Réduire la taille de `main.py` à ~500-800 lignes
3. **Testabilité:** Faciliter les tests unitaires par router
4. **Lisibilité:** Améliorer la navigation dans le code
5. **Réutilisabilité:** Faciliter l'ajout de nouvelles fonctionnalités

---

## 📋 PLAN D'ACTION DÉTAILLÉ

### ✅ ÉTAPE 1: SCRAPING ROUTER (12 endpoints)

**Fichier:** `backend/app/routers/scraping.py`

**Endpoints à déplacer:**
- `POST /scrape/x` → `POST /scrape/x`
- `POST /scrape/stackoverflow` → `POST /scrape/stackoverflow`
- `POST /scrape/github` → `POST /scrape/github`
- `POST /scrape/reddit` → `POST /scrape/reddit`
- `POST /scrape/ovh-forum` → `POST /scrape/ovh-forum`
- `POST /scrape/mastodon` → `POST /scrape/mastodon`
- `POST /scrape/linkedin` → `POST /scrape/linkedin`
- `POST /scrape/g2-crowd` → `POST /scrape/g2-crowd`
- `POST /scrape/news` → `POST /scrape/news`
- `POST /scrape/trustpilot` → `POST /scrape/trustpilot`
- `POST /scrape/{source}/job` → `POST /scrape/{source}/job`
- `POST /scrape/keywords` → `POST /scrape/keywords`
- `GET /scrape/jobs` → `GET /scrape/jobs`
- `GET /scrape/jobs/{job_id}` → `GET /scrape/jobs/{job_id}`
- `POST /scrape/jobs/{job_id}/cancel` → `POST /scrape/jobs/{job_id}/cancel`
- `POST /scrape/jobs/cancel-all` → `POST /scrape/jobs/cancel-all`

**Code à déplacer:**
- Fonction `should_insert_post()` (lignes 57-79)
- Modèles: `ScrapeResult`, `KeywordsPayload` (lignes 238-336)
- Fonctions utilitaires: `sanitize_log_message()`, `log_scraping()`
- Job tracking: `JOBS` dict et fonctions associées

**Dépendances:**
- `from ..scraper import *`
- `from ..analysis import sentiment, country_detection, relevance_scorer`
- `from ..config import keywords_base`
- `from ..auth.dependencies import require_auth`

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 2: DASHBOARD ROUTER (8 endpoints)

**Fichier:** `backend/app/routers/dashboard.py`

**Endpoints à déplacer:**
- `GET /api/posts-by-country` → `GET /api/posts-by-country`
- `GET /api/posts-by-source` → `GET /api/posts-by-source`
- `GET /posts` → `GET /posts`
- `GET /api/pain-points` → `GET /api/pain-points`
- `GET /api/product-analysis/{product_name}` → `GET /api/product-analysis/{product_name}`
- `GET /api/product-opportunities` → `GET /api/product-opportunities`
- `GET /api/posts-for-improvement` → `GET /api/posts-for-improvement`
- `POST /generate-improvement-ideas` → `POST /generate-improvement-ideas`
- `GET /api/improvements-summary` → `GET /api/improvements-summary`
- `POST /api/recommended-actions` → `POST /api/recommended-actions`

**Modèles à déplacer:**
- `PainPointsResponse` (déjà présent)
- `ProductDistributionResponse` (déjà présent)
- `ImprovementIdea`, `ImprovementIdeasResponse` (déjà présents)
- `RecommendedAction`, `RecommendedActionsResponse` (déjà présents)
- `RecurringPainPoint`, `ProductOpportunityScore`

**Dépendances:**
- `from .. import db`
- `from ..analysis import sentiment`
- LLM providers (OpenAI, Anthropic)

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 3: ADMIN ROUTER (8 endpoints)

**Fichier:** `backend/app/routers/admin.py`

**Endpoints à déplacer:**
- `POST /admin/cleanup-hackernews-posts` → `POST /admin/cleanup-hackernews-posts`
- `GET /admin/duplicates-stats` → `GET /admin/duplicates-stats`
- `POST /admin/cleanup-duplicates` → `POST /admin/cleanup-duplicates`
- `POST /admin/cleanup-non-ovh-posts` → `POST /admin/cleanup-non-ovh-posts`
- `POST /admin/set-ui-version` → `POST /admin/set-ui-version`
- `GET /admin/get-ui-version` → `GET /admin/get-ui-version`
- `POST /api/upload-logo` → `POST /api/upload-logo`
- `GET /api/logo-status` → `GET /api/logo-status`
- `POST /api/generate-powerpoint-report` → `POST /api/generate-powerpoint-report`

**Dépendances:**
- `from ..auth.dependencies import require_admin`
- `from .. import db`
- `from ..powerpoint_generator import *`

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 4: EMAIL ROUTER (9 endpoints)

**Fichier:** `backend/app/routers/email.py`

**Endpoints à déplacer:**
- `GET /api/email/triggers` → `GET /api/email/triggers`
- `GET /api/email/triggers/{trigger_id}` → `GET /api/email/triggers/{trigger_id}`
- `POST /api/email/triggers` → `POST /api/email/triggers`
- `PUT /api/email/triggers/{trigger_id}` → `PUT /api/email/triggers/{trigger_id}`
- `DELETE /api/email/triggers/{trigger_id}` → `DELETE /api/email/triggers/{trigger_id}`
- `POST /api/email/triggers/{trigger_id}/toggle` → `POST /api/email/triggers/{trigger_id}/toggle`
- `GET /api/email/config` → `GET /api/email/config`
- `POST /api/email/test` → `POST /api/email/test`
- `GET /api/email/notifications` → `GET /api/email/notifications`

**Modèles à déplacer:**
- `EmailConfigResponse` (déjà présent)
- `EmailTriggerPayload`, `EmailTriggerResponse`

**Dépendances:**
- `from .. import db`
- `from ..notifications.email_sender import *`
- `from ..auth.dependencies import require_auth, require_admin`

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 5: SETTINGS ROUTER (4 endpoints)

**Fichier:** `backend/app/routers/config.py` (étendre) ou `routers/settings.py` (nouveau)

**Endpoints à déplacer:**
- `GET /settings/queries` → `GET /settings/queries`
- `POST /settings/queries` → `POST /settings/queries`
- `GET /settings/base-keywords` → `GET /settings/base-keywords`
- `POST /settings/base-keywords` → `POST /settings/base-keywords`

**Dépendances:**
- `from .. import db`
- `from ..config.keywords_base import *`
- `from ..auth.dependencies import require_auth`

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 6: LOGS ROUTER (2 endpoints)

**Fichier:** `backend/app/routers/admin.py` (ajouter) ou `routers/logs.py` (nouveau)

**Endpoints à déplacer:**
- `GET /api/logs` → `GET /api/logs`
- `DELETE /api/logs` → `DELETE /api/logs`

**Dépendances:**
- `from .. import db`
- `from ..auth.dependencies import require_admin`

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 7: PAGES ROUTER (9 endpoints HTML)

**Fichier:** `backend/app/routers/pages.py` (nouveau) ou garder dans `main.py`

**Endpoints à déplacer:**
- `GET /` → `GET /`
- `GET /scraping` → `GET /scraping`
- `GET /scraping-configuration` → `GET /scraping-configuration`
- `GET /dashboard` → `GET /dashboard`
- `GET /dashboard-analytics` → `GET /dashboard-analytics`
- `GET /logs` → `GET /logs`
- `GET /improvements` → `GET /improvements`
- `GET /settings` → `GET /settings`

**Décision:** Garder dans `main.py` (configuration statique) ou créer `pages.py` ?

**Statut:** ⏳ En attente - Décision requise

---

### ✅ ÉTAPE 8: INCLUSION DES ROUTERS

**Fichier:** `backend/app/main.py`

**Actions:**
1. Importer tous les routers
2. Ajouter `app.include_router()` pour chaque router
3. Configurer les préfixes et tags si nécessaire

```python
from .routers import auth, config, scraping, dashboard, admin, email

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(scraping.router, prefix="/api", tags=["scraping"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(email.router, prefix="/api", tags=["email"])
```

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 9: NETTOYAGE DE MAIN.PY

**Fichier:** `backend/app/main.py`

**À garder:**
- Configuration FastAPI (lignes 92-99)
- Middleware CORS (lignes 140-145)
- Middleware de sécurité (lignes 151-180)
- Exception handlers (lignes 182-240)
- Rate limiting setup (lignes 102-105)
- Static files mounting (lignes 107-137)
- Scheduler setup (lignes 343-451)
- Fonctions utilitaires partagées (si nécessaire)

**À supprimer:**
- Tous les endpoints déplacés
- Modèles Pydantic déplacés
- Imports inutilisés

**Statut:** ⏳ En attente

---

### ✅ ÉTAPE 10: TESTS ET VALIDATION

**Actions:**
1. Vérifier que tous les endpoints fonctionnent
2. Tester les dépendances entre routers
3. Vérifier les imports
4. Tester les middlewares
5. Valider les permissions (auth/admin)

**Statut:** ⏳ En attente

---

## 📊 RÉPARTITION ESTIMÉE DES LIGNES

| Router | Endpoints | Lignes estimées | Priorité |
|--------|-----------|-----------------|----------|
| `scraping.py` | 15 | ~800-1000 | 🔴 Haute |
| `dashboard.py` | 10 | ~600-800 | 🟡 Moyenne |
| `admin.py` | 9 | ~400-500 | 🟡 Moyenne |
| `email.py` | 9 | ~300-400 | 🟢 Basse |
| `config.py` (étendu) | 4 | ~200-300 | 🟢 Basse |
| `main.py` (nettoyé) | 9 (pages) | ~500-800 | - |

**Total estimé après refactorisation:**
- `main.py`: ~500-800 lignes (au lieu de 4415)
- Routers: ~2300-3000 lignes réparties

---

## 🚀 ORDRE D'EXÉCUTION RECOMMANDÉ

1. **Scraping** (le plus volumineux, impact majeur)
2. **Dashboard** (fonctionnalités critiques)
3. **Admin** (utilitaires)
4. **Email** (fonctionnalités secondaires)
5. **Settings** (simple)
6. **Logs** (simple)
7. **Pages** (décision requise)
8. **Inclusion** (finalisation)
9. **Nettoyage** (optimisation)
10. **Tests** (validation)

---

## ⚠️ RISQUES ET PRÉCAUTIONS

### Risques identifiés
- 🔴 **Breaking changes:** Les endpoints doivent garder les mêmes chemins
- 🟡 **Dépendances circulaires:** Attention aux imports entre routers
- 🟡 **Rate limiting:** Le limiter doit être partagé correctement
- 🟡 **Scheduler:** Doit rester dans `main.py` ou être externalisé proprement

### Précaution à prendre
1. ✅ Créer une branche dédiée
2. ✅ Tester chaque router individuellement
3. ✅ Vérifier les imports et dépendances
4. ✅ Valider que tous les endpoints fonctionnent
5. ✅ Documenter les changements

---

## 📝 NOTES IMPORTANTES

### Fonctions partagées
Certaines fonctions doivent être accessibles à plusieurs routers:
- `should_insert_post()` → Utilitaires partagés ou `utils/`
- `sanitize_log_message()` → Utilitaires partagés
- `log_scraping()` → Utilitaires partagés

### Configuration partagée
- `RELEVANCE_THRESHOLD` → Variable d'environnement ou config centralisée
- `limiter` (rate limiting) → Doit être partagé entre routers

### Scheduler
Le scheduler doit rester dans `main.py` car il est lié au cycle de vie de l'application FastAPI.

---

## ✅ CHECKLIST DE VALIDATION

- [ ] Tous les endpoints déplacés fonctionnent
- [ ] Aucune régression fonctionnelle
- [ ] Les imports sont corrects
- [ ] Les tests passent
- [ ] La documentation est à jour
- [ ] `main.py` est réduit à ~500-800 lignes
- [ ] Les routers sont bien organisés
- [ ] Pas de code dupliqué
- [ ] Les permissions (auth/admin) fonctionnent

---

**Dernière mise à jour:** 18 Janvier 2026  
**Statut global:** ⏳ En attente de démarrage




