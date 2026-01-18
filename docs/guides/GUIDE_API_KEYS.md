# 🔑 Guide: Gestion sécurisée des clés API LLM

## 📋 Vue d'ensemble

Ce guide explique comment implémenter **proprement** la gestion des clés API pour les services LLM (OpenAI, Anthropic, Google, etc.) dans votre application.

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
- ✅ Masquage pour les logs (`sk-proj-...abc123`)
- ✅ Accès centralisé via `config.py`
- ✅ Type hints et validation

### 4. **Support multi-providers**
- ✅ OpenAI, Anthropic, Google
- ✅ Configuration dynamique du provider
- ✅ Fallback gracieux si clé manquante

---

## 🚀 Utilisation

### 1. Configuration initiale

**Éditer `backend/.env`:**

```dotenv
# LLM Provider (openai, anthropic, google)
LLM_PROVIDER=openai

# OpenAI API Key
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-VOTRE_CLE_ICI

# Anthropic API Key (optional)
# Get from: https://console.anthropic.com/
ANTHROPIC_API_KEY=

# Google AI API Key (optional)
# Get from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=

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
            model="gpt-4",
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
api_key = config.get_api_key("openai")

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
api_key = "sk-proj-abc123..."

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
# LLM Provider: openai
# 
# 🔑 API Keys Status:
#   ✅ openai      : sk-proj-...abc123
#   ❌ anthropic   : Not configured
#   ...
```

### Test 2: Vérifier le masquage

```python
from app.config import config

# Tester le masquage
key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
masked = config.mask_api_key(key)
print(masked)  # Affiche: sk-proj-...vwxyz

# JAMAIS:
print(key)  # ❌ N'affiche JAMAIS la clé complète
```

### Test 3: Validation du format

```python
from app.config import config

# Tester la validation
providers = ["openai", "github", "trustpilot"]
for provider in providers:
    is_valid = config.is_api_key_valid_format(provider)
    print(f"{provider}: {'✅' if is_valid else '❌'}")
```

---

## 🔄 Rotation des clés

### Étapes pour changer une clé API

1. **Générer une nouvelle clé** sur le portail du provider
2. **Mettre à jour `.env`:**
   ```dotenv
   OPENAI_API_KEY=sk-proj-NOUVELLE_CLE
   ```
3. **Redémarrer le serveur:**
   ```bash
   # Arrêter (Ctrl+C)
   # Redémarrer
   python -m uvicorn app.main:app --reload
   ```
4. **Vérifier les logs:**
   ```
   ✅ API key for openai: configured (51 chars)
   ```
5. **Révoquer l'ancienne clé** sur le portail

---

## 📊 Support multi-providers

### Configuration par provider

**OpenAI:**
```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
```

**Anthropic:**
```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**Google AI:**
```dotenv
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...
```

### Changer de provider dynamiquement

```python
from app.config import config

# Changer de provider (avant de créer le client)
config.LLM_PROVIDER = "anthropic"
client = get_llm_client()
```

---

## 🛡️ Sécurité avancée (Production)

### 1. Gestionnaire de secrets

Au lieu de `.env` en production:

```python
# AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

OPENAI_API_KEY = get_secret('prod/openai-api-key')
```

### 2. Permissions minimales

- Créer des clés avec permissions limitées
- Un projet = une clé dédiée
- Limites de dépenses configurées

### 3. Surveillance

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
def call_openai_api(prompt):
    client = get_llm_client()
    # ...
```

### 4. Rate limiting par clé

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
- [ ] Limites de dépenses configurées
- [ ] Clés différentes pour dev/staging/prod
- [ ] Permissions minimales sur les clés
- [ ] Plan de réponse si clé compromise

---

## 📞 Ressources

### Portails de gestion des clés

- **OpenAI:** https://platform.openai.com/api-keys
- **Anthropic:** https://console.anthropic.com/
- **Google AI:** https://makersuite.google.com/app/apikey
- **GitHub:** https://github.com/settings/tokens

### Documentation

- **OpenAI Best Practices:** https://platform.openai.com/docs/guides/production-best-practices
- **Anthropic Security:** https://docs.anthropic.com/claude/docs/security
- **12-Factor App:** https://12factor.net/config

---

## 🆘 En cas de compromission

Si une clé API est exposée:

1. **IMMÉDIAT:** Révoquer la clé sur le portail
2. Générer une nouvelle clé
3. Mettre à jour `.env` et redémarrer
4. Vérifier l'historique Git: `git log --all -- .env`
5. Si commitée, purger l'historique Git
6. Vérifier les logs d'usage sur le portail
7. Activer les alertes de facturation
8. Contacter le support si activité suspecte

---

**Créé le:** 15 janvier 2026  
**Version:** 1.0  
**Statut:** ✅ Production-ready
