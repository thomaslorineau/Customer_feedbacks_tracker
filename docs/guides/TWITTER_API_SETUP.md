# Guide de configuration de l'API Twitter/X

Ce guide vous explique comment obtenir et configurer votre propre Bearer Token Twitter pour activer le scraping via l'API officielle Twitter v2.

## Prérequis

- Un compte Twitter/X
- Accès au [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)

## Étapes de configuration

### 1. Créer un compte développeur Twitter

1. Allez sur [https://developer.twitter.com/en/portal/dashboard](https://developer.twitter.com/en/portal/dashboard)
2. Si vous n'avez pas encore de compte développeur :
   - Cliquez sur **"Sign up"** ou **"Apply"**
   - Remplissez le formulaire de demande
   - Acceptez les conditions d'utilisation
   - Attendez l'approbation (peut prendre quelques jours)

### 2. Créer une application

1. Une fois connecté au Developer Portal, cliquez sur **"Create App"** ou **"Create Project"**
2. Remplissez les informations :
   - **App name** : Choisissez un nom (ex: "OVH Feedback Tracker")
   - **Use case** : Sélectionnez votre cas d'usage (ex: "Making a bot")
   - **Description** : Décrivez brièvement votre application
3. Acceptez les conditions et créez l'application

### 3. Obtenir le Bearer Token

1. Dans votre application, allez dans l'onglet **"Keys and tokens"**
2. Sous **"Bearer Token"**, cliquez sur **"Generate"** ou **"Regenerate"**
3. **Important** : Copiez immédiatement le Bearer Token, il ne sera affiché qu'une seule fois
4. Si vous l'avez perdu, vous devrez le régénérer

### 4. Configurer les permissions

1. Dans l'onglet **"App permissions"**, vérifiez que votre application a les bonnes permissions :
   - **Read-only** : Suffisant pour le scraping
   - **Read and Write** : Si vous prévoyez d'interagir avec Twitter

2. Cliquez sur **"Save"** pour sauvegarder

### 5. Ajouter le Bearer Token dans l'application

1. Ouvrez le fichier `.env` dans le dossier `backend/`
2. Ajoutez la ligne suivante :
   ```env
   TWITTER_BEARER_TOKEN=votre_bearer_token_ici
   ```
3. Remplacez `votre_bearer_token_ici` par votre Bearer Token réel
4. Sauvegardez le fichier

### 6. Redémarrer l'application

Redémarrez le serveur backend pour que la nouvelle variable d'environnement soit prise en compte.

## Utilisation

Une fois configuré, le scraper X/Twitter utilisera automatiquement l'API officielle :

1. Allez sur la page **"Feedbacks Collection"**
2. Cliquez sur **"Scrape X/Twitter"**
3. L'application utilisera l'API Twitter v2 si le Bearer Token est configuré
4. Sinon, elle utilisera Nitter (fallback gratuit)

## Avantages de l'API officielle

- **Meilleure qualité** : Données directement depuis Twitter
- **Pagination** : Récupération de plusieurs pages de résultats
- **Fiabilité** : Moins de problèmes de disponibilité que Nitter
- **Rate limits clairs** : 300 requêtes par 15 minutes

## Limitations et notes importantes

### Rate Limits

- **300 requêtes par 15 minutes** : Limite standard pour l'API v2
- L'application respecte automatiquement ces limites avec des délais entre les pages
- Si la limite est atteinte, l'application attendra avant de réessayer

### Limitations de l'API

- **Recherche récente uniquement** : L'API v2 ne permet de rechercher que les tweets des 7 derniers jours
- **Limite de résultats** : Maximum 100 tweets par requête
- **Pagination** : L'application implémente la pagination pour récupérer plus de résultats

### Coûts

- **Gratuit** : Le plan gratuit (Essential) est suffisant pour le scraping
- **Limites** : Le plan gratuit a des limites de taux d'appel
- **Upgrade** : Des plans payants sont disponibles pour plus de requêtes

## Dépannage

### Erreur "Authentication failed"

- Vérifiez que votre `TWITTER_BEARER_TOKEN` est correct
- Assurez-vous qu'il est bien dans le fichier `.env`
- Vérifiez qu'il n'y a pas d'espaces supplémentaires
- Le token doit commencer par `AAAA...`

### Erreur "Rate limit exceeded"

- L'application attend automatiquement avant de réessayer
- Vous pouvez réduire la limite de posts demandés
- Attendez 15 minutes avant de réessayer

### Aucun résultat retourné

- Vérifiez que votre requête de recherche est valide
- L'API v2 ne recherche que les tweets des 7 derniers jours
- Essayez avec des mots-clés différents

### L'application utilise toujours Nitter

- Vérifiez que le Bearer Token est bien configuré dans `.env`
- Redémarrez le serveur backend
- Vérifiez les logs pour voir si le token est détecté

## Fallback vers Nitter

Si le Bearer Token n'est pas configuré ou si l'API échoue, l'application utilisera automatiquement Nitter (instances publiques gratuites) comme solution de repli. Cela garantit que le scraping fonctionne même sans credentials Twitter.

## Ressources

- [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
- [Documentation Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)
- [Guide d'authentification Twitter](https://developer.twitter.com/en/docs/authentication/overview)
- [Rate Limits Twitter API](https://developer.twitter.com/en/docs/rate-limits)

## Support

Si vous rencontrez des problèmes, consultez les logs de l'application dans la page **"Scraping Logs"** pour plus de détails.


