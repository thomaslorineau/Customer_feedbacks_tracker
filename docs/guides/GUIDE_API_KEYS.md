# 🔑 Guide: Gestion sécurisée des clés API

## 📋 Vue d'ensemble

Ce guide explique comment implémenter **proprement** la gestion des clés API pour OVH AI Endpoints et les services de scraping dans votre application.

> **Note:** Ce projet a été développé **100% avec VibeCoding** (Cursor AI).

---

## ✅ Bonnes pratiques implémentées

### 1. **Variables d'environnement** 
- ✅ Clés stockées dans `.env` (jamais dans le code)
- ✅ `.env` protégé par `.gitignore`
- ✅ `.env.example` comme template

### 2. **Validation au démarrage**
- ✅ Vérification de la présence des clés obligatoires
- ✅ Validation du format des clés
- ✅ Détection des clés compromises
- ✅ Warnings pour clés optionnelles manquantes

### 3. **Sécurité**
- ✅ Jamais de logging des clés complètes
- ✅ Masquage pour les logs (`eyJhbG...abc123`)
- ✅ Accès centralisé via `config.py`
- ✅ Type hints et validation

### 4. **Support OVH AI**
- ✅ OVH AI Endpoints (provider principal)
- ✅ Configuration dynamique
- ✅ Fallback gracieux si clé manquante

---

## 🚀 Utilisation

### 1. Configuration initiale

**Éditer `backend/.env`:**

```dotenv
# LLM Provider - OVH AI Endpoints
LLM_PROVIDER=ovh
OVH_API_KEY=votre_token_ovh
OVH_ENDPOINT_URL=https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1
OVH_MODEL=Mixtral-8x22B-Instruct-v0.1

# Optional: Enhanced scraping
TRUSTPILOT_API_KEY=
GITHUB_TOKEN=

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 2. Import et utilisation dans le code

**Dans `main.py`:**

```python
from .config import config, validate_config_on_startup, get_llm_client

# Au démarrage de l'application
@app.on_event("startup")
def startup_event():
    # Valider la configuration
    validation = validate_config_on_startup()
    
    if not validation["valid"]:
        logger.error("⚠️ Configuration errors detected - check logs")
    
    # Initialiser la base de données
    db.init_db()
    
    # Démarrer le scheduler
    scheduler.start()
```

**Utiliser un client LLM:**

```python
from .config import get_llm_client

# Dans une fonction
def analyze_with_llm(text: str):
    try:
        client = get_llm_client()
        
        response = client.chat.completions.create(
            model=config.OVH_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text}
            ]
        )
        
        return response.choices[0].message.content
        
    except ValueError as e:
        logger.error(f"LLM client error: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM request failed: {type(e).__name__}")
        return None
```

**Accéder à une clé spécifique:**

```python
from .config import config

# Dans un scraper
def scrape_with_api():
    github_token = config.get_api_key("github")
    
    if not github_token:
        logger.warning("GitHub token not configured - using anonymous access")
        headers = {"User-Agent": "MyApp/1.0"}
    else:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "User-Agent": "MyApp/1.0"
        }
    
    response = requests.get(url, headers=headers)
    # ...
```

---

## 🔒 Règles de sécurité

### ✅ À FAIRE

```python
# ✅ Récupérer via config
api_key = config.get_api_key("ovh")

# ✅ Masquer pour logging
logger.info(f"Using key: {config.mask_api_key(api_key)}")

# ✅ Gérer les erreurs
if not api_key:
    raise ValueError("API key not configured")

# ✅ Valider au démarrage
validation = config.validate_required_keys()
```

### ❌ À NE JAMAIS FAIRE

```python
# ❌ JAMAIS hardcoder une clé
api_key = "eyJhbGciOiJSUzI1N..."

# ❌ JAMAIS logger une clé complète
logger.info(f"API Key: {api_key}")

# ❌ JAMAIS exposer dans les réponses API
return {"api_key": api_key}

# ❌ JAMAIS commiter .env
# (Doit être dans .gitignore)

# ❌ JAMAIS passer les clés en paramètres URL
url = f"https://api.com?key={api_key}"
```

---

## 🧪 Tests et validation

### Test 1: Démarrage avec validation

```bash
# Démarrer le serveur
cd backend
python -m uvicorn app.main:app --reload

# Vérifier les logs au démarrage
# Doit afficher:
# 🔍 Validating configuration...
# ==================================================
# 🔧 APPLICATION CONFIGURATION
# ==================================================
# Environment: development
# LLM Provider: ovh
# 
# 🔑 API Keys Status:
#   ✅ ovh         : eyJhbG...abc123
#   ...
```

### Test 2: Vérifier le masquage

```python
from app.config import config

