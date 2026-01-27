# Correction : Accès HTTPS sur le port 11840

## Problème
Impossible d'accéder à `https://gw.lab.core.ovh.net:11840/dashboard` car nginx n'écoutait qu'en HTTP sur ce port.

## Solution appliquée
La configuration nginx a été modifiée pour :
- Écouter en HTTPS sur le port 11840
- Rediriger automatiquement HTTP vers HTTPS
- Utiliser les certificats SSL depuis `/etc/nginx/ssl/`

## Étapes de déploiement

### 1. Générer les certificats SSL

Sur votre serveur distant, vous avez deux options :

#### Option A : Certificat auto-signé (développement/test)

```bash
cd nginx
chmod +x generate-self-signed-cert.sh
./generate-self-signed-cert.sh
```

⚠️ **Note** : Les navigateurs afficheront un avertissement de sécurité avec un certificat auto-signé. Cliquez sur "Avancé" puis "Continuer vers le site" pour accepter.

#### Option B : Certificat Let's Encrypt (production recommandé)

```bash
# Installer certbot si nécessaire
sudo apt-get update
sudo apt-get install certbot

# Générer le certificat
sudo certbot certonly --standalone -d gw.lab.core.ovh.net

# Créer le dossier ssl si nécessaire
mkdir -p nginx/ssl

# Copier les certificats dans nginx/ssl/
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/privkey.pem nginx/ssl/key.pem
sudo chmod 644 nginx/ssl/cert.pem
sudo chmod 600 nginx/ssl/key.pem
```

### 2. Vérifier que les certificats existent

```bash
ls -la nginx/ssl/
```

Vous devriez voir :
- `cert.pem` (certificat)
- `key.pem` (clé privée)

### 3. Redémarrer nginx

```bash
# Redémarrer uniquement nginx pour appliquer la nouvelle configuration
docker compose restart nginx

# Vérifier les logs pour s'assurer qu'il n'y a pas d'erreur
docker compose logs nginx --tail=50
```

Si nginx ne démarre pas, vérifiez les erreurs :
```bash
docker compose logs nginx
```

### 4. Vérifier l'accès

```bash
# Tester HTTPS localement
curl -k https://localhost:11840/health

# Tester depuis l'extérieur
curl -k https://gw.lab.core.ovh.net:11840/health
```

### 5. Accéder au dashboard

Vous pouvez maintenant accéder à :
- **HTTPS** : `https://gw.lab.core.ovh.net:11840/dashboard` ✅
- **HTTP** : `http://gw.lab.core.ovh.net:11840/dashboard` → redirige automatiquement vers HTTPS

## Dépannage

### Erreur : "SSL certificate not found"

Les certificats n'existent pas dans `nginx/ssl/`. Générez-les avec l'option A ou B ci-dessus.

### Erreur : "Port 11840 already in use"

Un autre processus utilise le port 11840. Vérifiez :
```bash
sudo netstat -tlnp | grep 11840
# ou
sudo ss -tlnp | grep 11840
```

### nginx ne démarre pas

Vérifiez la syntaxe de la configuration :
```bash
docker compose exec nginx nginx -t
```

### Les certificats Let's Encrypt expirent

Renouvelez-les tous les 90 jours :
```bash
sudo certbot renew
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/gw.lab.core.ovh.net/privkey.pem nginx/ssl/key.pem
docker compose restart nginx
```

## Vérification finale

Une fois tout configuré, vérifiez que :
1. ✅ Les certificats SSL existent dans `nginx/ssl/`
2. ✅ nginx démarre sans erreur (`docker compose logs nginx`)
3. ✅ L'accès HTTPS fonctionne (`curl -k https://gw.lab.core.ovh.net:11840/health`)
4. ✅ Le dashboard est accessible (`https://gw.lab.core.ovh.net:11840/dashboard`)
