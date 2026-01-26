# Configuration HTTPS avec Nginx

## Génération du certificat SSL

### Option 1 : Certificat auto-signé (développement/test)

```bash
cd nginx
chmod +x generate-self-signed-cert.sh
./generate-self-signed-cert.sh
```

Cela génère un certificat auto-signé valable 365 jours dans `nginx/ssl/`.

**⚠️ Note :** Les navigateurs afficheront un avertissement de sécurité avec un certificat auto-signé. Cliquez sur "Avancé" puis "Continuer vers le site" pour accepter.

### Option 2 : Certificat Let's Encrypt (production)

Pour un certificat valide en production, utilisez certbot :

```bash
# Installer certbot
sudo apt-get update
sudo apt-get install certbot

# Générer le certificat
sudo certbot certonly --standalone -d gw.lab.core.ovh.net

# Copier les certificats dans nginx/ssl/
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/privkey.pem nginx/ssl/key.pem
sudo chmod 644 nginx/ssl/cert.pem
sudo chmod 600 nginx/ssl/key.pem
```

## Démarrage

Après avoir généré les certificats :

```bash
docker compose up -d nginx
docker compose restart api  # Pour appliquer les nouvelles CORS_ORIGINS
```

## Accès

- HTTP : `http://gw.lab.core.ovh.net` → redirige automatiquement vers HTTPS
- HTTPS : `https://gw.lab.core.ovh.net:443` (ou `https://gw.lab.core.ovh.net`)

## Vérification

```bash
# Vérifier que nginx démarre correctement
docker compose logs nginx

# Tester HTTPS
curl -k https://gw.lab.core.ovh.net/api/version
```

## Renouvellement Let's Encrypt

Les certificats Let's Encrypt expirent après 90 jours. Pour renouveler :

```bash
sudo certbot renew
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/privkey.pem nginx/ssl/key.pem
docker compose restart nginx
```
