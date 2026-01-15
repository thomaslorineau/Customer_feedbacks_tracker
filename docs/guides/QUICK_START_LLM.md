# 🔐 Guide rapide : Utiliser votre nouvelle clé OpenAI

## 📝 Étape 1 : Obtenir une nouvelle clé

1. Aller sur https://platform.openai.com/api-keys
2. Cliquer sur **"+ Create new secret key"**
3. Donner un nom (ex: "OVH-Complaints-Tracker-2026")
4. Copier la clé (elle commence par `sk-proj-...`)
5. ⚠️ **Important** : Vous ne pourrez plus la revoir après !

## 📋 Étape 2 : Mettre à jour le fichier .env

Ouvrir le fichier `backend/.env` et remplacer :

```dotenv
# AVANT
OPENAI_API_KEY=your_openai_api_key_here

# APRÈS  
OPENAI_API_KEY=sk-proj-VOTRE_NOUVELLE_CLE_ICI
```

**Exemple complet du fichier `.env` :**

```dotenv
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-1a2b3c4d5e6f7g8h9i0j...

# Optional API Keys
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
TRUSTPILOT_API_KEY=
GITHUB_TOKEN=

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

## ✅ Étape 3 : Tester la configuration

### Option A : Test complet (recommandé)

```bash
cd backend
python test_llm_config.py
```

Ce script va :
- ✅ Valider la configuration
- ✅ Tester le masquage des clés
- ✅ Initialiser le client
- ✅ Faire un appel API de test (coût ~$0.0001)

**Sortie attendue :**
```
============================================================
 LLM CONFIGURATION TEST SUITE
============================================================

TEST 1: Configuration Validation
✅ Configuration is valid

Configuration summary:
==================================================
🔧 APPLICATION CONFIGURATION
==================================================
Environment: development
LLM Provider: openai

🔑 API Keys Status:
  ✅ openai      : sk-proj-...abc123
  ...

TEST 4: LLM API Call (Simple Test)
✅ API call successful!
   Response: Hello
   Model used: gpt-4o-mini

Result: 4/4 tests passed
```

### Option B : Test rapide (sans appel API)

```bash
cd C:\Users\tlorinea\Documents\Documents\Documents\Projets\VibeCoding\ovh-complaints-tracker
python -c "from backend.app.config import config, validate_config_on_startup; result = validate_config_on_startup(); print('Valid:', result['valid'])"
```

## 🚀 Étape 4 : Redémarrer le serveur

```bash
cd C:\Users\tlorinea\Documents\Documents\Documents\Projets\VibeCoding\ovh-complaints-tracker

# Définir le PYTHONPATH et démarrer
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.app.main:app --port 9000 --reload
```

**Logs attendus au démarrage :**
```
============================================================
 STARTING OVH COMPLAINTS TRACKER
============================================================

[SECURITY] Validating configuration...
[OK] Configuration validated successfully

[DATABASE] Initializing...
[OK] Database initialized

[SCHEDULER] Starting auto-scrape job (every 3 hours)...
[OK] Scheduler started

============================================================
 APPLICATION READY!
============================================================
```

## 💡 Exemples d'utilisation dans le code

### Exemple 1 : Analyse de sentiment avec LLM

Créer `backend/app/analysis/llm_sentiment.py` :

```python
from ..config import get_llm_client
import logging

logger = logging.getLogger(__name__)

def analyze_sentiment_with_llm(text: str) -> dict:
    """Analyze sentiment using LLM (more accurate than VADER)."""
    try:
        client = get_llm_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a sentiment analyzer. Respond with only: POSITIVE, NEGATIVE, or NEUTRAL"
                },
                {
                    "role": "user",
                    "content": f"Analyze sentiment of: {text[:500]}"
                }
            ],
            max_tokens=10,
            temperature=0
        )
        
        sentiment = response.choices[0].message.content.strip().upper()
        
        # Convert to score
        score_map = {"POSITIVE": 0.8, "NEGATIVE": -0.8, "NEUTRAL": 0.0}
        score = score_map.get(sentiment, 0.0)
        
        return {
            "label": sentiment.lower(),
            "score": score,
            "method": "llm"
        }
        
    except Exception as e:
        logger.error(f"LLM sentiment analysis failed: {type(e).__name__}")
        # Fallback to VADER
        from . import sentiment
        return sentiment.analyze(text)
