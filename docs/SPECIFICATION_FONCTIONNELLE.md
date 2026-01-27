# 📋 Spécification Fonctionnelle - OVH Customer Feedbacks Tracker

**Version:** 1.0.8  
**Date:** Janvier 2026  
**Statut:** Beta

> **Note:** Ce projet a été développé **100% avec VibeCoding** (Cursor AI), démontrant la puissance de l'assistance IA pour créer des applications complètes et professionnelles.

---

## 🎯 Vue d'ensemble

L'application **OVH Customer Feedbacks Tracker** est une plateforme de monitoring en temps réel qui collecte, analyse et visualise les retours clients sur les services OVH depuis plusieurs sources en ligne.

---

## 📊 Fonctionnalités principales

### 1. Collecte de données (Scraping)

#### 1.1 Sources supportées
- ✅ **X/Twitter** : Via Nitter instances (10+ instances avec rotation automatique)
- ✅ **Reddit** : Via API JSON et RSS feeds
- ✅ **GitHub** : Issues et discussions via API v3
- ✅ **Stack Overflow** : Questions via API v2.3
- ✅ **Trustpilot** : Avis clients via HTML scraping et API
- ✅ **OVH Forum** : Discussions communautaires via HTML scraping
- ✅ **Mastodon** : Posts via API Mastodon
- ✅ **G2 Crowd** : Avis logiciels via HTML scraping
- ✅ **LinkedIn** : Posts publics via API (si configuré)

#### 1.2 Stratégies de fallback
Chaque scraper implémente une stratégie multi-niveaux :

1. **Méthode primaire** : API ou scraping HTML spécifique au site
2. **Google Search Fallback** : Recherche universelle via Google (`site:domain.com query`)
3. **RSS Detector** : Détection automatique et parsing de feeds RSS/Atom
4. **Final** : Liste vide (pas de données mockées)

#### 1.3 Système de keywords

**Keywords de base (configurables dans Settings)** :
- **Brands** : OVH, OVHCloud, Kimsufi, etc.
- **Products** : OVH domain, OVH hosting, OVH VPS, OVH dedicated, etc. (13 produits essentiels)
- **Problems** : OVH complaint, OVH support, OVH billing, etc.
- **Leadership** : Michel Paulin, Octave Klaba, OVH CEO, etc. (8 termes condensés)

**Keywords utilisateur** : Keywords additionnels définis par l'utilisateur

**Combinaison** : Les keywords de base et utilisateur sont automatiquement combinés lors du scraping.

#### 1.4 Score de pertinence (Relevance Scoring)

Chaque post scrapé reçoit un score de pertinence (0-100%) basé sur :
- **OVH Brands (40%)** : Mentions de marques OVH
- **OVH URLs (30%)** : Liens vers des domaines OVH
- **OVH Leadership (20%)** : Mentions de la direction OVH
- **OVH Products (10%)** : Mentions de produits OVH

**Filtrage automatique** : Posts avec score < 30% sont automatiquement filtrés avant insertion en base.

---

### 2. Analyse et traitement

#### 2.1 Analyse de sentiment
- **Moteur** : VADER (vaderSentiment)
- **Classification** : Positif / Négatif / Neutre
- **Score** : -1.0 (très négatif) à +1.0 (très positif)

#### 2.2 Détection de langue
- **Langues supportées** : Français, Anglais, Autres
- **Méthode** : TextBlob ou heuristique basée sur mots communs

#### 2.3 Détection de pays
- **Méthode** : Analyse du contenu et des métadonnées
- **Affichage** : Carte interactive sur le dashboard

#### 2.4 Opportunity Score (0-100)
Score additif pour prioriser les posts nécessitant une attention :
```
opportunity_score = relevance_score + sentiment_score + recency_score + engagement_score
```
- **relevance_score (0-30 points)** : Score de pertinence du post (relevance_score × 30)
- **sentiment_score (0-40 points)** : 
  - Négatif = 40 points
  - Neutre = 15 points
  - Positif = 5 points
