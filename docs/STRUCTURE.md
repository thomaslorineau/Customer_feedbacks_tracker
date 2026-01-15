# 📁 Structure du projet

Ce document explique l'organisation des dossiers du projet pour faciliter la navigation.

---

## 🎯 Vue d'ensemble

Le projet est organisé en **4 dossiers principaux** :

1. **`frontend/`** - Interface utilisateur
2. **`backend/`** - API et logique métier
3. **`docs/`** - Documentation complète
4. **`scripts/`** - Scripts d'administration

---

## 📂 Détails par dossier

### 🎨 `frontend/`

Interface utilisateur de l'application (HTML, CSS, JavaScript).

```
frontend/
├── index.html              # Page principale : Scraping & Configuration
├── logs.html               # Page des logs de scraping
├── test_api.html          # Page de test de l'API
├── css/
│   └── shared-theme.css   # Thème partagé (dark/light mode)
├── v2/                     # Dashboard Analytics (version 2)
│   ├── index.html         # Page dashboard principale
│   ├── settings.html      # Page de configuration
│   ├── css/               # Styles du dashboard
│   └── js/                # Modules JavaScript
└── improvements/           # Page d'améliorations
    ├── index.html
    └── js/
```

**Pages principales:**
- `/scraping` → `index.html` - Configuration et déclenchement des scrapers
- `/dashboard` → `v2/index.html` - Visualisation des données
- `/logs` → `logs.html` - Logs de scraping
- `/improvements` → `improvements/index.html` - Opportunités d'amélioration
- `/settings` → `v2/settings.html` - Paramètres

---

### ⚙️ `backend/`

API Backend en Python avec FastAPI.

```
backend/
├── app/                    # Code source de l'application
│   ├── main.py            # Point d'entrée FastAPI (routes, scheduler)
│   ├── config.py          # Configuration (clés API, variables d'env)
│   ├── db.py              # Gestion base de données SQLite
│   │
│   ├── scraper/           # Modules de scraping
│   │   ├── x_scraper.py   # X/Twitter (via Nitter)
│   │   ├── reddit.py      # Reddit (RSS)
│   │   ├── github.py      # GitHub Issues & Discussions
│   │   ├── stackoverflow.py # Stack Overflow (API)
│   │   ├── trustpilot.py  # Trustpilot (HTML + API)
│   │   ├── news.py        # Google News (RSS)
│   │   ├── ovh_forum.py   # OVH Community Forum
│   │   ├── mastodon.py    # Mastodon (API)
│   │   ├── g2_crowd.py    # G2 Crowd (HTML)
│   │   ├── anti_bot_helpers.py # Aide anti-bot
│   │   └── selenium_helper.py  # Automatisation navigateur
│   │
│   ├── analysis/          # Analyse de données
│   │   ├── sentiment.py   # Analyse de sentiment (VADER)
│   │   └── country_detection.py # Détection de pays
│   │
│   └── utils/             # Utilitaires
│       └── helpers.py
│
├── requirements.txt        # Dépendances Python
├── scripts/               # Scripts backend (tests E2E)
│   ├── e2e_test_real_server.py
│   ├── ci_test_endpoints.py
│   └── ci_test_job_persistence.py
│
└── data.db               # Base de données SQLite (générée)
```

**Points d'entrée:**
- `app/main.py` - Application FastAPI principale
- `app/config.py` - Configuration centralisée
- `app/db.py` - Accès base de données

**Endpoints principaux:**
- `POST /scrape/{source}` - Déclencher un scraper
- `GET /api/posts` - Récupérer les posts
- `GET /api/stats` - Statistiques
- `GET /api/logs` - Logs de scraping

---

### 📚 `docs/`

Documentation complète du projet, organisée par catégorie.