```

### Exemple 2 : Extraction de mots-clés

```python
def extract_keywords_with_llm(text: str, max_keywords: int = 5) -> list:
    """Extract key topics from customer feedback."""
    try:
        client = get_llm_client()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Extract {max_keywords} key topics. Return as comma-separated list."
                },
                {
                    "role": "user",
                    "content": text[:1000]
                }
            ],
            max_tokens=50
        )
        
        keywords_text = response.choices[0].message.content
        keywords = [k.strip() for k in keywords_text.split(",")]
        
        return keywords[:max_keywords]
        
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return []
```

### Exemple 3 : Résumé de feedback

```python
def summarize_feedback(feedbacks: list, max_length: int = 200) -> str:
    """Summarize multiple customer feedbacks."""
    try:
        client = get_llm_client()
        
        # Combine feedback texts
        combined = "\n".join([f["content"][:200] for f in feedbacks[:10]])
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Summarize customer complaints in {max_length} characters max."
                },
                {
                    "role": "user",
                    "content": combined
                }
            ],
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return "Unable to generate summary"
```

## 🛡️ Bonnes pratiques

### ✅ À FAIRE

```python
# 1. Toujours gérer les exceptions
try:
    client = get_llm_client()
    response = client.chat.completions.create(...)
except ValueError as e:
    logger.error(f"Config error: {e}")
except Exception as e:
    logger.error(f"API error: {type(e).__name__}")

# 2. Limiter les tokens pour contrôler les coûts
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Modèle le moins cher
    max_tokens=100,  # Limiter la réponse
    ...
)

# 3. Logger avec masquage
logger.info(f"Using API key: {config.mask_api_key(config.OPENAI_API_KEY)}")

# 4. Avoir un fallback
try:
    result = analyze_with_llm(text)
except:
    result = analyze_with_vader(text)  # Fallback local
```

### ❌ À NE PAS FAIRE

```python
# ❌ Ne jamais logger la clé complète
logger.info(f"API Key: {config.OPENAI_API_KEY}")

# ❌ Ne pas faire d'appels sans limite
for item in huge_list:  # Peut coûter cher !
    llm_analyze(item)

# ❌ Ne pas ignorer les erreurs silencieusement
try:
    result = llm_call()
except:
    pass  # ❌ Mauvais !
```

## 📊 Surveillance des coûts

### Sur OpenAI Dashboard

1. Aller sur https://platform.openai.com/usage
2. Vérifier :
   - **Usage today** : Combien de $ utilisés aujourd'hui
   - **Requests** : Nombre d'appels API
   - **Tokens** : Nombre de tokens consommés

### Définir une limite de dépenses

1. Aller sur https://platform.openai.com/account/limits
2. Définir **Monthly budget** (ex: $10/mois)
3. Activer les alertes email

### Estimer les coûts

**gpt-4o-mini** (recommandé) :
- Input : $0.150 / 1M tokens
- Output : $0.600 / 1M tokens

**Exemple** : 
- Analyser 1000 feedbacks de 200 caractères (~50 tokens)
- = 50,000 tokens input + 10,000 tokens output
- = ~$0.01 (1 centime)

## 🔄 Changer de provider LLM

### Passer à Anthropic (Claude)

```dotenv
# Dans .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api-...
```

Le code reste le même grâce à `get_llm_client()` !

### Passer à Google AI

```dotenv
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...
```

## 🆘 Dépannage

### Erreur : "Invalid API key"

```bash
# Vérifier que la clé est bien définie
python -c "from backend.app.config import config; print(config.mask_api_key(config.OPENAI_API_KEY))"
```

Si affiche `your_...here`, la clé n'est pas chargée.

**Solutions :**
1. Vérifier que `.env` est bien dans `backend/`
2. Pas d'espace avant/après `=`
3. Redémarrer le serveur après modification

### Erreur : "Rate limit exceeded"

Vous avez dépassé la limite de requêtes/minute.

**Solutions :**
- Ajouter `time.sleep(1)` entre les appels
- Réduire le nombre d'appels simultanés
- Upgrader votre plan OpenAI

### Erreur : "Insufficient quota"

Votre compte OpenAI n'a plus de crédit.

**Solutions :**
- Ajouter une carte de paiement : https://platform.openai.com/account/billing
- Vérifier les limites : https://platform.openai.com/account/limits

## ✅ Checklist finale

- [ ] Nouvelle clé OpenAI générée
- [ ] `.env` mis à jour avec la nouvelle clé  
- [ ] Test `python test_llm_config.py` réussi
- [ ] Serveur redémarré avec succès
- [ ] Logs de validation apparaissent au démarrage
- [ ] Budget/alertes configurés sur OpenAI
- [ ] Ancienne clé révoquée ✅ (déjà fait)

---

**Prêt à utiliser !** 🚀

Votre application peut maintenant :
- Analyser le sentiment avec LLM (plus précis)
- Extraire des mots-clés automatiquement
- Générer des résumés de feedback
- Et tout autre traitement NLP avancé

**Coût estimé :** ~$0.01-0.05 par 1000 feedbacks analysés
