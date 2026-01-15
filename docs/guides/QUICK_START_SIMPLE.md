# 🚀 Guide de Démarrage Simple - Pour Débutants

Ce guide vous explique **étape par étape** comment démarrer l'application, même si vous n'avez jamais utilisé Python.

---

## ✅ Prérequis

Avant de commencer, vous devez avoir :

1. **Python 3.11 ou supérieur** installé sur votre ordinateur
2. **Une connexion Internet** (pour télécharger les dépendances)
3. **Un navigateur web** (Chrome, Firefox, Edge, etc.)

---

## 🔍 Vérifier Python

### Windows
1. Ouvrir **PowerShell** ou **Invite de commandes**
2. Taper : `python --version`
3. Vous devriez voir : `Python 3.11.x` ou supérieur

**Si Python n'est pas installé :**
- Télécharger depuis : https://www.python.org/downloads/
- ⚠️ **Important** : Cocher "Add Python to PATH" lors de l'installation

### Linux/Mac
```bash
python3 --version
```

---

## 📦 Installation (5 minutes)

### Étape 1 : Ouvrir un terminal

**Windows :**
- Appuyer sur `Windows + R`
- Taper `powershell` et appuyer sur Entrée

**Linux/Mac :**
- Ouvrir le Terminal

### Étape 2 : Aller dans le dossier du projet

```bash
cd ovh-complaints-tracker
```

*(Remplacez `ovh-complaints-tracker` par le chemin complet si nécessaire)*

### Étape 3 : Installer les dépendances

```bash
cd backend
pip install -r requirements.txt
```

**⏱️ Cela peut prendre 2-5 minutes** (téléchargement des bibliothèques)

**Si `pip` ne fonctionne pas, essayer :**
- Windows : `python -m pip install -r requirements.txt`
- Linux/Mac : `pip3 install -r requirements.txt`

---

## 🚀 Démarrer l'application

### Option 1 : Script automatique (RECOMMANDÉ)

**Windows :**
```powershell
.\scripts\start\start_server.ps1
```

**Linux/Mac :**
```bash
./scripts/start/start.sh
```

**Vous devriez voir :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 🛑 Arrêter l'application

**Windows :**
```powershell
.\scripts\start\stop.sh
```

**Linux/Mac :**
```bash
./scripts/start/stop.sh
```

### Option 2 : Commande manuelle

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Vous devriez voir :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## 🌐 Accéder à l'application

1. **Ouvrir votre navigateur** (Chrome, Firefox, Edge, etc.)
2. **Aller à l'adresse :** http://localhost:8000
3. **Vous devriez voir** la page d'accueil de l'application

---

## 🧪 Tester rapidement

### Test 1 : Voir les posts existants
1. Cliquer sur **"Dashboard Analytics"** dans le menu
2. Vous devriez voir des graphiques et statistiques

### Test 2 : Lancer un scraper
1. Cliquer sur **"Feedbacks Collection"** dans le menu
2. Cliquer sur le bouton **"Scrape Reddit"** (ou un autre)
3. Attendre quelques secondes
4. Vous devriez voir un message de succès

### Test 3 : Voir les logs
1. Cliquer sur **"Scraping Logs"** dans le menu
2. Vous devriez voir l'historique des opérations

---

## ❌ Problèmes courants

### "python n'est pas reconnu"
**Solution :** Python n'est pas dans le PATH
- Réinstaller Python en cochant "Add Python to PATH"
- Ou utiliser `py` au lieu de `python` (Windows)

### "pip n'est pas reconnu"
**Solution :** Utiliser `python -m pip` au lieu de `pip`
```bash
python -m pip install -r requirements.txt
```

### "Le port 8000 est déjà utilisé"
**Solution :** Arrêter l'autre application ou changer le port
```bash
python -m uvicorn app.main:app --reload --port 8001
```
Puis aller à : http://localhost:8001

### "Module not found"
**Solution :** Réinstaller les dépendances
```bash
pip install -r requirements.txt --force-reinstall
```

### "Le serveur ne démarre pas"
**Vérifier :**
1. Êtes-vous dans le bon dossier ? (`backend/`)
2. Les dépendances sont-elles installées ?
3. Y a-t-il des erreurs dans le terminal ?

---

## 📚 Prochaines étapes

Une fois l'application démarrée :

1. **Explorer l'interface** - Naviguer entre les différentes pages
2. **Tester les scrapers** - Lancer quelques scrapers pour collecter des données
3. **Voir le dashboard** - Analyser les données collectées
4. **Configurer les clés API** (optionnel) - Pour utiliser les fonctionnalités LLM

📖 **Guide complet :** [GUIDE_TEST.md](GUIDE_TEST.md)

---

## 💡 Astuces

- **Garder le terminal ouvert** - Le serveur doit rester actif
- **Actualiser la page** - Si quelque chose ne fonctionne pas, appuyer sur F5
- **Vérifier les logs** - Les erreurs s'affichent dans le terminal

---

**Besoin d'aide ?** Consultez [GUIDE_TEST.md](GUIDE_TEST.md) pour plus de détails.

