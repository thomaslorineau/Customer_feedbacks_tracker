# Audit des Fonctions de Scraping - OVH Complaints Tracker

**Date**: 2026-01-13  
**Version**: 1.0

## Résumé Exécutif

Cet audit identifie les problèmes et limitations de chaque scraper dans le système. Sur **11 scrapers** analysés, plusieurs présentent des problèmes critiques ou des limitations qui peuvent empêcher leur fonctionnement correct.

---

## 1. Scraper X/Twitter (`x_scraper.py`)

### ✅ Points Positifs
- Stratégie de fallback avec plusieurs instances Nitter
- Gestion d'erreurs robuste
- Détection de langue

### ⚠️ Problèmes Identifiés

1. **Dépendance à Nitter (CRITIQUE)**
   - Les instances Nitter sont souvent instables ou bloquées
   - Pas de mécanisme de vérification de disponibilité
   - Si toutes les instances échouent, retourne une liste vide sans erreur

2. **API Twitter non fonctionnelle**
   - Ligne 135-149 : L'API Twitter est commentée car elle nécessite un Bearer token
   - Aucune alternative réelle si Nitter échoue

3. **Parsing HTML fragile**
   - Dépend de la structure HTML de Nitter qui peut changer
   - Sélecteurs CSS potentiellement obsolètes (lignes 87-102)

### 🔧 Recommandations
- Ajouter une vérification de santé des instances Nitter avant utilisation
- Implémenter un système de rotation d'instances
- Ajouter un mécanisme de notification si toutes les méthodes échouent
- Documenter que ce scraper peut retourner 0 résultats sans erreur

**Statut**: ⚠️ **FONCTIONNEL MAIS INSTABLE**

---

## 2. Scraper Reddit (`reddit.py`)

### ✅ Points Positifs
- Utilise les flux RSS officiels de Reddit (méthode légale)
- Retry logic avec exponential backoff
- Gestion des erreurs réseau robuste
- User-Agent approprié

### ⚠️ Problèmes Identifiés

1. **Limitation des flux RSS**
   - Reddit limite les résultats RSS (max 100 items)
   - Les flux RSS peuvent être incomplets ou filtrés

2. **Rate Limiting**
   - Reddit peut bloquer les requêtes répétées
   - Pas de gestion explicite du rate limiting (429)

3. **Parsing des dates**
   - Dépend de `published_parsed` qui peut être absent
   - Fallback sur `datetime.now()` peut créer des dates incorrectes

### 🔧 Recommandations
- Ajouter une gestion explicite du code 429 (Too Many Requests)
- Implémenter un cache pour éviter les requêtes répétées
- Améliorer le parsing des dates avec plusieurs formats

**Statut**: ✅ **FONCTIONNEL** (avec limitations connues)

---

## 3. Scraper GitHub (`github.py`)

### ✅ Points Positifs
- Utilise l'API GitHub officielle (gratuite, pas d'auth requise)
- Recherche à la fois Issues et Discussions
- Timeout configuré

### ⚠️ Problèmes Identifiés

1. **Rate Limiting GitHub (CRITIQUE)**
   - GitHub limite à 60 requêtes/heure pour les requêtes non authentifiées
   - Aucune gestion du rate limiting (code 403)
   - Pas de retry avec backoff pour les erreurs de rate limit

2. **Limitation de résultats**
   - L'API GitHub limite à 100 résultats par requête
   - Pas de pagination pour récupérer plus de résultats

3. **Erreurs silencieuses**
   - Si l'API échoue, retourne une liste vide sans log d'erreur détaillé
   - Les exceptions sont catchées mais pas toujours loggées

### 🔧 Recommandations
- Ajouter une gestion du rate limiting avec retry
- Implémenter la pagination pour plus de résultats
- Ajouter des logs d'erreur plus détaillés
- Considérer l'utilisation d'un token GitHub (optionnel) pour augmenter les limites

**Statut**: ⚠️ **FONCTIONNEL MAIS LIMITÉ PAR RATE LIMITING**

---