- **recency_score (0-20 points)** :
  - < 7 jours = 20 points
  - < 30 jours = 15 points
  - < 90 jours = 10 points
  - Sinon = 5 points
- **engagement_score (0-10 points)** : Basé sur vues (0.01 par vue), commentaires (3 par commentaire), réactions (2 par réaction), plafonné à 10 points

**Note** : L'ancien Priority Score multiplicatif (`sentiment × keyword_relevance × recency`) a été remplacé par ce système additif plus représentatif sur une échelle 0-100.

---

### 3. Interface utilisateur

#### 3.1 Page "Feedbacks Collection" (`/scraping`)
- **Configuration keywords** : Ajout de keywords personnalisés
- **Lancement scraping** : Bouton "Scrape New Data" pour tous les scrapers
- **Scrapers individuels** : Boutons pour chaque source
- **Suivi progression** : Barre de progression en temps réel avec bouton annulation
- **Filtres** : Recherche texte, sentiment, source, langue, produit, dates
- **Statistiques** : Total, positif, négatif, neutre, récent
- **Export** : Export CSV des posts filtrés
- **Affichage posts** : Cards avec score de pertinence, sentiment, métadonnées

#### 3.2 Page "Dashboard Analytics" (`/dashboard`)

**Section "Posts Statistics"** :
- **Métriques satisfaction** : Pourcentage avec échelle dynamique :
  - ≥ 70% : Vert (Excellent Satisfaction) 😊
  - 50-69% : Jaune (Good Satisfaction) 😐
  - 30-49% : Orange (Fair Satisfaction) 😐
  - < 30% : Rouge (Poor Satisfaction) 😞
- **Bouton "Critical Posts"** : Badge avec nombre de posts négatifs récents
- **Bouton "Go to Posts"** : Scroll vers la section "All Posts"

**Section "What's Happening"** :
- **Insights** : Alertes et recommandations basées sur l'IA
- **Actions recommandées** : Suggestions contextuelles

**Section "Analytics"** :
- **Timeline** : Graphique temporel des posts
- **Histogramme** : Distribution par période
- **Distribution par produit** : Graphique en barres
- **Distribution par source** : Graphique circulaire
- **Distribution par sentiment** : Graphique en barres
- **Carte géographique** : Distribution par pays

**Section "All Posts"** :
- **Filtres complets** : Tri, sentiment, source, langue, dates
- **Affichage posts** : Cards avec HTML rendu (pas de texte brut)
- **Pagination** : Chargement progressif
- **Actions** : Preview, View, Save to backlog

**Drawer "Critical Posts"** :
- **Filtres** : Période (1/7/30/90 jours), Tri (score/récent)
- **Titre dynamique** : "Critical Posts (Negative - Last X days)"
- **Compteur en rouge** : Nombre de posts critiques
- **Actions** : Ajouter au backlog directement depuis le drawer

#### 3.3 Page "Improvements Opportunities" (`/improvements`)
- **Pain Points** : Top 5 problèmes récurrents (30 derniers jours) détectés automatiquement via analyse de mots-clés
- **Distribution par produit** : Graphique avec scores d'opportunité (0-100) classés par ordre décroissant
- **Filtrage par produit** : Clic sur un produit dans la distribution → Filtre automatique de l'analyse LLM et des posts à revoir
- **Bouton "Clear Filter"** : Réinitialise le filtre produit pour afficher toutes les données
- **Analyse LLM** : Analyse contextuelle des problèmes avec overlay de chargement limité à la section d'analyse
- **Posts à revoir** : Liste triée par opportunity score avec filtres (recherche, langue, source, date)
- **Modale de prévisualisation** : Clic sur un post → Affichage complet du contenu, métadonnées (auteur, date, sentiment, score) et lien vers le post original
- **Opportunity Score** : Score sur 0-100 calculé à partir de :
  - Pertinence (0-30 points) : Score de pertinence du post
  - Sentiment (0-40 points) : Négatif = 40, Neutre = 15, Positif = 5
  - Récence (0-20 points) : < 7 jours = 20, < 30 jours = 15, < 90 jours = 10, sinon = 5
  - Engagement (0-10 points) : Basé sur vues, commentaires et réactions