# Tester le masquage
key = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
masked = config.mask_api_key(key)
print(masked)  # Affiche: eyJhbG...WT9...

# JAMAIS:
print(key)  # ❌ N'affiche JAMAIS la clé complète
```

### Test 3: Validation du format

```python
from app.config import config

# Tester la validation
providers = ["ovh", "github", "trustpilot"]
for provider in providers:
    is_valid = config.is_api_key_valid_format(provider)
    print(f"{provider}: {'✅' if is_valid else '❌'}")
```

---

## 🔄 Rotation des clés

### Étapes pour changer une clé API

1. **Générer une nouvelle clé** sur https://endpoints.ai.cloud.ovh.net/
2. **Mettre à jour `.env`:**
   ```dotenv
   OVH_API_KEY=nouveau_token_ovh
   ```
3. **Redémarrer le serveur:**
   ```bash
   # Arrêter (Ctrl+C)
   # Redémarrer
   python -m uvicorn app.main:app --reload
   ```
4. **Vérifier les logs:**
   ```
   ✅ API key for ovh: configured
   ```
5. **Révoquer l'ancien token** sur le portail OVH

---

## 📊 Configuration OVH AI Endpoints

### Configuration

```dotenv
LLM_PROVIDER=ovh
OVH_API_KEY=votre_token_ovh
OVH_ENDPOINT_URL=https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1
OVH_MODEL=Mixtral-8x22B-Instruct-v0.1
```

### Modèles disponibles

| Modèle | Description |
|--------|-------------|
| `Mixtral-8x22B-Instruct-v0.1` | Puissant, recommandé |
| `Llama-3.1-70B-Instruct` | Alternative performante |
| `Mistral-7B-Instruct` | Léger, pour tests |

---

## 🛡️ Sécurité avancée (Production)

### 1. Permissions minimales

- Créer des tokens avec permissions limitées
- Un projet = un token dédié
- Limites de ressources configurées

### 2. Surveillance

```python
import time
from functools import wraps

def monitor_api_calls(func):
    """Décorateur pour surveiller les appels API."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"API call {func.__name__}: {duration:.2f}s - SUCCESS")
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(f"API call {func.__name__}: {duration:.2f}s - FAILED: {e}")
            raise
    return wrapper

@monitor_api_calls
def call_ovh_api(prompt):
    client = get_llm_client()
    # ...
```

### 3. Rate limiting par clé

```python
from collections import defaultdict
from datetime import datetime, timedelta

api_call_counts = defaultdict(list)

def check_api_rate_limit(provider: str, max_calls: int = 100, window_minutes: int = 1):
    """Vérifier si la limite n'est pas dépassée."""
    now = datetime.now()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Nettoyer les anciennes entrées
    api_call_counts[provider] = [
        t for t in api_call_counts[provider] if t > cutoff
    ]
    
    # Vérifier la limite
    if len(api_call_counts[provider]) >= max_calls:
        raise Exception(f"Rate limit exceeded for {provider}")
    
    # Enregistrer cet appel
    api_call_counts[provider].append(now)
```

---

## ✅ Checklist de sécurité

- [ ] `.env` dans `.gitignore`
- [ ] `.env.example` créé et documenté
- [ ] Pas de clés hardcodées dans le code
- [ ] Validation des clés au démarrage
- [ ] Masquage dans les logs
- [ ] Gestion d'erreur si clé manquante
- [ ] Rotation régulière des clés (tous les 3-6 mois)
- [ ] Monitoring des appels API
- [ ] Clés différentes pour dev/staging/prod
- [ ] Permissions minimales sur les clés
- [ ] Plan de réponse si clé compromise

---

## 📞 Ressources

### Portails de gestion des clés

- **OVH AI Endpoints:** https://endpoints.ai.cloud.ovh.net/
- **GitHub:** https://github.com/settings/tokens

### Documentation

- **OVH AI Endpoints:** https://help.ovhcloud.com/csm/fr-ai-endpoints-capabilities
- **12-Factor App:** https://12factor.net/config

---

## 🆘 En cas de compromission

Si une clé API est exposée:

1. **IMMÉDIAT:** Révoquer le token sur le portail OVH
2. Générer un nouveau token
3. Mettre à jour `.env` et redémarrer
4. Vérifier l'historique Git: `git log --all -- .env`
5. Si commitée, purger l'historique Git
6. Vérifier les logs d'usage sur le portail
7. Activer les alertes de facturation
8. Contacter le support si activité suspecte

---

**Créé le:** 15 janvier 2026  
**Mis à jour:** Février 2026  
**Version:** 2.0  
**Statut:** ✅ Production-ready
