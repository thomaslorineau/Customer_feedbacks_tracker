# Guide d'Implémentation - OVH Customer Feedback Tracker

Ce guide décrit comment installer l'application et la déployer sur un serveur de production.

## 📋 Table des Matières

1. [Installation Locale](#installation-locale)
2. [Déploiement sur Serveur](#déploiement-sur-serveur)
3. [Configuration Production](#configuration-production)
4. [Maintenance](#maintenance)
5. [Dépannage](#dépannage)

## Installation Locale

### Prérequis

- **Python 3.11 ou 3.12** (Python 3.13 non supporté)
- **Git** pour cloner le dépôt
- **Navigateur web moderne**
- **Connexion Internet** (pour le scraping)

### Étape 1 : Cloner le Dépôt

```bash
git clone https://github.com/thomaslorineau/complaints_tracker.git
cd complaints_tracker
```

### Étape 2 : Créer l'Environnement Virtuel

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Étape 3 : Installer les Dépendances

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 4 : Configuration (Optionnel)

Créez un fichier `.env` dans le dossier `backend/` :

```bash
# Configuration CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Configuration LLM (pour la génération d'idées)
OPENAI_API_KEY=votre_cle_api_openai
OPENAI_MODEL=gpt-4o-mini

# Ou utiliser Anthropic
ANTHROPIC_API_KEY=votre_cle_api_anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

### Étape 5 : Démarrer le Backend

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Le backend est maintenant accessible sur `http://127.0.0.1:8000`

### Étape 6 : Démarrer le Frontend

Dans un nouveau terminal :

```bash
cd frontend
python -m http.server 3000
```

L'application est accessible sur `http://localhost:3000/index.html`

## Déploiement sur Serveur

### Option 1 : Installation sur VM Linux sans droits sudo

Cette section décrit comment installer l'application sur une VM Linux du réseau local **sans avoir besoin de droits sudo**. Ce guide est conçu pour être suivi par quelqu'un qui n'est pas administrateur système.

> 💡 **Conseil** : Si vous rencontrez des problèmes, notez les messages d'erreur et contactez votre administrateur système.

**📋 Résumé rapide :**
1. Télécharger le script d'installation
2. Exécuter `./install.sh`
3. Démarrer avec `./start.sh`
4. Accéder à `http://IP_DE_LA_VM:8000`

> 🚀 **Méthode rapide :** Utilisez le script d'installation automatique (recommandé) !

#### Installation automatique (Recommandé)

Le moyen le plus simple d'installer l'application est d'utiliser le script d'installation automatique :

```bash
# Télécharger le script d'installation
curl -O https://raw.githubusercontent.com/thomaslorineau/complaints_tracker/master/install.sh

# Ou si vous avez déjà cloné le dépôt :
cd complaints_tracker
chmod +x install.sh

# Lancer l'installation
./install.sh
```

Le script va automatiquement :
- ✅ Vérifier que Python 3.11/3.12 est installé
- ✅ Vérifier que Git est installé
- ✅ Télécharger l'application depuis GitHub
- ✅ Créer l'environnement virtuel Python
- ✅ Installer toutes les dépendances
- ✅ Configurer l'application
- ✅ Préparer les scripts de démarrage

**C'est tout !** L'installation est terminée. Vous pouvez ensuite démarrer l'application avec `./start.sh`.

> 💡 **Note :** Si le script d'installation rencontre des problèmes, suivez les instructions manuelles ci-dessous.

---

#### Installation manuelle

Si vous préférez installer manuellement ou si le script d'installation ne fonctionne pas :

#### Prérequis

Avant de commencer, vous devez avoir :
- ✅ Accès SSH à la VM Linux (ou accès direct à la console)
- ✅ Python 3.11 ou 3.12 installé sur la VM
- ✅ Git installé sur la VM
- ✅ Connexion Internet pour télécharger les dépendances
- ✅ Au moins 500 MB d'espace disque libre

> ⚠️ **Important** : Si Python ou Git ne sont pas installés, contactez votre administrateur système pour les installer. L'installation de Python sans sudo est complexe et peut ne pas fonctionner sur toutes les machines.

#### Étape 1 : Vérifier que Python est installé (Installation manuelle)

Ouvrez un terminal sur la VM et tapez :

```bash
python3 --version
```

**Résultat attendu :** `Python 3.11.x` ou `Python 3.12.x`

Si vous voyez une version inférieure (comme 3.9 ou 3.10), contactez votre administrateur pour installer Python 3.11 ou 3.12.

Vérifiez aussi Git :

```bash
git --version
```

Si Git n'est pas installé, contactez votre administrateur.

#### Étape 2 : Télécharger l'application

Dans le terminal, exécutez ces commandes une par une :

```bash
# Aller dans votre répertoire personnel
cd ~

# Créer un dossier pour l'application
mkdir -p apps
cd apps

# Télécharger l'application depuis GitHub
git clone https://github.com/thomaslorineau/complaints_tracker.git

# Entrer dans le dossier de l'application
cd complaints_tracker
```

✅ Si tout s'est bien passé, vous devriez voir plusieurs dossiers (`backend`, `frontend`, etc.).

#### Étape 3 : Créer l'environnement Python

L'application utilise un "environnement virtuel" Python pour isoler ses dépendances. Créez-le avec :

```bash
# Créer l'environnement virtuel
python3 -m venv venv
```

Cela peut prendre quelques secondes. Ensuite, activez-le :

```bash
# Activer l'environnement virtuel
source venv/bin/activate
```

✅ Vous devriez voir `(venv)` au début de votre ligne de commande. Cela signifie que l'environnement est actif.

#### Étape 4 : Installer les dépendances

L'application a besoin de plusieurs bibliothèques Python. Installez-les avec :

```bash
# Mettre à jour l'outil d'installation Python
pip install --upgrade pip

# Aller dans le dossier backend
cd backend

# Installer toutes les dépendances (cela peut prendre 2-5 minutes)
pip install -r requirements.txt
```

⏳ **Patience** : L'installation peut prendre plusieurs minutes. Ne fermez pas le terminal.

✅ Quand c'est terminé, vous devriez voir "Successfully installed" avec une liste de packages.

> ⚠️ **Si vous avez des erreurs** : Notez le message d'erreur complet et contactez votre administrateur système. Certaines dépendances peuvent nécessiter des outils système installés par un administrateur.

#### Étape 5 : Trouver l'adresse IP de la VM

Avant de configurer l'application, vous devez connaître l'adresse IP de votre VM pour y accéder depuis d'autres ordinateurs du réseau.

Dans le terminal, tapez :

```bash
hostname -I
```

Vous devriez voir une adresse IP, par exemple : `10.19.64.153` (IP interne) ou `5.196.197.1` (IP publique)

📝 **Notez cette adresse IP**, vous en aurez besoin pour accéder à l'application.

Si cette commande ne fonctionne pas, essayez :

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

Cherchez une ligne avec une adresse qui commence par `192.168.` ou `10.` ou `172.` (ce sont des adresses de réseau local).

#### Étape 6 : Configuration Docker (si applicable)

**Si vous êtes dans un conteneur Docker :**

Le script d'installation détecte automatiquement si vous êtes dans un conteneur Docker (par hostname, `/.dockerenv`, ou `cgroup`) et vous propose de configurer le port d'écoute.

**Configuration du port d'écoute :**

Sur les serveurs Docker OVH, l'application doit écouter directement sur le port externe accessible (ex: 11840) plutôt que sur le port 8000 par défaut.

**Méthode automatique (lors de l'installation) :**

Le script `install.sh` vous demande le port à utiliser (ex: 11840). La configuration est sauvegardée dans `backend/.app_config` :

```bash
APP_PORT=11840
```

L'application écoutera directement sur ce port. Redémarrez avec :
```bash
bash scripts/start/stop.sh && bash scripts/start/start.sh
```

**Configuration d'un alias host (optionnel) :**

Lors de l'installation, vous pouvez configurer un alias host pour un accès plus simple (ex: `ovh-tracker.local`).

⚠️ **IMPORTANT** : L'alias host fonctionne **UNIQUEMENT pour l'IP locale** (ex: `10.19.64.153`), pas pour l'IP publique.

- Chaque machine doit ajouter l'alias dans son `/etc/hosts` (Linux/Mac) ou `C:\Windows\System32\drivers\etc\hosts` (Windows)
- Pour l'accès depuis Internet, utilisez directement l'IP publique ou le hostname résolu (voir ci-dessous)

#### Étape 7 : Configuration CORS pour l'accès réseau

Pour permettre l'accès depuis d'autres ordinateurs du réseau, vous devez configurer CORS. Le script d'installation le fait **automatiquement** et détecte :

- Le hostname de la VM
- L'IP locale (ex: `10.19.64.153`)
- L'IP publique (ex: `5.196.197.1`)
- Le hostname résolu depuis l'IP publique (reverse DNS, ex: `tlorinea.sdev-docker.ha.ovh.net`)
- L'alias host configuré (si applicable)
- Le port configuré (8000 par défaut, ou celui configuré dans `backend/.app_config`)

La configuration CORS est automatiquement mise à jour dans `backend/.env` avec toutes les URLs possibles.

**Reconfiguration manuelle (si nécessaire) :**

```bash
cd ~/apps/complaints_tracker
./configure_cors.sh
```

> 💡 **Note** : La configuration CORS est automatique lors de l'installation. Vous n'avez généralement pas besoin de la reconfigurer manuellement.

#### Étape 8 : Démarrer l'application

**Méthode simple (recommandée) : Utiliser les scripts fournis**

```bash
# Retourner à la racine du projet
cd ~/apps/complaints_tracker

# Démarrer l'application
./start.sh
```

> 💡 **Note** : Les scripts se rendent automatiquement exécutables. Plus besoin de faire `chmod +x` manuellement.

✅ Si tout va bien, vous verrez :
```
✅ Serveur démarré avec succès (PID: ...)
🌐 Accès:
- Réseau local : http://10.19.64.153:11840
- Internet : http://tlorinea.sdev-docker.ha.ovh.net:11840
```

**Méthode manuelle :**

Si les scripts ne fonctionnent pas, vous pouvez démarrer manuellement :

```bash
# Activer l'environnement virtuel
source ~/apps/complaints_tracker/venv/bin/activate

# Aller dans le dossier backend
cd ~/apps/complaints_tracker/backend

# Démarrer le serveur
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> ⚠️ **Important** : Avec cette méthode, le serveur s'arrêtera si vous fermez le terminal. Utilisez plutôt la méthode avec les scripts.

#### Étape 8 : Accéder à l'application

Une fois l'application démarrée, vous pouvez y accéder de plusieurs façons :

**Depuis la VM elle-même :**
- Ouvrez un navigateur web sur la VM
- Allez à : `http://localhost:8000`

**Depuis un autre ordinateur du réseau local :**
- Ouvrez un navigateur web sur votre ordinateur
- Allez à : `http://IP_DE_LA_VM:8000` (remplacez par l'IP que vous avez notée à l'étape 5)
- Exemple réseau local : `http://10.19.64.153:11840`
- Exemple Internet : `http://tlorinea.sdev-docker.ha.ovh.net:11840` (hostname résolu automatiquement)

✅ **L'application devrait s'afficher !**

---

## 🌐 Partager l'application sur le réseau local

Une fois l'application démarrée, vous pouvez la partager avec d'autres personnes sur le même réseau local.

### Étape 1 : Trouver l'adresse IP de la VM

Si vous ne l'avez pas déjà notée, trouvez l'IP de votre VM :

```bash
hostname -I
```

Vous obtiendrez quelque chose comme : `10.19.64.153` (IP interne)

Pour l'IP publique, utilisez :
```bash
curl -s ifconfig.me
```

Vous obtiendrez : `5.196.197.1` (IP publique)

Le hostname de l'IP publique est automatiquement résolu via reverse DNS (ex: `tlorinea.sdev-docker.ha.ovh.net`)

### Étape 2 : Construire l'URL de l'application

L'URL de votre application est :
```
http://IP_DE_LA_VM:8000
```

**Exemple :** Si l'IP de votre VM est `10.19.64.153` (interne) ou `5.196.197.1` (publique), l'URL sera :
```
http://10.19.64.153:11840
```
ou
```
http://5.196.197.1:11840
```
(Le port peut varier selon votre configuration - 8000 par défaut, 11840 sur Docker OVH)

### Étape 3 : Partager l'URL

Vous pouvez maintenant partager cette URL avec vos collègues :

**Par email :**
```
Bonjour,

L'application OVH Customer Feedback Tracker est maintenant disponible :

Sur le réseau local : http://10.19.64.153:11840
Depuis Internet : http://tlorinea.sdev-docker.ha.ovh.net:11840

Vous pouvez y accéder depuis votre navigateur web.

Cordialement
```

**Par message/chat :**
```
L'app est disponible ici : http://tlorinea.sdev-docker.ha.ovh.net:11840
```

### Étape 4 : Accéder depuis un autre ordinateur

Pour accéder à l'application depuis un autre ordinateur :

1. **Assurez-vous que les deux machines sont sur le même réseau** (même Wi-Fi ou même réseau filaire)
2. **Ouvrez un navigateur web** (Chrome, Firefox, Edge, Safari, etc.)
3. **Tapez l'URL** dans la barre d'adresse :
   - Sur le réseau local : `http://10.19.64.153:11840`
   - Depuis Internet : `http://tlorinea.sdev-docker.ha.ovh.net:11840`
4. **Appuyez sur Entrée**

✅ L'application devrait s'afficher !

### Problèmes d'accès ?

**Si l'application ne s'affiche pas depuis un autre ordinateur :**

1. **Vérifiez que le serveur tourne bien :**
   ```bash
   cd ~/apps/complaints_tracker
   ./status.sh
   ```

2. **Vérifiez que vous utilisez la bonne IP :**
   ```bash
   hostname -I
   ```

3. **Vérifiez que les deux machines sont sur le même réseau :**
   - Les deux doivent être sur le même Wi-Fi ou le même réseau filaire
   - Les adresses IP doivent commencer par les mêmes chiffres (ex: `192.168.1.x`)

4. **Vérifiez le firewall :**
   - Si vous avez un firewall activé sur la VM, il peut bloquer les connexions
   - Contactez votre administrateur système pour ouvrir le port 8000

5. **Testez depuis la VM elle-même :**
   - Ouvrez un navigateur sur la VM et allez à `http://localhost:8000`
   - Si ça fonctionne, le problème vient du réseau, pas de l'application

### URLs utiles

Une fois l'application accessible, voici les URLs importantes :

- **Interface principale :** `http://IP_DE_LA_VM:8000`
- **Documentation API :** `http://IP_DE_LA_VM:8000/docs`
- **Liste des posts (API) :** `http://IP_DE_LA_VM:8000/posts?limit=10`

---

#### Étape 10 : Gérer l'application (arrêter, redémarrer, vérifier le statut)

L'application fournit des scripts simples pour la gestion. Utilisez-les ainsi :

**Vérifier le statut :**
```bash
cd ~/apps/complaints_tracker
./status.sh
```

**Arrêter l'application :**
```bash
cd ~/apps/complaints_tracker
bash scripts/start/stop.sh
```

**Redémarrer l'application :**
```bash
cd ~/apps/complaints_tracker
bash scripts/start/stop.sh
./start.sh
```

**Voir les logs (pour déboguer) :**
```bash
cd ~/apps/complaints_tracker/backend
tail -f server.log
```

> 💡 **Note** : Les scripts se rendent automatiquement exécutables. Plus besoin de faire `chmod +x` manuellement.

**Note :** Ces scripts sont également disponibles à la racine du projet. Si vous avez cloné le dépôt, vous pouvez les utiliser directement depuis le répertoire du projet :

```bash
cd ~/apps/complaints_tracker
./start.sh    # Démarrer l'application
bash scripts/start/stop.sh     # Arrêter l'application
./status.sh   # Vérifier le statut
./backup.sh   # Sauvegarder la base de données
```

#### Étape 11 : Automatiser le démarrage (optionnel)

Si vous voulez que l'application démarre automatiquement quand vous vous connectez à la VM :

```bash
# Éditer le fichier de configuration
nano ~/.bashrc
```

Ajoutez ces lignes à la fin du fichier :

```bash
# Démarrer l'application OVH Tracker automatiquement
if [ -f "$HOME/apps/complaints_tracker/start.sh" ]; then
    if ! pgrep -f "uvicorn app.main:app" > /dev/null; then
        sleep 2
        bash "$HOME/apps/complaints_tracker/start.sh" > /dev/null 2>&1 &
    fi
fi
```

Sauvegardez avec `Ctrl+O`, `Enter`, puis `Ctrl+X`.

> ⚠️ **Note** : Cette méthode fonctionne seulement si vous vous connectez en SSH. Pour un démarrage automatique au boot de la VM, vous aurez besoin de l'aide d'un administrateur système.

---

## 📝 Résumé des commandes utiles

Voici un résumé des commandes les plus utiles :

**Gestion de l'application :**
```bash
cd ~/apps/complaints_tracker
./start.sh      # Démarrer l'application
bash scripts/start/stop.sh       # Arrêter l'application
./status.sh     # Vérifier le statut
./backup.sh     # Sauvegarder la base de données
```

**Voir les logs :**
```bash
tail -f ~/apps/complaints_tracker/backend/server.log
```

**Trouver l'IP de la VM :**
```bash
hostname -I
```

**Configurer CORS (si problème d'accès réseau) :**
```bash
cd ~/apps/complaints_tracker
./configure_cors.sh
bash scripts/start/stop.sh
./start.sh
```

**Tester que l'application fonctionne :**
```bash
curl http://localhost:8000/docs
```

**Redémarrer l'application :**
```bash
cd ~/apps/complaints_tracker
bash scripts/start/stop.sh
./start.sh
```

#### Dépannage sans sudo

**Problème : Port déjà utilisé**

```bash
# Trouver le processus utilisant le port
lsof -i :8000 2>/dev/null || netstat -tlnp 2>/dev/null | grep 8000

# Si c'est votre processus, l'arrêter
~/apps/complaints_tracker/scripts/start/stop.sh

# Si c'est un autre processus, utiliser un autre port
# Modifier start.sh pour utiliser --port 8001
```

**Problème : Permission refusée sur le port**

```bash
# Utiliser un port > 1024 (non-privilégié)
# Modifier start.sh pour utiliser --port 8080
```

**Problème : Base de données verrouillée**

```bash
# Vérifier les processus utilisant la DB
lsof ~/apps/complaints_tracker/backend/data.db 2>/dev/null

# Arrêter tous les processus Python de l'application
pkill -f "uvicorn app.main:app"
```

**Problème : Dépendances manquantes**

```bash
# Réinstaller les dépendances
source ~/apps/complaints_tracker/venv/bin/activate
cd ~/apps/complaints_tracker/backend
pip install --force-reinstall -r requirements.txt
```

### Option 2 : Déploiement avec Systemd (Linux avec sudo)

#### 1. Préparer le Serveur

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Python et dépendances
sudo apt install python3.11 python3.11-venv python3-pip git nginx -y
```

#### 2. Cloner et Configurer l'Application

```bash
# Créer un utilisateur dédié
sudo useradd -m -s /bin/bash ovh-tracker
sudo su - ovh-tracker

# Cloner le dépôt
git clone https://github.com/thomaslorineau/complaints_tracker.git
cd complaints_tracker

# Créer l'environnement virtuel
python3.11 -m venv venv
source venv/bin/activate

# Installer les dépendances
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Créer le Service Systemd

Créez le fichier `/etc/systemd/system/ovh-tracker.service` :

```ini
[Unit]
Description=OVH Customer Feedback Tracker
After=network.target

[Service]
Type=simple
User=ovh-tracker
WorkingDirectory=/home/ovh-tracker/complaints_tracker/backend
Environment="PATH=/home/ovh-tracker/complaints_tracker/venv/bin"
Environment="CORS_ORIGINS=https://votre-domaine.com"
ExecStart=/home/ovh-tracker/complaints_tracker/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Activer et Démarrer le Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable ovh-tracker
sudo systemctl start ovh-tracker
sudo systemctl status ovh-tracker
```

#### 5. Configurer Nginx comme Reverse Proxy

Créez le fichier `/etc/nginx/sites-available/ovh-tracker` :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    # Redirection HTTPS (optionnel mais recommandé)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    # Certificats SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/votre-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.com/privkey.pem;

    # Frontend
    location / {
        root /home/ovh-tracker/complaints_tracker/frontend;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (si nécessaire)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Logs
    access_log /var/log/nginx/ovh-tracker-access.log;
    error_log /var/log/nginx/ovh-tracker-error.log;
}
```

Activez la configuration :

```bash
sudo ln -s /etc/nginx/sites-available/ovh-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. Configurer SSL avec Let's Encrypt (Recommandé)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com
```

### Option 2 : Déploiement avec Docker

#### 1. Créer le Dockerfile

Créez `Dockerfile` à la racine du projet :

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Exposer le port
EXPOSE 8000

# Variables d'environnement
ENV PYTHONUNBUFFERED=1

# Commande de démarrage
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Créer docker-compose.yml

```yaml
version: '3.8'

services:
  ovh-tracker:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend/data.db:/app/backend/data.db
      - ./backend/.env:/app/backend/.env
    environment:
      - CORS_ORIGINS=https://votre-domaine.com
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 3. Démarrer avec Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

### Option 3 : Déploiement sur Cloud (AWS, Azure, GCP)

#### AWS EC2

1. **Créer une instance EC2** (Ubuntu 22.04 LTS recommandé)
2. **Configurer le Security Group** :
   - Port 22 (SSH)
   - Port 80 (HTTP)
   - Port 443 (HTTPS)
3. **Suivre les étapes de l'Option 1** (Systemd)

#### Azure App Service

1. **Créer une Web App** avec Python 3.11
2. **Configurer les variables d'environnement** dans le portail Azure
3. **Déployer via Git** ou Azure CLI

#### Google Cloud Run

1. **Créer un Dockerfile** (voir Option 2)
2. **Déployer avec gcloud** :
```bash
gcloud run deploy ovh-tracker \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

## Configuration Production

### Variables d'Environnement Recommandées

```bash
# CORS - Limiter aux domaines autorisés
CORS_ORIGINS=https://votre-domaine.com,https://www.votre-domaine.com

# LLM Configuration
OPENAI_API_KEY=votre_cle_secrete
OPENAI_MODEL=gpt-4o-mini

# Base de données (si PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/ovh_tracker

# Logging
LOG_LEVEL=INFO
```

### Sécurité

1. **Firewall** : Limiter l'accès au port 8000 (backend) uniquement depuis Nginx
2. **SSL/TLS** : Toujours utiliser HTTPS en production
3. **Secrets** : Ne jamais commiter les fichiers `.env` ou clés API
4. **Backup** : Configurer des sauvegardes régulières de `data.db`

### Performance

1. **Base de données** : Pour plus de 100k posts, migrer vers PostgreSQL
2. **Cache** : Considérer Redis pour le cache des requêtes fréquentes
3. **Rate Limiting** : Configurer des limites de taux pour les endpoints API
4. **Monitoring** : Utiliser des outils comme Prometheus + Grafana

## Maintenance

### Mettre à Jour l'Application

**Avec sudo (Systemd) :**

```bash
# Se connecter au serveur
ssh user@votre-serveur

# Arrêter le service
sudo systemctl stop ovh-tracker

# Mettre à jour le code
cd /home/ovh-tracker/complaints_tracker
git pull origin master

# Mettre à jour les dépendances
source venv/bin/activate
cd backend
pip install -r requirements.txt --upgrade

# Redémarrer le service
sudo systemctl start ovh-tracker
```

**Sans sudo (Installation manuelle) :**

**Méthode automatique (recommandée) :**

```bash
# Se connecter au serveur
ssh user@votre-vm

# Mettre à jour l'application (fait tout automatiquement)
cd ~/apps/complaints_tracker
./update.sh
```

Le script `update.sh` fait automatiquement :
- ✅ Arrête l'application
- ✅ Sauvegarde la configuration (.env, .app_config, .host_alias)
- ✅ Met à jour le code via `git pull`
- ✅ Restaure la configuration
- ✅ Met à jour les dépendances Python
- ✅ Redémarre l'application

**Méthode manuelle (si nécessaire) :**

```bash
# Se connecter au serveur
ssh user@votre-vm

# Arrêter l'application
~/apps/complaints_tracker/scripts/start/stop.sh

# Mettre à jour le code (gère automatiquement les modifications locales)
cd ~/apps/complaints_tracker
git stash  # Sauvegarder les modifications locales si nécessaire
git pull origin master
git stash pop  # Restaurer les modifications si nécessaire

# Mettre à jour les dépendances
source venv/bin/activate
cd backend
pip install -r requirements.txt --upgrade

# Redémarrer l'application
~/apps/complaints_tracker/start.sh

# Vérifier le statut
~/apps/complaints_tracker/status.sh
```

> 💡 **Note** : Le script `update.sh` gère automatiquement les modifications locales via `git stash`, donc vous n'avez généralement pas besoin de le faire manuellement.

### Sauvegardes

**Avec sudo (Systemd) :**

```bash
# Script de sauvegarde quotidienne
#!/bin/bash
BACKUP_DIR="/backups/ovh-tracker"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
cp /home/ovh-tracker/complaints_tracker/backend/data.db $BACKUP_DIR/data_$DATE.db
# Garder seulement les 30 derniers backups
find $BACKUP_DIR -name "data_*.db" -mtime +30 -delete
```

Ajoutez au crontab :
```bash
0 2 * * * /path/to/backup-script.sh
```

**Sans sudo (Installation manuelle) :**

```bash
# Créer le script de sauvegarde
cat > ~/apps/complaints_tracker/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="$HOME/backups/ovh-tracker"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
cp "$HOME/apps/complaints_tracker/backend/data.db" "$BACKUP_DIR/data_$DATE.db"
# Garder seulement les 30 derniers backups
find "$BACKUP_DIR" -name "data_*.db" -mtime +30 -delete
echo "Sauvegarde effectuée: $BACKUP_DIR/data_$DATE.db"
EOF

chmod +x ~/apps/complaints_tracker/backup.sh

# Tester la sauvegarde
~/apps/complaints_tracker/backup.sh

# Ajouter au crontab (sans sudo)
crontab -e
# Ajouter cette ligne pour une sauvegarde quotidienne à 2h du matin
# 0 2 * * * $HOME/apps/complaints_tracker/backup.sh >> $HOME/backups/ovh-tracker/backup.log 2>&1
```

### Logs

**Avec sudo (Systemd) :**

```bash
# Voir les logs du service
sudo journalctl -u ovh-tracker -f

# Logs Nginx
sudo tail -f /var/log/nginx/ovh-tracker-access.log
sudo tail -f /var/log/nginx/ovh-tracker-error.log
```

**Sans sudo (Installation manuelle) :**

```bash
# Voir les logs du serveur
tail -f ~/apps/complaints_tracker/backend/server.log

# Voir les dernières lignes
tail -n 100 ~/apps/complaints_tracker/backend/server.log

# Chercher des erreurs
grep -i error ~/apps/complaints_tracker/backend/server.log

# Voir les logs du frontend (si servi séparément)
tail -f ~/apps/complaints_tracker/frontend.log
```

## Dépannage

### Le Service ne Démarre Pas

**Avec sudo (Systemd) :**

```bash
# Vérifier les logs
sudo journalctl -u ovh-tracker -n 50

# Vérifier les permissions
sudo chown -R ovh-tracker:ovh-tracker /home/ovh-tracker/complaints_tracker

# Vérifier le port
sudo netstat -tlnp | grep 8000
```

**Sans sudo (Installation manuelle) :**

```bash
# Vérifier les logs
tail -n 50 ~/apps/complaints_tracker/backend/server.log

# Vérifier le statut
~/apps/complaints_tracker/status.sh

# Vérifier les processus
ps aux | grep uvicorn

# Vérifier le port
netstat -tlnp 2>/dev/null | grep 8000 || ss -tlnp | grep 8000

# Vérifier les permissions
ls -la ~/apps/complaints_tracker/backend/data.db
ls -la ~/apps/complaints_tracker/backend/server.log

# Tester manuellement
source ~/apps/complaints_tracker/venv/bin/activate
cd ~/apps/complaints_tracker/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Erreurs de Connexion

1. **Vérifier le firewall** : `sudo ufw status`
2. **Vérifier Nginx** : `sudo nginx -t`
3. **Vérifier les logs** : `sudo tail -f /var/log/nginx/error.log`

### Problèmes de Base de Données

```bash
# Vérifier les permissions
ls -la /home/ovh-tracker/complaints_tracker/backend/data.db

# Réinitialiser la base (ATTENTION: supprime toutes les données)
rm /home/ovh-tracker/complaints_tracker/backend/data.db
cd /home/ovh-tracker/complaints_tracker/backend
source ../venv/bin/activate
python -c "from app.db import init_db; init_db()"
```

### Scrapers ne Fonctionnent Pas

1. **Vérifier la connexion Internet** : `ping google.com`
2. **Vérifier les logs** : `sudo journalctl -u ovh-tracker | grep scraper`
3. **Tester manuellement** : Se connecter au serveur et tester les scrapers

## Ressources Additionnelles

- [Architecture Documentation](ARCHITECTURE.md) - Architecture détaillée du système
- [Test Guide](GUIDE_TEST.md) - Guide de test de l'application
- [Anti-Bot Guide](backend/ANTI_BOT_GUIDE.md) - Techniques anti-scraping
