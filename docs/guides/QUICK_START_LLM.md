# 🔐 Guide rapide : Configurer OVH AI Endpoints

## 📝 Étape 1 : Obtenir un token OVH AI

1. Aller sur https://endpoints.ai.cloud.ovh.net/
2. Se connecter avec votre compte OVH
3. Créer un nouveau endpoint ou utiliser un existant
4. Récupérer :
   - **URL de l'endpoint** : `https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1`
   - **Token API** : Le token d'authentification

## 📋 Étape 2 : Mettre à jour le fichier .env

Ouvrir le fichier `backend/.env` et configurer :

```dotenv
# LLM Configuration - OVH AI Endpoints
LLM_PROVIDER=ovh
OVH_API_KEY=votre_token_ovh_ici
OVH_ENDPOINT_URL=https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1
OVH_MODEL=Mixtral-8x22B-Instruct-v0.1

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

**Exemple complet du fichier `.env` :**

```dotenv
# LLM Configuration - OVH AI Endpoints
LLM_PROVIDER=ovh
OVH_API_KEY=eyJhbGciOiJSUzI1NiIsInR5...
OVH_ENDPOINT_URL=https://mixtral-8x22b.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1
OVH_MODEL=Mixtral-8x22B-Instruct-v0.1

# Optional - Other settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## ✅ Étape 3 : Tester la configuration

### Option A : Via l'interface Settings

1. Aller sur `http://localhost:8000/dashboard/settings.html`
2. Ouvrir la section **"LLM Configuration"**
3. Remplir les champs :
   - **Provider** : OVH
   - **OVH API Key** : Votre token
   - **OVH Endpoint URL** : L'URL de votre endpoint
   - **OVH Model** : Le nom du modèle (ex: Mixtral-8x22B-Instruct-v0.1)
4. Cliquer sur **"Save Configuration"**

### Option B : Test via API

```bash
curl -X GET "http://localhost:8000/api/llm-config" | jq
```

**Réponse attendue :**
```json
{
  "provider": "ovh",
  "api_key_set": true,
  "available": true,
  "llm_provider": "ovh",
  "status": "configured"
}
```

## 🚀 Étape 4 : Utiliser les fonctionnalités LLM

Une fois configuré, les fonctionnalités suivantes sont disponibles :

### Dashboard Analytics - "What's Happening"
- Génération automatique d'insights à partir des posts collectés
- Cliquer sur "Generate Insights" pour lancer l'analyse

### Improvements Opportunities
- Analyse automatique des pain points
- Recommandations d'améliorations produit
- Filtrage par produit avec analyse contextuelle

## 💡 Modèles OVH AI disponibles

| Modèle | Description | Utilisation |
|--------|-------------|-------------|
| **Mixtral-8x22B-Instruct-v0.1** | Modèle puissant pour l'analyse | Recommandé pour analyses complexes |
| **Llama-3.1-70B-Instruct** | Modèle Llama optimisé | Bonne alternative |
| **Mistral-7B-Instruct** | Modèle léger | Pour tests et usage modéré |

## 🛡️ Bonnes pratiques

### ✅ À FAIRE

```python
# 1. Toujours vérifier la disponibilité du LLM
from backend.app.database import pg_get_config

ovh_key = pg_get_config('OVH_API_KEY')
if not ovh_key:
    logger.warning("OVH API key not configured")

# 2. Utiliser les timeouts
response = await client.chat.completions.create(
    model=model_name,
    messages=messages,
    timeout=30  # 30 secondes max
)

# 3. Logger sans exposer les secrets
logger.info(f"Using OVH endpoint: {endpoint_url[:30]}...")
```

### ❌ À NE PAS FAIRE

```python
# ❌ Ne jamais logger le token complet
logger.info(f"Token: {ovh_token}")

# ❌ Ne pas faire d'appels sans limite de temps
response = await client.chat.completions.create(...)  # Pas de timeout
```

## 🆘 Dépannage

### Erreur : "OVH endpoint not configured"

**Vérifier :**
1. `OVH_API_KEY` est défini dans `.env` ou via l'interface Settings
2. `OVH_ENDPOINT_URL` est défini et correct
3. Le serveur a été redémarré après modification du `.env`

### Erreur : "Authentication failed"

**Solutions :**
1. Vérifier que le token est valide (pas expiré)
2. Vérifier que le token a les permissions nécessaires
3. Régénérer le token sur https://endpoints.ai.cloud.ovh.net/

### Erreur : "Model not found"

**Solutions :**
1. Vérifier le nom exact du modèle sur votre endpoint OVH
2. Mettre à jour `OVH_MODEL` avec le bon nom

## ✅ Checklist finale

- [ ] Token OVH AI obtenu depuis endpoints.ai.cloud.ovh.net
- [ ] `.env` configuré avec OVH_API_KEY, OVH_ENDPOINT_URL, OVH_MODEL
- [ ] LLM_PROVIDER=ovh défini
- [ ] Test via API ou interface réussi
- [ ] Fonctionnalités LLM opérationnelles (Insights, Improvements)

---

**Prêt à utiliser !** 🚀

Votre application utilise maintenant **OVH AI Endpoints** pour :
- Générer des insights automatiques
- Analyser les problèmes clients
- Recommander des améliorations produit

**Avantage :** Infrastructure OVH interne, pas de dépendance externe, données sécurisées.
