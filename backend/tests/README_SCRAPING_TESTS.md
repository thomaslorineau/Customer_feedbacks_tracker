# 🧪 Tests pour les Scrapers et leur Affichage

Ce document explique comment utiliser les tests pour valider le fonctionnement des scrapers et leur affichage dans l'application.

## 📋 Types de Tests

### 1. Tests Unitaires (`tests/unit/test_scraping_jobs.py`)

Tests unitaires pour les fonctions de gestion des jobs de scraping :
- Création de jobs
- Gestion du statut (pending, running, completed, failed, cancelled)
- Mise à jour de la progression
- Annulation de jobs
- Gestion des erreurs

**Exécution :**
```bash
python -m pytest backend/tests/unit/test_scraping_jobs.py -v
```

### 2. Tests E2E API (`tests/test_e2e_jobs.py`)

Tests end-to-end pour les endpoints API des jobs :
- Création de jobs via API
- Récupération du statut d'un job
- Récupération de tous les jobs
- Filtrage par statut (running, completed, etc.)
- Mise à jour de la progression
- Annulation de jobs
- Gestion des jobs inexistants

**Exécution :**
```bash
# Assurez-vous que le serveur est démarré sur le port 8000
python -m pytest backend/tests/test_e2e_jobs.py -v -s
```

**Avec un serveur sur un autre port :**
```bash
API_BASE_URL=http://127.0.0.1:8001 python -m pytest backend/tests/test_e2e_jobs.py -v -s
```

### 3. Tests E2E UI (`tests/test_e2e_progress_bar.py`)

Tests end-to-end pour l'affichage de la barre de progression dans l'interface utilisateur :
- Apparition de la barre sur la page logs.html
- Mise à jour de la barre de progression
- Disparition de la barre à la fin du job
- Fonctionnement du bouton refresh avec la barre
- Affichage sur la page dashboard.html

**Prérequis :**
- Installer Playwright : `python -m pip install playwright && python -m playwright install chromium`

**Exécution :**
```bash
# Assurez-vous que le serveur est démarré sur le port 8000
python -m pytest backend/tests/test_e2e_progress_bar.py -v -s
```

### 4. Script de Test Complet (`scripts/test_scraping_flow.py`)

Script Python pour tester le flux complet scraping → affichage :
- Création de jobs
- Suivi de la progression
- Vérification de l'affichage dans l'API
- Validation de la complétion

**Exécution :**
```bash
# Assurez-vous que le serveur est démarré sur le port 8000
python backend/scripts/test_scraping_flow.py
```

**Avec un serveur sur un autre port :**
```bash
API_BASE_URL=http://127.0.0.1:8001 python backend/scripts/test_scraping_flow.py
```

## 🚀 Exécution de Tous les Tests

### Tests Unitaires
```bash
python -m pytest backend/tests/unit/ -v
```

### Tests E2E (nécessite un serveur en cours d'exécution)
```bash
# Démarrer le serveur dans un terminal séparé
# Puis dans un autre terminal :
python -m pytest backend/tests/test_e2e_jobs.py backend/tests/test_e2e_progress_bar.py -v -s
```

### Tests avec Marqueurs
```bash
# Tests unitaires uniquement
python -m pytest backend/tests/unit/ -m unit -v

# Tests E2E uniquement
python -m pytest backend/tests/ -m e2e -v
```

## 📊 Interprétation des Résultats

### ✅ Tests Réussis
- Tous les tests passent : le système fonctionne correctement
- Les jobs sont créés et suivis correctement
- La progression est mise à jour
- L'affichage fonctionne dans l'UI

### ❌ Tests Échoués

#### Erreurs de Connexion
- **Problème** : Le serveur n'est pas accessible
- **Solution** : Démarrer le serveur avec `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

#### Jobs qui ne Progressent Pas
- **Problème** : Les jobs restent bloqués en "pending" ou "running"
- **Solution** : Vérifier les logs du serveur pour identifier les erreurs de scraping

#### Barre de Progression qui Disparaît
- **Problème** : La barre disparaît avant la fin du job
- **Solution** : Vérifier la logique de polling dans `frontend/logs.html` et `frontend/dashboard/js/dashboard.js`

#### Erreurs de Base de Données
- **Problème** : Erreurs lors de la création ou mise à jour des jobs
- **Solution** : Vérifier l'intégrité de la base de données DuckDB

## 🔍 Debugging

### Activer les Logs Détaillés
```bash
python -m pytest backend/tests/test_e2e_jobs.py -v -s --log-cli-level=DEBUG
```

### Exécuter un Test Spécifique
```bash
python -m pytest backend/tests/test_e2e_jobs.py::TestJobAPI::test_create_single_source_job -v -s
```

### Capturer les Screenshots (tests UI)
Les tests Playwright peuvent capturer des screenshots en cas d'échec :
```bash
python -m pytest backend/tests/test_e2e_progress_bar.py -v -s --headed
```

## 📝 Ajout de Nouveaux Tests

### Test Unitaire
Ajoutez votre test dans `backend/tests/unit/test_scraping_jobs.py` :
```python
def test_my_new_feature(self):
    """Test pour ma nouvelle fonctionnalité."""
    # Votre code de test ici
    assert condition
```

### Test E2E API
Ajoutez votre test dans `backend/tests/test_e2e_jobs.py` :
```python
@pytest.mark.asyncio
async def test_my_new_endpoint(self, client):
    """Test pour mon nouvel endpoint."""
    response = await client.get("/my/endpoint")
    assert response.status_code == 200
```

### Test E2E UI
Ajoutez votre test dans `backend/tests/test_e2e_progress_bar.py` :
```python
@pytest.mark.asyncio
async def test_my_new_ui_feature(self, page: Page):
    """Test pour ma nouvelle fonctionnalité UI."""
    await page.goto(f"{FRONTEND_BASE}/my-page")
    # Votre code de test ici
```

## 🎯 Bonnes Pratiques

1. **Toujours nettoyer les jobs** : Utilisez `JOBS.clear()` dans `setup_method()` pour éviter les interférences entre tests
2. **Utiliser des timeouts appropriés** : Les scrapers peuvent prendre du temps, utilisez des timeouts suffisants
3. **Vérifier les statuts** : Ne supposez pas qu'un job est terminé immédiatement
4. **Gérer les erreurs réseau** : Les tests E2E peuvent échouer si le serveur n'est pas accessible
5. **Isoler les tests** : Chaque test devrait être indépendant et pouvoir s'exécuter seul

## 📚 Ressources

- [Documentation pytest](https://docs.pytest.org/)
- [Documentation pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Documentation Playwright](https://playwright.dev/python/)
- [Documentation httpx](https://www.python-httpx.org/)

