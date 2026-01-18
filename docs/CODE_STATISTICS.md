# 📊 Statistiques de Code - OVH Customer Feedbacks Tracker

**Date:** 2026-01-XX  
**Version:** 1.0.9

---

## 📈 Vue d'ensemble

### Total: **~18 691 lignes de code**

| Composant | Langage | Lignes | Fichiers |
|-----------|---------|--------|----------|
| **Backend** | Python | 5 725 | 21 |
| **Frontend** | JavaScript | 3 946 | 13 |
| **Frontend** | HTML | 7 516 | 6 |
| **Frontend** | CSS | 1 504 | 3 |
| **TOTAL** | | **18 691** | **43** |

---

## 🔍 Détail par composant

### Backend (Python) - 5 725 lignes

#### Core (2 954 lignes)
- `main.py` - 2 167 lignes (FastAPI app, endpoints, scheduler)
- `db.py` - 498 lignes (Gestion base de données)
- `config.py` - 289 lignes (Configuration)

#### Scrapers (2 232 lignes)
- `x_scraper.py` - 192 lignes (X/Twitter scraper)
- `reddit.py` - 218 lignes (Reddit RSS scraper)
- `github.py` - 169 lignes (GitHub Issues scraper)
- `stackoverflow.py` - 93 lignes (Stack Overflow API scraper)
- `trustpilot.py` - 266 lignes (Trustpilot scraper)
- `news.py` - 169 lignes (Google News RSS scraper)
- `ovh_forum.py` - 275 lignes (OVH Forum scraper)
- `mastodon.py` - 184 lignes (Mastodon API scraper)
- `g2_crowd.py` - 297 lignes (G2 Crowd scraper)
- `anti_bot_helpers.py` - 182 lignes (Helpers anti-bot)
- `selenium_helper.py` - 187 lignes (Automatisation navigateur)

#### Analysis (265 lignes)
- `sentiment.py` - 14 lignes (Analyse de sentiment VADER)
- `country_detection.py` - 251 lignes (Détection de pays)

#### Utils
- `helpers.py` - Utilitaires

---

### Frontend - 12 966 lignes

#### JavaScript (3 946 lignes - 13 fichiers)
- `app.js` - Initialisation application
- `api.js` - Communication API
- `state.js` - Gestion d'état
- `dashboard.js` - Logique dashboard
- `charts.js` - Visualisations Chart.js
- `sentiment-chart.js` - Graphique sentiment
- `source-chart.js` - Graphique par source
- `product-detection.js` - Détection produits
- `whats-happening.js` - Analyse "What's Happening"
- `world-map.js` - Carte mondiale
- `settings.js` - Gestion paramètres
- `version-switch.js` - Changement de version

#### HTML (7 516 lignes - 6 fichiers)
- `index.html` - Page principale (Scraping)
- `logs.html` - Page des logs
- `v2/index.html` - Dashboard Analytics
- `v2/settings.html` - Page de configuration
- `improvements/index.html` - Page d'améliorations
- `test_api.html` - Page de test API

#### CSS (1 504 lignes - 3 fichiers)
- `shared-theme.css` - Thème partagé (dark/light)
- `v2/css/styles.css` - Styles dashboard
- `v2/css/navigation.css` - Styles navigation

---

## 📦 Répartition par fonctionnalité

| Fonctionnalité | Lignes |
|----------------|--------|
| **API Backend** | ~2 500 |
| **Scrapers** | 2 232 |
| **Base de données** | 498 |
| **Analyse (sentiment, pays)** | 265 |
| **Dashboard Frontend** | ~6 000 |
| **Pages Frontend** | 7 516 |
| **Configuration & Utils** | ~400 |

---

## 🎯 Complexité

### Fichiers les plus volumineux
1. `backend/app/main.py` - 2 167 lignes (API principale)
2. `frontend/v2/index.html` - ~4 000 lignes (Dashboard)
3. `frontend/index.html` - ~5 000 lignes (Page scraping)

### Modules les plus complexes
- **Scrapers** : 9 scrapers différents avec logique de fallback
- **Dashboard** : Visualisations interactives avec Chart.js
- **API** : 20+ endpoints avec validation et gestion d'erreurs

---

## 📝 Notes

- Les lignes de code incluent les commentaires et la documentation
- Les fichiers de configuration (`.env`, `.gitignore`) ne sont pas comptés
- Les fichiers générés (`__pycache__/`, `*.pyc`) sont exclus
- La documentation Markdown n'est pas incluse dans le comptage

---

**Dernière mise à jour:** 2026-01-XX