## 4. Scraper Stack Overflow (`stackoverflow.py`)

### ✅ Points Positifs
- Utilise l'API Stack Exchange officielle (gratuite, bien documentée)
- Retry logic avec exponential backoff
- Gestion des timeouts

### ⚠️ Problèmes Identifiés

1. **Rate Limiting Stack Exchange**
   - Stack Exchange limite à 300 requêtes/jour par IP
   - Pas de gestion explicite du quota
   - Peut échouer silencieusement si quota dépassé

2. **Filtre de recherche limité**
   - Utilise `intitle` qui ne recherche que dans les titres
   - Peut manquer des questions pertinentes dans le corps

3. **Parsing des dates**
   - Conversion timestamp peut échouer si `creation_date` est absent
   - Fallback sur `datetime.now()` peut être incorrect

### 🔧 Recommandations
- Ajouter une vérification du quota API avant requête
- Améliorer la requête de recherche pour inclure le corps
- Améliorer le parsing des dates avec validation

**Statut**: ✅ **FONCTIONNEL** (avec limitations de quota)

---

## 5. Scraper Trustpilot (`trustpilot.py`)

### ✅ Points Positifs
- Stratégie multi-niveaux (HTML → API → Sample)
- Parsing HTML robuste avec BeautifulSoup
- Mapping rating → sentiment automatique

### ⚠️ Problèmes Identifiés

1. **Fallback vers données sample (CRITIQUE)**
   - Ligne 56 : Si HTML et API échouent, retourne des données sample
   - **VIOLATION** : Le système ne devrait jamais retourner de données sample
   - Les données sample polluent la base de données

2. **Parsing HTML fragile**
   - Dépend de sélecteurs CSS spécifiques (lignes 78-110)
   - Structure HTML de Trustpilot peut changer
   - Peut échouer silencieusement si structure change

3. **API nécessite une clé**
   - L'API Trustpilot nécessite une clé API (non fournie)
   - Pas de fallback gracieux si clé manquante

4. **URL hardcodée**
   - Ligne 15 : URL hardcodée vers `fr.trustpilot.com`
   - Ne supporte pas d'autres langues/régions

### 🔧 Recommandations
- **URGENT** : Supprimer le fallback vers données sample (ligne 56)
- Améliorer la robustesse du parsing HTML
- Ajouter une documentation pour obtenir une clé API Trustpilot
- Rendre l'URL configurable

**Statut**: ❌ **PROBLÈME CRITIQUE** (retourne des données sample)

---

## 6. Scraper Google News (`news.py`)

### ✅ Points Positifs
- Utilise les flux RSS de Google News (méthode légale)
- Gestion de plusieurs keywords
- Retry logic avec exponential backoff
- Évite les doublons avec `seen_urls`

### ⚠️ Problèmes Identifiés

1. **Limitation des flux RSS Google**
   - Google News RSS peut être limité ou filtré
   - Pas de garantie de résultats complets

2. **Parsing des dates**
   - Dépend de `published_parsed` qui peut être absent
   - Fallback sur `datetime.now()` peut être incorrect

3. **Extraction d'auteur fragile**
   - Lignes 98-105 : Logique complexe pour extraire l'auteur
   - Peut échouer si structure RSS change

### 🔧 Recommandations
- Améliorer le parsing des dates avec validation
- Simplifier l'extraction d'auteur
- Ajouter des logs pour debug

**Statut**: ✅ **FONCTIONNEL** (avec limitations connues)

---

## 7. Scraper OVH Forum (`ovh_forum.py`)

### ✅ Points Positifs
- Utilise des techniques anti-bot (stealth session, headers réalistes)
- Timeout global pour éviter les boucles infinies
- Fallback vers browser automation (Selenium/Playwright)

### ⚠️ Problèmes Identifiés

1. **Scraping HTML fragile (CRITIQUE)**
   - Dépend fortement de la structure HTML du forum
   - Sélecteurs CSS peuvent être obsolètes (lignes 110-121)
   - Peut retourner 0 résultats si structure change