```
docs/
├── guides/                # Guides d'utilisation
│   ├── QUICK_START.md     # Guide de démarrage rapide
│   ├── GUIDE_API_KEYS.md  # Configuration des clés API
│   ├── GUIDE_TEST.md      # Guide de test
│   ├── QUICK_START_LLM.md # Configuration LLM
│   ├── GET_API_KEY.md     # Obtenir les clés API
│   └── ANTI_BOT_GUIDE.md  # Guide anti-bot
│
├── architecture/          # Documentation technique
│   ├── ARCHITECTURE.md    # Architecture détaillée
│   ├── SECURITY_OVERVIEW.md # Vue d'ensemble sécurité
│   └── IMPLEMENTATION.md  # Détails d'implémentation
│
├── audits/               # Rapports d'audit
│   ├── SECURITY_AUDIT.md  # Audit de sécurité
│   ├── SECURITY_AUDIT_PHASE2.md
│   ├── AUDIT.md
│   ├── AUDIT_SCRAPERS.md  # Audit des scrapers
│   ├── AUDIT_PRE_DEMO.md  # Audit pré-démo
│   └── FIXES_SCRAPERS.md  # Correctifs scrapers
│
├── changelog/            # Historique des changements
│   ├── STATUS.md         # Statut actuel du projet
│   ├── CHANGES_APPLIED.md # Changements appliqués
│   ├── PHASE1_COMPLETE.md
│   ├── PHASE2_COMPLETE.md
│   ├── CLEANUP_LOG.md    # Log de nettoyage
│   └── ...
│
└── screenshots/          # Captures d'écran
    └── README.md
```

**Navigation recommandée:**
1. Nouveau développeur → `guides/QUICK_START.md`
2. Comprendre l'architecture → `architecture/ARCHITECTURE.md`
3. Configurer les clés API → `guides/GUIDE_API_KEYS.md`
4. Voir les audits → `audits/`

---

### 🔧 `scripts/`

Scripts d'administration organisés par fonction.

```
scripts/
├── start/                # Scripts de démarrage
│   ├── start_server.ps1  # Windows PowerShell
│   ├── start.sh         # Linux/Mac
│   ├── start.bat        # Windows Batch
│   ├── start_backend.py # Python
│   └── run_server.bat   # Alternative Windows
│
├── install/             # Scripts d'installation
│   ├── install.sh       # Installation complète
│   ├── configure_cors.sh # Configuration CORS
│   ├── check_access.sh  # Vérification accès
│   ├── backup.sh        # Sauvegarde
│   ├── update.sh        # Mise à jour
│   ├── status.sh        # Statut
│   └── stop.sh          # Arrêt
│
└── utils/               # Utilitaires
    └── bump-version.ps1 # Incrémenter version
```

**Utilisation:**
- Démarrage: `scripts/start/start_server.ps1` (Windows) ou `scripts/start/start.sh` (Linux/Mac)
- Installation: `scripts/install/install.sh`
- Utilitaires: `scripts/utils/bump-version.ps1`

---

## 🔍 Fichiers à la racine

```
ovh-complaints-tracker/
├── README.md              # Ce fichier (point d'entrée)
├── VERSION                # Version actuelle
├── VERSIONING.md          # Politique de versioning
├── REORGANIZATION_PLAN.md # Plan de réorganisation (historique)
└── .gitignore            # Fichiers ignorés par Git
```

---

## 🎯 Où trouver quoi ?

| Besoin | Chemin |
|--------|--------|
| **Démarrer l'application** | `scripts/start/start_server.ps1` ou `start.sh` |
| **Comprendre l'architecture** | `docs/architecture/ARCHITECTURE.md` |
| **Configurer les clés API** | `docs/guides/GUIDE_API_KEYS.md` |
| **Voir le code frontend** | `frontend/` |
| **Voir le code backend** | `backend/app/` |
| **Tester l'application** | `docs/guides/GUIDE_TEST.md` |
| **Voir les audits** | `docs/audits/` |
| **Historique des changements** | `docs/changelog/` |

---

## 📝 Notes

- Les fichiers de base de données (`*.db`) sont générés automatiquement
- Les fichiers de log (`*.log`) sont dans `backend/logs/`
- Les fichiers de configuration (`.env`) sont dans `backend/` et ne sont **pas** commités
- Les caches Python (`__pycache__/`) sont ignorés par Git

---

**Dernière mise à jour:** 2026-01-XX

