# 🎯 OVH Customer Feedbacks Tracker

> Plateforme de monitoring en temps réel qui collecte et analyse les **retours clients** et **feedback** sur les services OVH depuis plusieurs sources.

[![Version](https://img.shields.io/badge/version-1.0.8-blue.svg)](VERSION)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](docs/changelog/STATUS.md)
[![VibeCoding](https://img.shields.io/badge/made%20with-VibeCoding-00D9FF.svg)](https://cursor.sh)

> **💡 Note:** Ce projet a été développé **100% avec VibeCoding** (Cursor AI), démontrant la puissance de l'assistance IA pour créer des applications complètes et professionnelles.

---

## 🚀 Démarrage rapide (3 étapes simples)

### ✅ Étape 1 : Vérifier Python
Ouvrir un terminal et taper :
```bash
python --version
```
**Doit afficher :** `Python 3.11.x` ou supérieur  
**Si erreur :** Installer depuis [python.org](https://www.python.org/downloads/) (⚠️ cocher "Add Python to PATH")

### ✅ Étape 2 : Installer les dépendances
```bash
cd backend
pip install -r requirements.txt
```
⏱️ *Cela prend 2-5 minutes (téléchargement des bibliothèques)*

### ✅ Étape 3 : Démarrer l'application

**Windows :**
```powershell
.\scripts\start\start_server.ps1
```

**Linux/Mac :**
```bash
bash scripts/app/start.sh
```

**Vous devriez voir :** `INFO: Uvicorn running on http://127.0.0.1:8000`

### 🌐 Accéder à l'application

1. **Ouvrir votre navigateur** (Chrome, Firefox, Edge...)
2. **Aller à :** http://localhost:8000
3. **C'est prêt !** 🎉

### 🛑 Arrêter l'application

**Windows :**
```powershell
.\scripts\start\stop.sh
```

**Linux/Mac :**
```bash
bash scripts/app/stop.sh
```

### 🧪 Tester rapidement

1. Cliquer sur **"Feedbacks Collection"** dans le menu
2. Cliquer sur **"Scrape Reddit"** (ou un autre bouton)
3. Attendre quelques secondes
4. Voir le résultat dans les logs ou le dashboard

---

📖 **Guide détaillé pour débutants (avec dépannage) :** [docs/guides/QUICK_START_SIMPLE.md](docs/guides/QUICK_START_SIMPLE.md)  
📖 **Guide complet avec tests avancés :** [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)

---

## � Déploiement Docker (Production)

Pour un déploiement robuste en production avec isolation des processus :

### Installation Docker

**Linux :**
```bash
./scripts/install-docker.sh --migrate
```

**Windows :**
```powershell
.\scripts\install-docker.ps1 -Migrate
```

### Architecture Docker

- **PostgreSQL** : Base de données robuste (remplace DuckDB)
- **Redis** : File d'attente pour les jobs de scraping
- **API** : Gunicorn avec 4 workers Uvicorn
- **Worker** : Processus isolé pour le scraping (Selenium/Chrome)
- **Scheduler** : Jobs planifiés (APScheduler)

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f

# Mettre à jour
./scripts/update-docker.sh

# Redémarrer
docker compose restart
```

📖 **Documentation complète :** [docs/guides/DOCKER_ARCHITECTURE.md](docs/guides/DOCKER_ARCHITECTURE.md)

---

## �📁 Structure du projet

```
ovh-complaints-tracker/
│
├── 🎨 frontend/              # Interface utilisateur (HTML/CSS/JS)
│   ├── index.html            # Page principale (Scraping & Configuration)
│   ├── logs.html             # Page des logs
│   ├── dashboard/            # Dashboard Analytics
│   ├── improvements/         # Page d'améliorations
│   └── assets/                # Assets statiques (logos, images)
│       └── logo/             # Logos OVHcloud
│
├── ⚙️ backend/               # API Backend (Python/FastAPI)
│   ├── app/
│   │   ├── main.py           # Point d'entrée FastAPI
│   │   ├── scraper/          # Modules de scraping (X, Reddit, GitHub...)
│   │   │   ├── google_search_fallback.py  # Fallback universel via Google Search
│   │   │   └── rss_detector.py             # Détection et parsing de feeds RSS/Atom
│   │   ├── analysis/         # Analyse de sentiment et pertinence
│   │   ├── config/           # Configuration (keywords de base)
│   │   └── db.py             # Gestion base de données
│   └── requirements.txt      # Dépendances Python
│
├── 📚 docs/                  # Documentation complète
│   ├── guides/               # Guides d'utilisation
│   ├── architecture/          # Documentation technique
│   ├── audits/               # Rapports d'audit
│   └── changelog/            # Historique des changements
│
└── 🔧 scripts/               # Scripts d'administration
    ├── start/                # Scripts de démarrage
    ├── install/              # Scripts d'installation
    └── utils/                # Utilitaires
```

---

## 🏗️ Architecture en 30 secondes

```
┌─────────────┐
│  Frontend   │  →  Pages HTML/JS (Scraping, Dashboard, Logs)
└──────┬──────┘
       │ HTTP
┌──────▼──────┐
│   Backend   │  →  FastAPI + Scrapers + DuckDB
│  (FastAPI)  │
└──────┬──────┘
       │
┌──────▼──────┐
│  Scrapers   │  →  X/Twitter, Reddit, GitHub, Stack Overflow...
│             │     + Google Search Fallback + RSS Detector
└──────┬──────┘
       │
┌──────▼──────┐
│  Database   │  →  DuckDB (posts, logs, queries)
└─────────────┘
```

**Flux de données:**
1. **Scrapers** collectent les posts depuis différentes sources (avec fallbacks Google Search et RSS)
2. **Relevance Scoring** filtre les posts non pertinents (< 30%)
3. **Analyse de sentiment** (VADER) classe chaque post
4. **Base de données** stocke les posts avec métadonnées (relevance_score inclus)
5. **Notifications email** vérifient les triggers et envoient des alertes si nécessaire
6. **API REST** expose les données au frontend
7. **Dashboard** visualise les données avec Chart.js et sections interactives

📖 **Architecture détaillée:** [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

---

## 🎯 Fonctionnalités

- ✅ **Scraping multi-sources** : X/Twitter, Reddit, GitHub, Stack Overflow, Trustpilot, G2 Crowd, OVH Forum, Mastodon, Google News, LinkedIn
- ✅ **Fallback strategies** : Google Search fallback et RSS/Atom feed detection pour maximiser la collecte de données
- ✅ **Base Keywords System** : Keywords de base configurables (brands, products, problems, leadership) combinés avec keywords utilisateur
- ✅ **Relevance Scoring** : Score de pertinence automatique (0-100%) pour filtrer les posts non pertinents (< 30% filtrés)
- ✅ **Analyse de sentiment** : Classification automatique (positif/négatif/neutre) avec VADER
- ✅ **Opportunity Score** : Score additif sur 0-100 combinant pertinence (0-30), sentiment (0-40), récence (0-20) et engagement (0-10) pour prioriser les posts
- ✅ **Dashboard interactif** : Graphiques, filtres, timeline, section "All Posts" avec filtres complets
- ✅ **Posts Statistics** : Métriques de satisfaction avec échelle dynamique (Excellent/Good/Fair/Poor)
- ✅ **Critical Posts Drawer** : Accès rapide aux posts négatifs avec filtres personnalisables
- ✅ **Product Analysis** : Analyse LLM des produits avec identification des pain points et filtrage interactif
- ✅ **Filtrage par produit** : Clic sur un produit dans "Distribution by Product" pour filtrer l'analyse LLM et les posts
- ✅ **Modale de prévisualisation** : Affichage complet du contenu des posts avec lien vers la source originale
- ✅ **Opportunity Score amélioré** : Score sur 0-100 combinant pertinence, sentiment, récence et engagement
- ✅ **Pain Points** : Détection automatique des problèmes récurrents basée sur l'analyse de mots-clés
- ✅ **Logs persistants** : Suivi détaillé des opérations de scraping
- ✅ **Détection de pays** : Identification du pays depuis le contenu
- ✅ **Actions recommandées** : Suggestions basées sur l'IA (OpenAI/Anthropic)
- ✅ **Notifications email** : Alertes automatiques par email pour les posts problématiques (négatifs) avec système de triggers configurables
- ✅ **Système de jobs asynchrones** : Scraping en arrière-plan avec suivi de progression en temps réel

---

## 📚 Documentation

### Guides
- 🚀 [Démarrage rapide](docs/guides/QUICK_START.md)
- 🔑 [Configuration des clés API](docs/guides/GUIDE_API_KEYS.md)
- 🧪 [Guide de test](docs/guides/GUIDE_TEST.md)
- 🤖 [Configuration LLM](docs/guides/QUICK_START_LLM.md)

### Architecture
- 🏗️ [Architecture détaillée](docs/architecture/ARCHITECTURE.md)
- 🔒 [Vue d'ensemble sécurité](docs/architecture/SECURITY_OVERVIEW.md)
- 📝 [Implémentation](docs/architecture/IMPLEMENTATION.md)

### Audits
- 🔍 [Audit de sécurité](docs/audits/SECURITY_AUDIT.md)
- 📊 [Audit des scrapers](docs/audits/AUDIT_SCRAPERS.md)

---

## 🛠️ Technologies

| Composant | Technologie |
|-----------|------------|
| **Frontend** | HTML5, CSS3, Vanilla JS (ES6 Modules) |
| **Backend** | FastAPI (Python 3.11+) |
| **Base de données** | DuckDB |
| **Scraping** | httpx, BeautifulSoup, feedparser |
| **Analyse** | VADER Sentiment |
| **Visualisation** | Chart.js |
| **IA** | OpenAI GPT-4o-mini / Anthropic Claude |

---

## 🔧 Configuration

### Variables d'environnement

Créer `backend/.env` :

```env
# LLM Provider (openai, anthropic)
LLM_PROVIDER=openai

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optionnel
GITHUB_TOKEN=ghp_...
TRUSTPILOT_API_KEY=...

# Email Notifications (optionnel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre_email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_app
SMTP_FROM_EMAIL=votre_email@gmail.com
SMTP_FROM_NAME=OVH Feedbacks Tracker

# Configuration
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

📖 **Guide complet:** [docs/guides/GUIDE_API_KEYS.md](docs/guides/GUIDE_API_KEYS.md)

---

## 🧪 Tests

```bash
# Tests E2E
cd backend
python scripts/e2e_test_real_server.py
```

📖 **Guide de test:** [docs/guides/GUIDE_TEST.md](docs/guides/GUIDE_TEST.md)

---

## 📊 Statut du projet

- ✅ **Phase 1** : Sécurité critique - Terminée
- ✅ **Phase 2** : Sécurité avancée - Terminée
- ✅ **Nettoyage** : Projet professionnel - Terminé
- ✅ **Notifications email** : Système complet avec triggers configurables - Terminé
- 🚧 **Version** : 1.0.8 (Beta)

📖 **Statut détaillé:** [docs/changelog/STATUS.md](docs/changelog/STATUS.md)

## 🎨 Développement avec VibeCoding

Ce projet a été développé **100% avec VibeCoding** (Cursor AI), démontrant comment l'assistance IA peut accélérer le développement d'applications complètes :

- **Architecture complète** : Backend FastAPI, Frontend vanilla JS, base de données DuckDB
- **10 sources de scraping** : Implémentation de scrapers avec fallbacks intelligents
- **Système de notifications** : Email notifications avec triggers configurables
- **Analyse IA** : Intégration OpenAI/Anthropic pour recommandations et insights
- **Interface moderne** : Dashboard interactif avec visualisations Chart.js

**Technologies utilisées :** Python, FastAPI, DuckDB, HTML/CSS/JS, SMTP, VADER Sentiment, Chart.js

---

## 🤝 Contribution

Ce projet est en version **beta**. Pour toute question ou suggestion, voir la [documentation](docs/).

---

## 📄 Licence

Projet interne OVH.

---

**Dernière mise à jour:** Janvier 2026
