# Comment Obtenir une Clé API LLM

Pour utiliser la fonctionnalité de génération d'idées d'amélioration produit, vous devez configurer une clé API.

## Option 1: OpenAI (Recommandé)

### Étape 1: Créer un compte
1. Allez sur https://platform.openai.com/
2. Cliquez sur "Sign up" ou "Log in"
3. Créez un compte ou connectez-vous

### Étape 2: Ajouter des crédits
1. Allez dans "Settings" → "Billing"
2. Cliquez sur "Add payment method"
3. Ajoutez une carte de crédit
4. Ajoutez des crédits (minimum ~$5 pour commencer)

### Étape 3: Créer une clé API
1. Allez dans "API keys" (https://platform.openai.com/api-keys)
2. Cliquez sur "Create new secret key"
3. Donnez un nom (ex: "OVH Tracker")
4. **COPIEZ LA CLÉ IMMÉDIATEMENT** (elle ne sera affichée qu'une fois)
5. Collez-la dans votre fichier `.env` comme `OPENAI_API_KEY`

### Coûts
- **GPT-4o-mini** (recommandé): ~$0.15 par million de tokens d'entrée
- Pour la génération d'idées: environ $0.001-0.01 par requête
- Très économique pour un usage modéré

## Option 2: Anthropic Claude

### Étape 1: Créer un compte
1. Allez sur https://console.anthropic.com/
2. Créez un compte ou connectez-vous

### Étape 2: Ajouter des crédits
1. Allez dans "Billing"
2. Ajoutez une méthode de paiement
3. Ajoutez des crédits

### Étape 3: Créer une clé API
1. Allez dans "API Keys"
2. Cliquez sur "Create Key"
3. Donnez un nom
4. **COPIEZ LA CLÉ** et collez-la dans `.env` comme `ANTHROPIC_API_KEY`
5. Ajoutez aussi `LLM_PROVIDER=anthropic`

### Coûts
- **Claude 3 Haiku**: ~$0.25 par million de tokens
- Similaire à OpenAI en termes de coût

## Option 3: Sans Clé API (Fallback)

Si vous n'avez pas de clé API, l'application fonctionnera quand même mais utilisera un système de génération d'idées basé sur des règles (moins intelligent mais gratuit).

## Configuration sur la VM

Une fois que vous avez votre clé API :

1. **Créez le fichier `.env`** :
   ```bash
   cd /chemin/vers/complaints_tracker/backend
   cp .env.example .env
   nano .env  # ou vi .env
   ```

2. **Ajoutez votre clé** :
   ```bash
   OPENAI_API_KEY=sk-votre-vraie-cle-ici
   ```

3. **Sécurisez le fichier** :
   ```bash
   chmod 600 .env  # Seul le propriétaire peut lire/écrire
   ```

4. **Redémarrez l'application** pour que les changements prennent effet

## Vérification

Pour vérifier que la clé fonctionne, testez la génération d'idées dans l'interface web. Si vous voyez des erreurs, vérifiez :
- La clé est correctement copiée (sans espaces)
- Les crédits sont suffisants
- L'API n'est pas bloquée par un firewall


