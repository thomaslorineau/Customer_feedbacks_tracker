# Comment Configurer OVH AI Endpoints

Pour utiliser les fonctionnalités d'analyse LLM (génération d'insights, recommandations d'amélioration), vous devez configurer OVH AI Endpoints.

## 🚀 OVH AI Endpoints (Recommandé)

### Étape 1: Accéder à OVH AI Endpoints
1. Allez sur https://endpoints.ai.cloud.ovh.net/
2. Connectez-vous avec votre compte OVH
3. Créez un nouveau endpoint ou utilisez un existant

### Étape 2: Récupérer les informations
1. **URL de l'endpoint** : Copiez l'URL complète de votre endpoint
   - Format : `https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1`
2. **Token API** : Générez ou copiez votre token d'authentification
3. **Nom du modèle** : Notez le nom exact du modèle (ex: `Mixtral-8x22B-Instruct-v0.1`)

### Étape 3: Configurer l'application

#### Option A : Via l'interface Settings (Recommandé)
1. Accédez à `http://localhost:8000/dashboard/settings.html`
2. Ouvrez la section **"LLM Configuration"**
3. Sélectionnez **"OVH"** comme provider
4. Remplissez :
   - **OVH API Key** : Votre token
   - **OVH Endpoint URL** : L'URL de votre endpoint
   - **OVH Model** : Le nom du modèle
5. Cliquez sur **"Save Configuration"**

#### Option B : Via fichier .env
```bash
cd backend
nano .env  # ou vi .env
```

Ajoutez :
```dotenv
LLM_PROVIDER=ovh
OVH_API_KEY=votre_token_ici
OVH_ENDPOINT_URL=https://xxx.endpoints.kepler.ai.cloud.ovh.net/api/openai_compat/v1
OVH_MODEL=Mixtral-8x22B-Instruct-v0.1
```

Sécurisez le fichier :
```bash
chmod 600 .env  # Seul le propriétaire peut lire/écrire
```

### Modèles disponibles

| Modèle | Description |
|--------|-------------|
| `Mixtral-8x22B-Instruct-v0.1` | Puissant, recommandé pour analyses |
| `Llama-3.1-70B-Instruct` | Alternative performante |
| `Mistral-7B-Instruct` | Léger, pour tests |

### Avantages OVH AI Endpoints

- ✅ **Interne OVH** : Pas de dépendance externe
- ✅ **Données sécurisées** : Données restent dans l'infrastructure OVH
- ✅ **Performance** : Endpoints optimisés
- ✅ **Coût maîtrisé** : Facturation OVH

## 🔧 Sans Clé API (Fallback)

Si vous n'avez pas configuré OVH AI Endpoints, l'application fonctionnera quand même avec :
- Analyse de sentiment (VADER) - Local, gratuit
- Détection de langue - Local, gratuit
- Scoring de pertinence - Local, gratuit

Seules les fonctionnalités suivantes nécessitent OVH AI :
- Génération d'insights "What's Happening"
- Analyse LLM des opportunités d'amélioration
- Recommandations contextuelles

## ✅ Vérification

Pour vérifier que la configuration fonctionne :

1. **Via l'interface** : Allez dans Settings > LLM Configuration
   - Le statut doit afficher "Configured" ✅

2. **Via API** :
```bash
curl http://localhost:8000/api/llm-config
```

**Réponse attendue :**
```json
{
  "provider": "ovh",
  "api_key_set": true,
  "available": true,
  "status": "configured"
}
```

## 🆘 Dépannage

### "Token invalide"
- Vérifiez que le token est correctement copié (pas d'espaces)
- Vérifiez que le token n'est pas expiré
- Régénérez le token sur endpoints.ai.cloud.ovh.net

### "Endpoint non accessible"
- Vérifiez l'URL de l'endpoint
- Vérifiez que l'endpoint est actif sur OVH
- Vérifiez la connectivité réseau

### "Modèle non trouvé"
- Vérifiez le nom exact du modèle sur votre endpoint OVH
- Le nom est sensible à la casse