#### 3.4 Page "Settings" (`/settings`)
- **Configuration API Keys** : OpenAI, Anthropic, Google, GitHub, Trustpilot
- **Sélection provider LLM** : OpenAI ou Anthropic
- **Gestion Base Keywords** : Édition des keywords de base (brands, products, problems, leadership)
- **Email Notifications** : Configuration des triggers de notification par email pour les posts problématiques
  - Création/édition de triggers avec conditions personnalisables
  - Configuration des emails destinataires directement dans les triggers
  - Test de connexion SMTP
  - Historique des notifications envoyées

#### 3.5 Page "Scraping Logs" (`/logs`)
- **Affichage logs** : Liste des opérations de scraping
- **Filtres** : Source, niveau (info/success/warning/error), limite
- **Statistiques** : Total logs, erreurs, succès, sources actives
- **Actualisation auto** : Option pour rafraîchir toutes les 5 secondes

---

### 4. Base de données

#### 4.1 Schéma principal

**Table `posts`** :
- `id` : BIGINT PRIMARY KEY
- `source` : TEXT (nom de la source)
- `author` : TEXT (auteur du post)
- `content` : TEXT (contenu du post, HTML)
- `url` : TEXT (URL originale)
- `created_at` : TEXT (date ISO)
- `sentiment_score` : REAL (-1.0 à +1.0)
- `sentiment_label` : TEXT (positive/negative/neutral)
- `language` : TEXT (fr/en/other/unknown)
- `country` : TEXT (code pays)
- `relevance_score` : REAL (0.0 à 1.0) ⭐ **NOUVEAU**

**Table `base_keywords`** :
- `id` : BIGINT PRIMARY KEY
- `category` : TEXT (brands/products/problems/leadership)
- `keyword` : TEXT (le keyword)
- `created_at` : TEXT (date de création)

**Table `jobs`** :
- `id` : TEXT PRIMARY KEY (UUID)
- `status` : TEXT (pending/running/completed/failed/cancelled)
- `progress` : JSON (total, completed)
- `results` : JSON (résultats par source)
- `errors` : JSON (erreurs rencontrées)
- `created_at` : TEXT
- `updated_at` : TEXT

**Table `notification_triggers`** :
- `id` : BIGINT PRIMARY KEY
- `name` : TEXT (nom du trigger)
- `enabled` : BOOLEAN (actif/inactif)
- `conditions` : TEXT JSON (sentiment, relevance_score_min, sources, language, etc.)
- `emails` : TEXT JSON (liste des emails destinataires)
- `cooldown_minutes` : INTEGER (délai minimum entre notifications)
- `max_posts_per_email` : INTEGER (nombre max de posts par email)
- `last_notification_sent_at` : TEXT (timestamp dernière notification)
- `created_at` : TEXT
- `updated_at` : TEXT

