# Guide de configuration de l'API LinkedIn

Ce guide vous explique comment obtenir et configurer vos propres identifiants API LinkedIn pour activer le scraping de posts LinkedIn dans l'application.

## Prérequis

- Un compte LinkedIn
- Accès au [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)

## Étapes de configuration

### 1. Créer une application LinkedIn

1. Allez sur [https://www.linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
2. Cliquez sur **"Create app"**
3. Remplissez le formulaire :
   - **App name** : Choisissez un nom pour votre application (ex: "OVH Feedback Tracker")
   - **LinkedIn Page** : Sélectionnez ou créez une page LinkedIn associée
   - **Privacy policy URL** : URL de votre politique de confidentialité
   - **App logo** : Logo optionnel
4. Acceptez les conditions d'utilisation
5. Cliquez sur **"Create app"**

### 2. Obtenir les identifiants

Une fois l'application créée :

1. Allez dans l'onglet **"Auth"** de votre application
2. Notez les valeurs suivantes :
   - **Client ID** : Identifiant unique de votre application
   - **Client Secret** : Secret de votre application (cliquez sur "Show" pour le révéler)

### 3. Configurer les permissions

1. Dans l'onglet **"Auth"**, sous **"OAuth 2.0 scopes"**, sélectionnez les permissions nécessaires :
   - `r_liteprofile` : Accès au profil de base
   - `r_basicprofile` : Accès au profil de base (si disponible)
   - `r_organization_social` : Accès aux posts d'organisation (recommandé)
   - `r_social_basic` : Accès de base aux posts sociaux

2. Cliquez sur **"Update"** pour sauvegarder

### 4. Configurer l'URL de redirection

1. Dans l'onglet **"Auth"**, sous **"Redirect URLs"**, ajoutez :
   - `http://localhost:8000` (pour le développement)
   - Votre URL de production si applicable

2. Cliquez sur **"Update"**

### 5. Ajouter les identifiants dans l'application

1. Ouvrez le fichier `.env` dans le dossier `backend/`
2. Ajoutez les lignes suivantes :
   ```env
   LINKEDIN_CLIENT_ID=votre_client_id_ici
   LINKEDIN_CLIENT_SECRET=votre_client_secret_ici
   ```
3. Remplacez `votre_client_id_ici` et `votre_client_secret_ici` par vos valeurs réelles
4. Sauvegardez le fichier

### 6. Redémarrer l'application

Redémarrez le serveur backend pour que les nouvelles variables d'environnement soient prises en compte.

## Utilisation

Une fois configuré, vous pouvez utiliser le scraper LinkedIn :

1. Allez sur la page **"Feedbacks Collection"**
2. Cliquez sur **"Scrape LinkedIn"**
3. Les posts LinkedIn correspondant à votre requête seront collectés

## Limitations et notes importantes

### Limitations de l'API LinkedIn

- **Permissions limitées** : L'API LinkedIn v2 a des capacités de recherche limitées pour les posts publics
- **Rate limits** : LinkedIn impose des limites de taux d'appel (varie selon le type de compte)
- **Permissions requises** : Certaines fonctionnalités nécessitent des permissions spécifiques qui peuvent nécessiter une validation par LinkedIn

### Alternatives

Si l'API LinkedIn ne retourne pas de résultats satisfaisants, cela peut être dû à :
- Limitations de l'API v2 pour la recherche de posts publics
- Permissions insuffisantes
- Restrictions géographiques

Dans ce cas, l'application retournera une liste vide sans erreur, et vous pourrez continuer à utiliser les autres sources de scraping.

## Dépannage

### Erreur "Authentication failed"

- Vérifiez que votre `CLIENT_ID` et `CLIENT_SECRET` sont corrects
- Assurez-vous qu'ils sont bien dans le fichier `.env`
- Vérifiez qu'il n'y a pas d'espaces supplémentaires

### Erreur "Access forbidden"

- Vérifiez que les permissions OAuth sont correctement configurées dans le Developer Portal
- Certaines permissions peuvent nécessiter une validation par LinkedIn

### Aucun résultat retourné

- C'est normal si l'API LinkedIn v2 a des limitations pour la recherche de posts
- L'application continuera à fonctionner avec les autres sources

## Ressources

- [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
- [Documentation LinkedIn API v2](https://docs.microsoft.com/en-us/linkedin/)
- [Guide OAuth 2.0 LinkedIn](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authentication)

## Support

Si vous rencontrez des problèmes, consultez les logs de l'application dans la page **"Scraping Logs"** pour plus de détails.

