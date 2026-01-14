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

### Option 1 : Déploiement avec Systemd (Linux)

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

### Sauvegardes

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

### Logs

```bash
# Voir les logs du service
sudo journalctl -u ovh-tracker -f

# Logs Nginx
sudo tail -f /var/log/nginx/ovh-tracker-access.log
sudo tail -f /var/log/nginx/ovh-tracker-error.log
```

## Dépannage

### Le Service ne Démarre Pas

```bash
# Vérifier les logs
sudo journalctl -u ovh-tracker -n 50

# Vérifier les permissions
sudo chown -R ovh-tracker:ovh-tracker /home/ovh-tracker/complaints_tracker

# Vérifier le port
sudo netstat -tlnp | grep 8000
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
