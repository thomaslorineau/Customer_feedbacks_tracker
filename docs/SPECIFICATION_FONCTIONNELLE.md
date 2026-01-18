# 📋 Spécification Fonctionnelle - OVH Customer Feedbacks Tracker

**Version:** 1.0.8  
**Date:** Janvier 2026  
**Statut:** Beta

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
- ✅ **Google News** : Articles via RSS feeds
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

#### 2.4 Priority Scoring
Algorithme multiplicatif pour prioriser les posts :
```
priority_score = sentiment_value × keyword_relevance × recency_value
```
- **sentiment_value** : 1.0 (négatif), 0.5 (neutre), 0.2 (positif)
- **keyword_relevance** : Basé sur correspondance avec pain points
- **recency_value** : Décroissance exponentielle selon l'âge du post

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
- **Pain Points** : Top 5 problèmes récurrents (30 derniers jours)
- **Distribution par produit** : Graphique avec scores d'opportunité
- **Analyse produit** : Clic sur un produit → Analyse LLM des problèmes
- **Posts à revoir** : Liste triée par priority score

#### 3.4 Page "Settings" (`/settings`)
- **Configuration API Keys** : OpenAI, Anthropic, Google, GitHub, Trustpilot
- **Sélection provider LLM** : OpenAI ou Anthropic
- **Gestion Base Keywords** : Édition des keywords de base (brands, products, problems, leadership)

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
- `POST /scrape/news` : Scraper Google News
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
- `GET /api/posts-for-improvement` : Posts triés par priority score
- `GET /api/product-analysis/{product_name}` : Analyse LLM d'un produit ⭐ **NOUVEAU**

#### 5.4 Endpoints de configuration
- `GET /api/llm-config` : Configuration LLM actuelle
- `POST /api/llm-config` : Sauvegarder configuration LLM
- `GET /settings/base-keywords` : Keywords de base ⭐ **NOUVEAU**
- `POST /settings/base-keywords` : Sauvegarder keywords de base ⭐ **NOUVEAU**

#### 5.5 Endpoints utilitaires
- `GET /health` : Health check avec vérifications DB
- `GET /api/version` : Version de l'application
- `GET /api/logs` : Logs de scraping

---

### 6. Intégration LLM

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
7. **Frontend affiche** → Dashboard avec visualisations

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