2. **Performance lente**
   - Fait des requêtes individuelles pour chaque post (ligne 173)
   - Peut prendre très longtemps avec beaucoup de posts
   - Timeout de 60s peut être insuffisant

3. **Browser automation optionnel**
   - Nécessite Playwright ou Selenium installés
   - Peut échouer si non disponible

4. **Filtrage par query limité**
   - Ligne 157 : Filtre simple par substring dans titre/URL
   - Peut manquer des posts pertinents

### 🔧 Recommandations
- Améliorer la robustesse des sélecteurs CSS
- Optimiser pour réduire le nombre de requêtes
- Documenter les dépendances optionnelles (Playwright/Selenium)
- Améliorer le filtrage par query

**Statut**: ⚠️ **INSTABLE** (dépend de la structure HTML)

---

## 8. Scraper Mastodon (`mastodon.py`)

### ✅ Points Positifs
- Essaie plusieurs instances Mastodon
- Utilise l'API publique Mastodon
- Évite les doublons avec `seen_urls`

### ⚠️ Problèmes Identifiés

1. **Recherche par hashtag limitée**
   - Ligne 58 : Convertit la query en hashtag (supprime espaces)
   - Peut ne pas trouver de résultats si query n'est pas un hashtag populaire

2. **API de recherche peut être limitée**
   - Certaines instances Mastodon limitent l'API de recherche
   - Pas de gestion explicite des erreurs 429

3. **Parsing HTML dans contenu**
   - Ligne 74 : Supprime les balises HTML mais peut laisser du contenu mal formaté

### 🔧 Recommandations
- Améliorer la stratégie de recherche (hashtag + texte)
- Ajouter une gestion du rate limiting
- Améliorer le nettoyage HTML

**Statut**: ✅ **FONCTIONNEL** (avec limitations)

---

## 9. Scraper G2 Crowd (`g2_crowd.py`)

### ✅ Points Positifs
- Utilise des techniques anti-bot
- Timeout global pour éviter les boucles infinies
- Fallback vers browser automation

### ⚠️ Problèmes Identifiés

1. **Scraping HTML très fragile (CRITIQUE)**
   - Dépend fortement de la structure HTML de G2
   - Sélecteurs CSS multiples et complexes (lignes 90-99)
   - Peut facilement échouer si structure change

2. **Blocage fréquent (403)**
   - G2 bloque souvent les scrapers (ligne 66)
   - Nécessite browser automation qui peut ne pas être disponible

3. **Performance lente**
   - Limite à 15 reviews max (ligne 104)
   - Peut prendre du temps même avec peu de résultats

4. **URL hardcodée**
   - Ligne 42 : URL hardcodée vers `/products/ovhcloud/reviews`
   - Ne supporte pas d'autres produits

### 🔧 Recommandations
- **URGENT** : Améliorer la robustesse du parsing HTML
- Documenter les dépendances optionnelles
- Rendre l'URL configurable
- Considérer l'utilisation de l'API G2 si disponible

**Statut**: ❌ **TRÈS INSTABLE** (bloqué fréquemment)

---

## 10. Endpoint `/scrape/github` dans `main.py`

### ⚠️ Problème Critique Identifié

**Ligne 758** : Le scraper GitHub **ne vérifie pas** si `insert_post` a réussi !

```python
db.insert_post({...})
added += 1  # Toujours incrémenté, même si insert a échoué !
```

Cela peut créer des compteurs incorrects et masquer des erreurs de base de données.

### 🔧 Recommandation
- **URGENT** : Vérifier le retour de `insert_post` avant d'incrémenter `added`

**Statut**: ❌ **BUG CRITIQUE**

---

## 11. Endpoint `/scrape/stackoverflow` dans `main.py`

### ⚠️ Problème Identifié

**Ligne 742** : Même problème - ne vérifie pas le retour de `insert_post` correctement, mais au moins utilise `if db.insert_post(...)`.

**Statut**: ✅ **CORRECT** (mais similaire au pattern de GitHub)

---

