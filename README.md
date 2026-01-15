# 🎯 OVH Customer Feedbacks Tracker

> Plateforme de monitoring en temps réel qui collecte et analyse les **retours clients** et **feedback** sur les services OVH depuis plusieurs sources.

[![Version](https://img.shields.io/badge/version-1.0.8-blue.svg)](VERSION)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](docs/changelog/STATUS.md)

---

## 🚀 Démarrage rapide

```bash
# Windows (PowerShell)
.\scripts\start\start_server.ps1

# Linux/Mac
./scripts/start/start.sh

# Ou manuellement
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Puis ouvrir: **http://localhost:8000**

📖 **Guide complet:** [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)

---

## 📁 Structure du projet

```
ovh-complaints-tracker/
│
├── 🎨 frontend/              # Interface utilisateur (HTML/CSS/JS)
│   ├── index.html            # Page principale (Scraping & Configuration)
│   ├── logs.html             # Page des logs
│   ├── v2/                   # Dashboard Analytics
│   └── improvements/         # Page d'améliorations
│
├── ⚙️ backend/               # API Backend (Python/FastAPI)
│   ├── app/
│   │   ├── main.py           # Point d'entrée FastAPI
│   │   ├── scraper/          # Modules de scraping (X, Reddit, GitHub...)
│   │   ├── analysis/         # Analyse de sentiment
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
│   Backend   │  →  FastAPI + Scrapers + SQLite
│  (FastAPI)  │
└──────┬──────┘
       │
┌──────▼──────┐
│  Scrapers   │  →  X/Twitter, Reddit, GitHub, Stack Overflow...
└──────┬──────┘
       │
┌──────▼──────┐
│  Database   │  →  SQLite (posts, logs, queries)
└─────────────┘
```

**Flux de données:**
1. **Scrapers** collectent les posts depuis différentes sources
2. **Analyse de sentiment** (VADER) classe chaque post
3. **Base de données** stocke les posts avec métadonnées
4. **API REST** expose les données au frontend
5. **Dashboard** visualise les données avec Chart.js

📖 **Architecture détaillée:** [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

---

## 🎯 Fonctionnalités

- ✅ **Scraping multi-sources** : X/Twitter, Reddit, GitHub, Stack Overflow, Trustpilot, G2 Crowd, OVH Forum, Mastodon, Google News
- ✅ **Analyse de sentiment** : Classification automatique (positif/négatif/neutre)
- ✅ **Dashboard interactif** : Graphiques, filtres, timeline
- ✅ **Logs persistants** : Suivi détaillé des opérations de scraping
- ✅ **Détection de pays** : Identification du pays depuis le contenu
- ✅ **Actions recommandées** : Suggestions basées sur l'IA (OpenAI/Anthropic)

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
| **Base de données** | SQLite |
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
- 🚧 **Version** : 1.0.8 (Beta)

📖 **Statut détaillé:** [docs/changelog/STATUS.md](docs/changelog/STATUS.md)

---

## 🤝 Contribution

Ce projet est en version **beta**. Pour toute question ou suggestion, voir la [documentation](docs/).

---

## 📄 Licence

Projet interne OVH.

---

**Dernière mise à jour:** 2026-01-XX
