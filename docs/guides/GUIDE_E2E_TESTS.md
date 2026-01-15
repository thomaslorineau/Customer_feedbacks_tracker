# 🧪 Guide des Tests E2E

Ce guide explique comment exécuter les tests E2E (End-to-End) pour valider que l'application fonctionne correctement.

---

## 🎯 Objectif

Les tests E2E vérifient que **toutes les fonctionnalités principales** de l'application fonctionnent correctement :
- ✅ Démarrage du serveur
- ✅ Endpoints API
- ✅ Scrapers
- ✅ Pages frontend
- ✅ Logs
- ✅ Configuration
- ✅ Sécurité

---

## 🚀 Exécution rapide

```bash
# Depuis la racine du projet
python backend/scripts/e2e_full_test.py
```

**Résultat attendu :**
```
✅ Tous les tests sont passés !
Score: 100.0%
```

---

## 📋 Tests inclus

### 1. Health Check
Vérifie que le serveur répond correctement.

### 2. API Version
Teste l'endpoint `/api/version` pour obtenir la version de l'application.

### 3. API Config
Teste l'endpoint `/api/config` pour vérifier la configuration.

### 4. API Posts
Teste l'endpoint `/posts` pour récupérer les posts.

### 5. API Stats
Teste l'endpoint `/api/posts-by-source` pour obtenir les statistiques.

### 6. API Posts by Source
Teste l'endpoint `/api/posts-by-source` pour la répartition par source.

### 7. Scraper Reddit
Teste le scraper Reddit (peut prendre quelques secondes).

### 8. Scraper Stack Overflow
Teste le scraper Stack Overflow (peut prendre quelques secondes).

### 9. Frontend Pages
Vérifie que toutes les pages frontend se chargent :
- `/scraping`
- `/dashboard`
- `/logs`
- `/settings`

### 10. API Logs
Teste l'endpoint `/api/logs` pour récupérer les logs.

### 11. Settings Queries
Teste la sauvegarde et récupération des keywords.

### 12. Security Headers
Vérifie que les headers de sécurité sont présents :
- `X-Content-Type-Options`
- `X-Frame-Options`
- `X-XSS-Protection`

---

## 📊 Interprétation des résultats

### Score 100% ✅
Tous les tests sont passés. L'application fonctionne correctement.

### Score 80-99% ⚠️
La plupart des tests sont passés. Vérifier les tests échoués.

### Score < 80% ❌
Plusieurs tests ont échoué. Vérifier les erreurs et corriger.

---

## 🔧 Dépannage

### Le serveur ne démarre pas
- Vérifier que le port 8000 est libre
- Vérifier que Python et les dépendances sont installés
- Vérifier les logs d'erreur

### Tests de scrapers échouent
- C'est normal si les scrapers retournent 0 posts (pas de données disponibles)
- Vérifier la connexion Internet
- Certains scrapers peuvent être bloqués (rate limiting)

### Tests frontend échouent
- Vérifier que les fichiers HTML existent dans `frontend/`
- Vérifier les chemins dans `backend/app/main.py`

---

## 📝 Ajouter de nouveaux tests

Pour ajouter un nouveau test, ajoutez une fonction dans `e2e_full_test.py` :

```python
def test_mon_nouveau_test(result: TestResult):
    """Description du test."""
    result.name = "Mon Nouveau Test"
    success, data = test_endpoint('GET', '/mon/endpoint')
    if success:
        print_success("Test réussi")
    else:
        raise AssertionError(f"Erreur: {data}")
```

Puis ajoutez-la à la liste `tests` dans `run_all_tests()`.

---

## 🎯 Utilisation en CI/CD

Le script retourne un code de sortie :
- `0` : Tous les tests sont passés
- `1` : Au moins un test a échoué
- `130` : Tests interrompus (Ctrl+C)

**Exemple d'utilisation en CI :**
```bash
python backend/scripts/e2e_full_test.py
if [ $? -eq 0 ]; then
    echo "✅ Tests E2E réussis"
else
    echo "❌ Tests E2E échoués"
    exit 1
fi
```

---

## 📚 Voir aussi

- [Guide de test général](GUIDE_TEST.md)
- [Architecture de l'application](../architecture/ARCHITECTURE.md)

---

**Dernière mise à jour:** 2026-01-XX