## 12. Endpoint `/scrape/news` dans `main.py`

### ⚠️ Problème Identifié

**Ligne 903** : Le paramètre `query` est **obligatoire** mais n'a pas de valeur par défaut.

Si appelé sans `query`, FastAPI retournera une erreur 422.

**Statut**: ⚠️ **INCOHÉRENT** (devrait avoir une valeur par défaut comme les autres)

---

## Problèmes Généraux

### 1. Gestion des Erreurs Incohérente
- Certains scrapers retournent `[]` en cas d'erreur
- D'autres lèvent des exceptions
- Pas de standardisation

### 2. Logging Incohérent
- Certains utilisent `logger.info()`, d'autres `print()`
- Niveaux de log différents
- Pas de format standardisé

### 3. Données Sample
- Trustpilot retourne des données sample (VIOLATION)
- Doit être supprimé immédiatement

### 4. Rate Limiting
- Peu de scrapers gèrent explicitement le rate limiting
- Peut causer des blocages IP

### 5. Timeouts
- Timeouts différents selon les scrapers
- Pas de configuration centralisée

---

## Recommandations Globales

### Priorité Haute (URGENT)

1. **Supprimer les données sample de Trustpilot** (ligne 56 de `trustpilot.py`)
2. **Corriger le bug GitHub** (ligne 758 de `main.py`)
3. **Ajouter une valeur par défaut pour `query` dans `/scrape/news`**

### Priorité Moyenne

1. Standardiser la gestion des erreurs (tous retournent `[]` ou tous lèvent des exceptions)
2. Standardiser le logging (utiliser `logger` partout)
3. Ajouter une gestion centralisée du rate limiting
4. Améliorer la robustesse des scrapers HTML (OVH Forum, G2 Crowd)

### Priorité Basse

1. Ajouter des tests unitaires pour chaque scraper
2. Documenter les limitations de chaque scraper
3. Créer un système de monitoring de santé des scrapers

---

## Tests Recommandés

Pour chaque scraper, tester :
1. ✅ Scraping avec query valide
2. ✅ Scraping avec query vide/invalide
3. ✅ Gestion des erreurs réseau
4. ✅ Gestion du rate limiting
5. ✅ Parsing des données retournées
6. ✅ Insertion en base de données

---

## Conclusion

Sur **11 scrapers** analysés :
- ✅ **4 fonctionnels** : Reddit, Stack Overflow, Google News, Mastodon
- ⚠️ **5 instables/limites** : X/Twitter, GitHub, OVH Forum, News (query), Trustpilot
- ❌ **2 critiques** : Trustpilot (données sample), GitHub (bug insertion)

**Taux de fonctionnalité estimé** : ~60% des scrapers fonctionnent correctement dans des conditions normales.

---

## Corrections Appliquées

### ✅ Problèmes Critiques Corrigés

1. **Trustpilot - Suppression des données sample** ✅
   - **Fichier** : `backend/app/scraper/trustpilot.py`
   - **Ligne 56** : Supprimé le fallback vers `_get_sample_trustpilot_reviews()`
   - **Résultat** : Retourne maintenant une liste vide si tous les scrapers échouent

2. **GitHub - Correction du bug d'insertion** ✅
   - **Fichier** : `backend/app/main.py`
   - **Ligne 758** : Ajouté une vérification du retour de `insert_post()` avant d'incrémenter `added`
   - **Résultat** : Le compteur `added` reflète maintenant correctement le nombre de posts réellement insérés

3. **News - Ajout de valeur par défaut pour query** ✅
   - **Fichier** : `backend/app/main.py`
   - **Ligne 903** : Ajouté `query: str = "OVH"` comme valeur par défaut
   - **Résultat** : L'endpoint peut maintenant être appelé sans paramètre `query`

### 📋 Problèmes Restants (Priorité Moyenne/Basse)

- Améliorer la robustesse des scrapers HTML (OVH Forum, G2 Crowd)
- Standardiser la gestion des erreurs
- Ajouter une gestion centralisée du rate limiting
- Améliorer le logging

