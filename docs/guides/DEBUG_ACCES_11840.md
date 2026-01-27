# Dépannage : Accès à gw.lab.core.ovh.net:11840

## Problème
Impossible d'accéder à `https://gw.lab.core.ovh.net:11840` depuis Linux.

## Diagnostic rapide

### 1. Vérifier l'état des conteneurs Docker

```bash
docker compose ps
```

Tous les conteneurs doivent être en état "Up" :
- `ocft_nginx` (reverse proxy)
- `ocft_api` (API FastAPI)
- `ocft_postgres` (base de données)
- `ocft_redis` (cache)
- `ocft_worker` (travailleur)
- `ocft_scheduler` (planificateur)

**Si des conteneurs sont arrêtés :**
```bash
docker compose up -d
```

### 2. Vérifier les certificats SSL

Nginx nécessite des certificats SSL pour fonctionner sur le port 11840 en HTTPS.

```bash
# Vérifier que les certificats existent
ls -la nginx/ssl/
```

Vous devez voir :
- `cert.pem` (certificat)
- `key.pem` (clé privée)

**Si les certificats manquent :**

```bash
cd nginx
chmod +x generate-self-signed-cert.sh
./generate-self-signed-cert.sh
cd ..
docker compose restart nginx
```

### 3. Vérifier les logs nginx

```bash
# Logs nginx (erreurs)
docker compose logs nginx --tail=50

# Vérifier la configuration nginx
docker compose exec nginx nginx -t
```

**Erreurs courantes :**
- `SSL certificate not found` → Les certificats manquent (voir étape 2)
- `Port already in use` → Un autre processus utilise le port 11840
- `upstream connection failed` → L'API n'est pas accessible depuis nginx

### 4. Vérifier que le port 11840 est en écoute

```bash
# Vérifier les ports en écoute
sudo ss -tlnp | grep 11840
# OU
sudo netstat -tlnp | grep 11840
```

Vous devriez voir nginx écouter sur le port 11840.

**Si le port n'est pas en écoute :**
```bash
docker compose restart nginx
docker compose logs nginx
```

### 5. Tester la connexion locale

```bash
# Test HTTP (devrait rediriger vers HTTPS)
curl -L http://localhost:11840/health

# Test HTTPS (avec certificat auto-signé, utiliser -k)
curl -k https://localhost:11840/health
```

### 6. Vérifier l'état de l'API

```bash
# Logs API
docker compose logs api --tail=50

# Santé de l'API
docker compose exec api curl -f http://localhost:8000/health
```

## Solutions par problème

### Problème : Containers ne démarrent pas

```bash
# Arrêter tous les containers
docker compose down

# Redémarrer
docker compose up -d

# Vérifier les logs
docker compose logs
```

### Problème : Certificats SSL manquants

```bash
# Générer des certificats auto-signés
cd nginx
chmod +x generate-self-signed-cert.sh
./generate-self-signed-cert.sh
cd ..

# Redémarrer nginx
docker compose restart nginx

# Vérifier les logs
docker compose logs nginx
```

### Problème : Port 11840 déjà utilisé

```bash
# Trouver le processus qui utilise le port
sudo lsof -i :11840
# OU
sudo ss -tlnp | grep 11840

# Arrêter le processus ou changer le port dans docker-compose.yml
```

### Problème : nginx ne démarre pas

```bash
# Vérifier la syntaxe de la configuration
docker compose exec nginx nginx -t

# Vérifier les logs détaillés
docker compose logs nginx

# Redémarrer nginx
docker compose restart nginx
```

### Problème : API inaccessible depuis nginx

```bash
# Vérifier que l'API est démarrée
docker compose ps api

# Vérifier les logs API
docker compose logs api --tail=100

# Tester la connexion depuis nginx vers l'API
docker compose exec nginx wget -O- http://api:8000/health
```

### Problème : Firewall bloque le port 11840

```bash
# Vérifier le firewall (UFW)
sudo ufw status
sudo ufw allow 11840/tcp

# Vérifier iptables
sudo iptables -L -n | grep 11840

# Ouvrir le port si nécessaire
sudo iptables -A INPUT -p tcp --dport 11840 -j ACCEPT
```

## Solution complète (redémarrage propre)

Si rien ne fonctionne, redémarrez proprement :

```bash
# 1. Arrêter tous les containers
docker compose down

# 2. Vérifier/générer les certificats SSL
cd nginx
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    chmod +x generate-self-signed-cert.sh
    ./generate-self-signed-cert.sh
fi
cd ..

# 3. Redémarrer tous les services
docker compose up -d

# 4. Attendre que les services démarrent (30 secondes)
sleep 30

# 5. Vérifier l'état
docker compose ps

# 6. Tester la connexion
curl -k https://localhost:11840/health
```

## Vérification finale

Une fois les corrections appliquées :

```bash
# 1. Tous les containers sont "Up"
docker compose ps

# 2. Le port 11840 est en écoute
sudo ss -tlnp | grep 11840

# 3. La connexion HTTPS fonctionne localement
curl -k https://localhost:11840/health

# 4. Les logs nginx ne montrent pas d'erreurs
docker compose logs nginx | grep -i error
```

## Accès depuis l'extérieur

Si le serveur est accessible depuis l'extérieur :

```bash
# Depuis votre machine Linux locale
curl -k https://gw.lab.core.ovh.net:11840/health
```

**Note :** Avec un certificat auto-signé, votre navigateur affichera un avertissement de sécurité. Cliquez sur "Avancé" puis "Continuer vers le site" pour accepter.

## Commandes utiles

```bash
# Voir tous les containers
docker compose ps -a

# Logs en temps réel
docker compose logs -f nginx
docker compose logs -f api

# Redémarrer un service spécifique
docker compose restart nginx
docker compose restart api

# Reconstruire et redémarrer
docker compose up -d --build

# Nettoyer et repartir à zéro (ATTENTION: supprime les données)
docker compose down -v
docker compose up -d
```
