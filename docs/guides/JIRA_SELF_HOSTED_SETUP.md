# Guide : Configuration Jira Self-Hosted

## Informations nécessaires

Pour intégrer votre Jira self-hosted, j'aurai besoin des informations suivantes :

### 1. URL du serveur Jira

- URL complète de votre instance Jira
- Exemples :
  - `https://jira.votre-domaine.com`
  - `http://jira.local:8080`
  - `https://jira.internal.company.com`
- **Important** : L'URL doit être accessible depuis l'application (même réseau ou VPN)

### 2. Version Jira

- Version exacte de votre Jira (ex: Jira Server 8.22, Data Center 9.0)
- Détermine les méthodes d'authentification disponibles
- Vérifier : Administration → System → System Info

### 3. Méthode d'authentification

Selon votre version Jira, choisir une méthode :

#### Option A : Personal Access Token (Recommandé - Jira 8.14+)

1. Se connecter à Jira
2. Aller dans : Account Settings → Security → API tokens
3. Créer un nouveau token
4. **Copier le token** (affiché une seule fois)

**Avantages** :
- Plus sécurisé que Basic Auth
- Pas besoin de mot de passe
- Révoquable facilement

#### Option B : Basic Auth (Jira < 8.14 ou si PAT non disponible)

1. Créer un compte de service dans Jira (recommandé)
2. Ou utiliser un compte utilisateur existant
3. **Username** : nom d'utilisateur
4. **Password** : mot de passe (ou token API si Basic Auth avec token)

**Note** : Moins sécurisé, à éviter si possible

#### Option C : OAuth 2.0 (Jira 8.22+)

1. Créer une application OAuth dans Jira
2. Administration → Applications → Application links
3. Créer application OAuth
4. Récupérer **Client ID** et **Client Secret**

**Avantages** :
- Plus sécurisé
- Refresh token automatique

### 4. Permissions requises

Le compte utilisé doit avoir les permissions suivantes :

- ✅ **Créer des issues** dans le projet cible
- ✅ **Lire les issues** créées
- ✅ **Modifier les issues** (pour synchronisation statut)
- ✅ **Voir le projet** (permissions de base)

**Recommandation** : Utiliser un compte de service dédié (pas un compte utilisateur)

### 5. Projet Jira

- **Clé du projet** : Ex: "PROJ", "DEV", "IMPROV", "BACKLOG"
- **Type de ticket par défaut** : Task, Bug, Story, Improvement, etc.
- Vérifier que le type existe dans le projet

### 6. Certificat SSL (si applicable)

Si votre Jira utilise HTTPS avec certificat auto-signé :

- Option `verify_ssl=false` sera disponible dans la configuration
- **Attention** : Moins sécurisé, à utiliser seulement si nécessaire

## Configuration dans l'application

Une fois les informations collectées, configuration via l'interface :

1. Aller dans **Settings** → **Jira Integration**
2. Sélectionner le **workspace** (configuration par workspace)
3. Remplir le formulaire :
   - URL Jira
   - Méthode d'authentification
   - Credentials (token, username/password, ou OAuth)
   - Projet et type de ticket
4. Cliquer sur **Test Connection** pour vérifier
5. Sauvegarder

## Test de connexion

L'application testera automatiquement :

- ✅ Connexion au serveur Jira
- ✅ Authentification (token/credentials valides)
- ✅ Accès au projet
- ✅ Permissions (créer issue)
- ✅ Certificat SSL (si HTTPS)

## Dépannage

### Erreur : "Connection refused" ou "Timeout"

- Vérifier que Jira est accessible depuis l'application
- Vérifier réseau/VPN si Jira interne
- Vérifier firewall/ports (généralement 8080 ou 443)

### Erreur : "Authentication failed"

- Vérifier token/credentials
- Vérifier que le compte a les permissions nécessaires
- Vérifier que le compte n'est pas désactivé

### Erreur : "SSL certificate verification failed"

- Activer `verify_ssl=false` dans la configuration
- Ou ajouter certificat dans le conteneur Docker

### Erreur : "Project not found"

- Vérifier la clé du projet (exacte, sensible à la casse)
- Vérifier que le compte a accès au projet

## Sécurité

- ✅ Credentials stockés dans `workspace_settings` (chiffré si possible)
- ✅ Pas de credentials dans les logs
- ✅ Test connexion avant utilisation
- ✅ Timeout requêtes (éviter blocage)
- ✅ Rate limiting respecté

## Support

Si vous rencontrez des problèmes :

1. Vérifier les logs de l'application
2. Tester la connexion Jira manuellement (curl, Postman)
3. Vérifier les permissions du compte
4. Contacter l'administrateur Jira si nécessaire













