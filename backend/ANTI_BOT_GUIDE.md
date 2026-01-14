# Guide: Contourner les Protections Anti-Scraping

Ce guide explique les techniques légitimes pour améliorer la fiabilité des scrapers face aux protections anti-bot.

## ⚠️ Important : Éthique et Légalité

- **Respectez les ToS** : Vérifiez toujours les conditions d'utilisation
- **Respectez robots.txt** : Consultez `/robots.txt` avant de scraper
- **Rate Limiting** : Ne surchargez pas les serveurs
- **Données publiques uniquement** : Ne scrapez que du contenu public
- **Utilisez les APIs officielles** quand disponibles

## 🛡️ Techniques Implémentées

### 1. Headers Réalistes

Les scrapers utilisent maintenant des headers de navigateur réalistes :

```python
from app.scraper.anti_bot_helpers import get_realistic_headers

headers = get_realistic_headers(referer="https://example.com")
```

**Inclut :**
- User-Agent rotatif (pool de User-Agents réalistes)
- Headers complets (Accept, Accept-Language, Accept-Encoding, etc.)
- Sec-Fetch-* headers (comportement navigateur moderne)
- Referer approprié

### 2. Délais Humains

Simulation de comportement humain avec délais aléatoires :

```python
from app.scraper.anti_bot_helpers import human_like_delay

human_like_delay(min_seconds=1.0, max_seconds=3.0)
```

**Avantages :**
- Distribution normale (plus réaliste)
- Évite les patterns détectables
- Respecte les serveurs

### 3. Sessions Stealth

Création de sessions avec configuration optimale :

```python
from app.scraper.anti_bot_helpers import create_stealth_session

session = create_stealth_session()
```

**Caractéristiques :**
- Retry strategy intelligente
- Headers réalistes par défaut
- Gestion des connexions optimisée

### 4. Simulation de Comportement Humain

Visite de la page principale avant la requête cible :

```python
from app.scraper.anti_bot_helpers import simulate_human_behavior

simulate_human_behavior(session, target_url)
```

**Comportement :**
- Visite la page d'accueil d'abord
- Ajoute des délais naturels
- Définit le Referer correctement

## 🚀 Techniques Avancées

### 5. Selenium/Playwright (Pour sites JavaScript)

Pour les sites avec protection Cloudflare ou JavaScript lourd :

```python
from app.scraper.selenium_helper import scrape_with_selenium, scrape_with_playwright

# Avec Selenium
html = scrape_with_selenium(url, wait_selector=".content", timeout=10)

# Avec Playwright (recommandé)
html = scrape_with_playwright(url, wait_selector=".content", timeout=10000)
```

**Installation :**
```bash
# Selenium
pip install selenium
# Télécharger ChromeDriver et l'ajouter au PATH

# Playwright (recommandé)
pip install playwright
playwright install chromium
```

**Avantages :**
- Exécute le JavaScript
- Contourne Cloudflare
- Comportement de navigateur réel

**Inconvénients :**
- Plus lent
- Consomme plus de ressources
- Nécessite un navigateur

### 6. Rotation de Proxies

Utilisation de proxies pour éviter les blocages IP :

```python
from app.scraper.anti_bot_helpers import rotate_proxy

proxies = rotate_proxy(proxy_list=[
    'http://proxy1:8080',
    'http://proxy2:8080'
])

session.get(url, proxies=proxies)
```

**Types de proxies :**
- **Residential** : IPs résidentielles (meilleur, plus cher)
- **Datacenter** : IPs de datacenter (moins cher, plus détectable)
- **Rotating** : Rotation automatique

**Services recommandés :**
- Bright Data (ex-Luminati)
- Smartproxy
- Oxylabs

### 7. Cookies et Sessions

Maintenir des sessions persistantes :

```python
from app.scraper.anti_bot_helpers import add_cookies_from_browser

# Extraire les cookies depuis un navigateur réel
cookies = {
    'session_id': 'abc123',
    'csrf_token': 'xyz789'
}
add_cookies_from_browser(session, cookies)
```

## 📋 Stratégies par Type de Protection

### Cloudflare

**Solution :** Playwright avec options stealth
```python
html = scrape_with_playwright(url)
```

### Rate Limiting (429)

**Solution :** Exponential backoff + rotation User-Agent
```python
from app.scraper.anti_bot_helpers import exponential_backoff_delay

delay = exponential_backoff_delay(attempt=2)
time.sleep(delay)
```

### JavaScript Required

**Solution :** Selenium ou Playwright
```python
html = scrape_with_playwright(url, wait_selector=".main-content")
```

### CAPTCHA

**Solutions :**
1. **2Captcha / AntiCaptcha** : Services de résolution
2. **Playwright avec extensions** : Résolution automatique
3. **Éviter** : Utiliser des APIs ou sources alternatives

### IP Blocking

**Solutions :**
1. **Proxies rotatifs** : Rotation d'IPs
2. **VPN** : Changer d'IP régulièrement
3. **Rate limiting** : Réduire la fréquence

## 🔧 Configuration

### Variables d'Environnement

```bash
# Proxies (optionnel)
PROXY_LIST=http://proxy1:8080,http://proxy2:8080

# User-Agents personnalisés (optionnel)
CUSTOM_USER_AGENTS=...

# Délais personnalisés (optionnel)
SCRAPER_MIN_DELAY=1.0
SCRAPER_MAX_DELAY=3.0
```

### Utilisation dans les Scrapers

Les scrapers utilisent automatiquement ces techniques :

```python
# OVH Forum
from app.scraper import ovh_forum
posts = ovh_forum.scrape_ovh_forum(query="OVH", limit=50)

# G2 Crowd
from app.scraper import g2_crowd
reviews = g2_crowd.scrape_g2_crowd(query="OVH", limit=50)
```

## ⚡ Meilleures Pratiques

1. **Commencez simple** : Utilisez requests avec headers réalistes
2. **Ajoutez des délais** : Toujours entre les requêtes
3. **Respectez robots.txt** : Vérifiez avant de scraper
4. **Utilisez les APIs** : Préférez les APIs officielles
5. **Cachez les résultats** : Évitez de re-scraper inutilement
6. **Surveillez les erreurs** : Loggez les 403/503 pour ajuster
7. **Testez régulièrement** : Les protections évoluent

## 🎯 Solutions par Site

### OVH Forum
- ✅ Headers réalistes
- ✅ Délais humains
- ⚠️ Peut nécessiter Selenium si protection renforcée

### G2 Crowd
- ✅ Headers réalistes
- ✅ Délais humains
- ⚠️ Protection forte - peut nécessiter proxies ou Selenium
- 💡 Alternative : Utiliser G2 API si disponible

### Mastodon
- ✅ API publique - pas de protection
- ✅ Fonctionne bien avec requests simple

## 📚 Ressources

- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Scrapy Middleware](https://docs.scrapy.org/en/latest/topics/spider-middleware.html)
- [HTTP Headers Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)

## ⚖️ Avertissement Légal

Ce guide fournit des techniques techniques. Vous êtes responsable de :
- Respecter les ToS de chaque site
- Respecter les lois locales
- Ne pas surcharger les serveurs
- Utiliser les données de manière éthique

**En cas de doute, utilisez les APIs officielles ou contactez le propriétaire du site.**