**Table `email_notifications`** :
- `id` : BIGINT PRIMARY KEY
- `trigger_id` : BIGINT (référence au trigger)
- `post_ids` : TEXT JSON (IDs des posts inclus dans l'email)
- `recipient_emails` : TEXT JSON (emails destinataires)
- `sent_at` : TEXT (timestamp d'envoi)
- `status` : TEXT (sent/failed/pending)
- `error_message` : TEXT (message d'erreur si échec)
- `created_at` : TEXT

#### 4.2 Index
- `idx_posts_source` : Sur `source`
- `idx_posts_sentiment` : Sur `sentiment_label`
- `idx_posts_created` : Sur `created_at DESC`
- `idx_posts_language` : Sur `language`
- `idx_posts_source_date` : Sur `(source, created_at DESC)`

---

### 5. API REST

#### 5.1 Endpoints de scraping
- `POST /scrape/x` : Scraper X/Twitter
- `POST /scrape/reddit` : Scraper Reddit
- `POST /scrape/github` : Scraper GitHub
- `POST /scrape/stackoverflow` : Scraper Stack Overflow
- `POST /scrape/trustpilot` : Scraper Trustpilot
- `POST /scrape/ovh-forum` : Scraper OVH Forum
- `POST /scrape/mastodon` : Scraper Mastodon
- `POST /scrape/g2-crowd` : Scraper G2 Crowd
- `POST /scrape/linkedin` : Scraper LinkedIn
- `POST /scrape/keywords` : Scraping multi-keywords en arrière-plan

#### 5.2 Endpoints de gestion des jobs
- `GET /scrape/jobs/{job_id}` : Statut d'un job
- `POST /scrape/jobs/{job_id}/cancel` : Annuler un job

#### 5.3 Endpoints de données
- `GET /posts` : Liste des posts (avec filtres : limit, offset, language, product, sentiment, source, date_from, date_to)
- `GET /api/stats` : Statistiques globales
- `GET /api/pain-points` : Points de douleur récurrents
- `GET /api/product-opportunities` : Opportunités par produit
- `GET /api/posts-for-improvement` : Posts triés par opportunity score (0-100)
- `GET /api/product-analysis/{product_name}` : Analyse LLM d'un produit ⭐ **NOUVEAU**

#### 5.4 Endpoints de configuration
- `GET /api/llm-config` : Configuration LLM actuelle
- `POST /api/llm-config` : Sauvegarder configuration LLM
- `GET /settings/base-keywords` : Keywords de base ⭐ **NOUVEAU**
- `POST /settings/base-keywords` : Sauvegarder keywords de base ⭐ **NOUVEAU**

#### 5.5 Endpoints de notifications email
- `GET /api/email/triggers` : Liste tous les triggers
- `GET /api/email/triggers/{id}` : Détails d'un trigger
- `POST /api/email/triggers` : Créer un trigger
- `PUT /api/email/triggers/{id}` : Modifier un trigger
- `DELETE /api/email/triggers/{id}` : Supprimer un trigger
- `POST /api/email/triggers/{id}/toggle` : Activer/désactiver un trigger
- `GET /api/email/config` : Statut de la configuration SMTP
- `POST /api/email/test` : Tester l'envoi d'email
- `GET /api/email/notifications` : Historique des notifications

#### 5.6 Endpoints utilitaires
- `GET /health` : Health check avec vérifications DB
- `GET /api/version` : Version de l'application
- `GET /api/logs` : Logs de scraping

---

### 6. Notifications Email

#### 6.1 Système de triggers
Les triggers permettent de configurer des alertes automatiques par email lorsque des posts problématiques sont détectés.

**Conditions supportées :**
- **Sentiment** : All, Negative, Positive, Neutral
- **Score de pertinence minimum** : 0.0 à 1.0
- **Sources** : Filtre par sources spécifiques (X/Twitter, Reddit, GitHub, etc.)
- **Langue** : All, French, English, etc.
- **Score de priorité minimum** : Optionnel (0.0 à 1.0)

**Configuration :**
- **Emails destinataires** : Liste d'emails (max 50) configurés directement dans le trigger
- **Cooldown** : Délai minimum entre notifications (défaut: 60 minutes) pour éviter le spam
- **Max posts par email** : Nombre maximum de posts inclus dans un email (défaut: 10)

**Fonctionnement :**
1. Lorsqu'un nouveau post est inséré en base de données
2. Le système vérifie tous les triggers actifs
3. Si le post correspond aux conditions d'un trigger
4. Vérification du cooldown (évite les notifications trop fréquentes)
5. Récupération des posts problématiques récents (24h) correspondant au trigger
6. Envoi d'un email groupé avec les posts les plus prioritaires
7. Logging de la notification dans `email_notifications`

**Configuration SMTP :**
Les paramètres SMTP sont configurés via variables d'environnement :
- `SMTP_HOST` : Serveur SMTP (ex: smtp.gmail.com)
- `SMTP_PORT` : Port SMTP (ex: 587)
- `SMTP_USER` : Utilisateur SMTP
- `SMTP_PASSWORD` : Mot de passe SMTP
- `SMTP_FROM_EMAIL` : Email expéditeur
- `SMTP_FROM_NAME` : Nom expéditeur

**Template d'email :**
- Format HTML avec en-tête, contenu des posts, et footer
- Format texte alternatif pour compatibilité
- Inclut : source, auteur, date, contenu (tronqué), score de pertinence, lien vers le post

### 7. Intégration LLM

#### 6.1 Providers supportés
- **OpenAI** : GPT-4o-mini (par défaut)
- **Anthropic** : Claude 3 Haiku

#### 6.2 Fonctionnalités LLM
- **Actions recommandées** : Suggestions contextuelles basées sur les posts filtrés
- **Idées d'amélioration** : Génération d'idées depuis le backlog
- **Analyse produit** : Résumé des problèmes pour un produit spécifique ⭐ **NOUVEAU**
- **Fallback** : Analyse basée sur règles si LLM indisponible

---

### 7. Sécurité et performance

#### 7.1 Sécurité
- **CORS** : Restrictions sur origines autorisées
- **Validation** : Validation Pydantic sur tous les endpoints
- **Rate Limiting** : Limitation des requêtes (si configuré)
- **Protection API Keys** : Stockage sécurisé dans `.env`
- **HTML Escaping** : Protection XSS sur le frontend

#### 7.2 Performance
- **Caching** : Cache en mémoire pour endpoints critiques (TTL configurable)
- **Index DB** : Index optimisés pour requêtes fréquentes
- **Async/Await** : Opérations asynchrones pour I/O
- **Pagination** : Chargement progressif des données

---

### 8. Thème et accessibilité

#### 8.1 Thème
- **Light/Dark Mode** : Basculement via bouton dans le menu
- **Synchronisation** : Préférence sauvegardée dans localStorage
- **Cohérence** : Thème uniforme sur toutes les pages

#### 8.2 Accessibilité
- **Navigation clavier** : Support des raccourcis clavier
- **ARIA labels** : Labels pour lecteurs d'écran
- **Contraste** : Respect des standards de contraste

---

## 🔄 Flux de données

1. **Utilisateur lance scraping** → `POST /scrape/keywords`
2. **Backend combine keywords** → Base keywords + User keywords
3. **Scrapers exécutés** → Pour chaque source avec fallbacks
4. **Relevance Scoring** → Filtrage automatique (< 30%)
5. **Sentiment Analysis** → Classification automatique
6. **Insertion DB** → Stockage avec métadonnées
7. **Notifications email** → Vérification des triggers et envoi d'alertes si nécessaire
8. **Frontend affiche** → Dashboard avec visualisations

---

## 📈 Métriques et KPIs

### KPIs Dashboard
- **Total Posts** : Nombre total de posts en base
- **Positive Satisfaction** : Pourcentage de posts positifs (avec échelle dynamique)
- **Negative Posts** : Nombre de posts négatifs
- **Neutral Posts** : Nombre de posts neutres
- **Recent Posts** : Posts des 7 derniers jours

### Métriques de qualité
- **Relevance Score** : Score moyen de pertinence des posts
- **Source Distribution** : Répartition par source
- **Sentiment Distribution** : Répartition par sentiment
- **Geographic Distribution** : Répartition par pays

---

## 🚀 Améliorations futures

- [ ] Support multi-langue amélioré (modèles de sentiment multilingues)
- [ ] Détection automatique de catégories de problèmes
- [ ] Alertes email/Slack pour posts critiques
- [ ] Tagging manuel par équipe support
- [ ] Détection de doublons cross-platform
- [ ] Optimisation RateCard basée sur mentions de prix concurrents

---

**Dernière mise à jour** : Janvier 2026

