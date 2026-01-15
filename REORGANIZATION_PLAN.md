# 📁 PLAN DE RÉORGANISATION - STRUCTURE DU PROJET

## 🎯 Objectif
Réorganiser les dossiers pour rendre l'architecture de l'application **immédiatement compréhensible** pour un nouveau développeur.

---

## 📊 Structure actuelle vs Structure proposée

### ❌ Problèmes actuels
- **28 fichiers Markdown** à la racine (confus)
- Scripts éparpillés (`.sh`, `.bat`, `.ps1`, `.py`)
- Documentation mélangée avec le code
- Pas de séparation claire entre docs, scripts, config

### ✅ Structure proposée

```
ovh-complaints-tracker/
│
├── 📖 README.md                    # Point d'entrée principal
├── 📋 VERSION                      # Version de l'application
│
├── 🎨 frontend/                    # Application frontend (HTML/CSS/JS)
│   ├── index.html                  # Page principale (Scraping)
│   ├── logs.html                   # Page des logs
│   ├── css/                        # Styles partagés
│   ├── v2/                         # Dashboard Analytics (v2)
│   └── improvements/               # Page d'améliorations
│
├── ⚙️ backend/                     # Application backend (Python/FastAPI)
│   ├── app/                        # Code source de l'application
│   │   ├── main.py                 # Point d'entrée FastAPI
│   │   ├── config.py               # Configuration
│   │   ├── db.py                   # Base de données
│   │   ├── scraper/                # Modules de scraping
│   │   ├── analysis/               # Analyse de sentiment
│   │   └── utils/                  # Utilitaires
│   ├── requirements.txt            # Dépendances Python
│   └── scripts/                    # Scripts backend (tests E2E)
│
├── 📚 docs/                        # Documentation complète
│   ├── guides/                     # Guides d'utilisation
│   │   ├── QUICK_START.md
│   │   ├── GUIDE_API_KEYS.md
│   │   └── GUIDE_TEST.md
│   ├── architecture/               # Documentation technique
│   │   ├── ARCHITECTURE.md
│   │   └── SECURITY_OVERVIEW.md
│   ├── audits/                     # Rapports d'audit
│   │   ├── SECURITY_AUDIT.md
│   │   └── AUDIT_SCRAPERS.md
│   └── changelog/                  # Historique des changements
│       ├── CHANGES_APPLIED.md
│       └── STATUS.md
│
├── 🔧 scripts/                     # Scripts d'administration
│   ├── start/                      # Scripts de démarrage
│   │   ├── start_server.ps1
│   │   ├── start.sh
│   │   └── start.bat
│   ├── install/                    # Scripts d'installation
│   │   └── install.sh
│   └── utils/                      # Utilitaires
│       └── bump-version.ps1
│
└── 📝 .gitignore                   # Fichiers ignorés par Git
```

---

## 🔄 Actions à effectuer

### 1. Créer la structure de dossiers
- [ ] Créer `docs/guides/`
- [ ] Créer `docs/architecture/`
- [ ] Créer `docs/audits/`
- [ ] Créer `docs/changelog/`
- [ ] Créer `scripts/start/`
- [ ] Créer `scripts/install/`
- [ ] Créer `scripts/utils/`

### 2. Déplacer la documentation
- [ ] Guides → `docs/guides/`
- [ ] Architecture → `docs/architecture/`
- [ ] Audits → `docs/audits/`
- [ ] Changelog → `docs/changelog/`

### 3. Déplacer les scripts
- [ ] Scripts de démarrage → `scripts/start/`
- [ ] Scripts d'installation → `scripts/install/`
- [ ] Utilitaires → `scripts/utils/`

### 4. Mettre à jour les références
- [ ] Mettre à jour les liens dans README.md
- [ ] Mettre à jour les chemins dans les scripts
- [ ] Mettre à jour ARCHITECTURE.md

### 5. Créer un README principal clair
- [ ] Structure du projet
- [ ] Architecture en 30 secondes
- [ ] Démarrage rapide
- [ ] Liens vers la documentation

---

## 📝 Fichiers à déplacer

### Documentation → `docs/`

**Guides (`docs/guides/`):**
- QUICK_START.md
- QUICK_START_LLM.md
- GUIDE_API_KEYS.md
- GUIDE_TEST.md
- backend/GET_API_KEY.md
- backend/ANTI_BOT_GUIDE.md

**Architecture (`docs/architecture/`):**
- ARCHITECTURE.md
- SECURITY_OVERVIEW.md
- IMPLEMENTATION.md

**Audits (`docs/audits/`):**
- SECURITY_AUDIT.md
- SECURITY_AUDIT_PHASE2.md
- AUDIT.md
- AUDIT_SCRAPERS.md
- AUDIT_PRE_DEMO.md
- FIXES_SCRAPERS.md

**Changelog (`docs/changelog/`):**
- CHANGES_APPLIED.md
- STATUS.md
- PHASE1_COMPLETE.md
- PHASE2_COMPLETE.md
- FINAL_SUMMARY.md
- EXECUTIVE_SUMMARY.md
- IMPROVEMENT_PLAN.md
- URGENT_API_KEY.md
- CLEANUP_LOG.md
- CLEANUP_REPORT_FINAL.md

### Scripts → `scripts/`

**Démarrage (`scripts/start/`):**
- start_server.ps1
- start.sh
- start.bat
- start_backend.py
- run_server.bat

**Installation (`scripts/install/`):**
- install.sh
- configure_cors.sh
- check_access.sh
- backup.sh
- update.sh
- status.sh
- stop.sh

**Utilitaires (`scripts/utils/`):**
- scripts/bump-version.ps1

---

## ✅ Avantages de cette structure

1. **Clarté immédiate** : On comprend l'architecture en regardant les dossiers
2. **Séparation des responsabilités** : Code, docs, scripts séparés
3. **Facilité de navigation** : Tout est à sa place logique
4. **Maintenabilité** : Plus facile d'ajouter/modifier des fichiers
5. **Professionnalisme** : Structure standard d'un projet Python/Web

---

## 🚀 Après réorganisation

Le README principal pointera vers :
- `docs/guides/QUICK_START.md` pour démarrer
- `docs/architecture/ARCHITECTURE.md` pour comprendre l'architecture
- `docs/guides/GUIDE_API_KEYS.md` pour configurer les clés API

