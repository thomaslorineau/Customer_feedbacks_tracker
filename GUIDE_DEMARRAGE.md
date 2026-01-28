# 🚀 Guide de Démarrage Rapide

Ce guide vous explique comment démarrer le projet **OVH Customer Feedbacks Tracker** en local.

## ✅ État de la Configuration

Votre environnement a été configuré avec succès :

- ✅ **Python 3.11.3** détecté et fonctionnel
- ✅ **Dépendances Python** installées
- ✅ **Fichier .env** créé dans `backend/.env`

## ⚠️ Action Requise : Configuration PostgreSQL

**PostgreSQL est obligatoire** pour ce projet. Vous devez configurer `DATABASE_URL` dans `backend/.env`.

### Option 1 : Service Cloud Gratuit (RECOMMANDÉ) ⭐

**Supabase** (gratuit jusqu'à 500MB) :

1. Allez sur https://supabase.com
2. Créez un compte gratuit
3. Créez un nouveau projet
4. Allez dans **Settings** > **Database**
5. Copiez la **Connection string**
6. Remplacez `[YOUR-PASSWORD]` par votre mot de passe
7. Mettez à jour `DATABASE_URL` dans `backend/.env`

**Neon** (gratuit jusqu'à 3GB) :

1. Allez sur https://neon.tech
2. Créez un compte gratuit
3. Créez un nouveau projet
4. Copiez la connection string
5. Mettez à jour `DATABASE_URL` dans `backend/.env`

### Option 2 : PostgreSQL Local

1. Installez PostgreSQL depuis https://www.postgresql.org/download/windows/
2. Créez la base de données :
```sql
CREATE DATABASE ocft_tracker;
CREATE USER ocft_user WITH PASSWORD 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON DATABASE ocft_tracker TO ocft_user;
```
3. Mettez à jour `DATABASE_URL` dans `backend/.env` :
```env
DATABASE_URL=postgresql://ocft_user:votre_mot_de_passe@localhost:5432/ocft_tracker
```

### Option 3 : Docker PostgreSQL

Si vous avez Docker Desktop :

```powershell
docker run -d `
  --name ocft_postgres `
  -e POSTGRES_DB=ocft_tracker `
  -e POSTGRES_USER=ocft_user `
  -e POSTGRES_PASSWORD=ocft_secure_password_2026 `
  -p 5432:5432 `
  postgres:15-alpine
```

Puis dans `backend/.env` :
```env
DATABASE_URL=postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker
```

📖 **Guide détaillé** : Voir `backend/SETUP_POSTGRES.md`

## 🚀 Démarrer l'Application

Une fois PostgreSQL configuré, démarrez l'application :

### Méthode 1 : Script Automatique (RECOMMANDÉ)

```powershell
cd backend
.\start-local.ps1
```

Ce script :
- ✅ Vérifie Python
- ✅ Vérifie la configuration
- ✅ Teste la connexion PostgreSQL
- ✅ Démarre le serveur

### Méthode 2 : Démarrage Manuel

```powershell
cd backend
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 🌐 Accéder à l'Application

Une fois le serveur démarré, ouvrez votre navigateur :

- **Application** : http://localhost:8000
- **Documentation API** : http://localhost:8000/api/docs
- **Dashboard** : http://localhost:8000/dashboard

## 🛑 Arrêter l'Application

Appuyez sur **Ctrl+C** dans le terminal où le serveur tourne.

## 🧪 Tester Rapidement

1. Ouvrez http://localhost:8000
2. Cliquez sur **"Feedbacks Collection"**
3. Cliquez sur **"Scrape Reddit"** (ou un autre bouton)
4. Attendez quelques secondes
5. Vérifiez les résultats dans le dashboard

## ❌ Dépannage

### Erreur "DATABASE_URL not found"
- Vérifiez que `backend/.env` existe
- Vérifiez que `DATABASE_URL` est défini dans `.env`

### Erreur de connexion PostgreSQL
- Vérifiez que PostgreSQL est démarré
- Vérifiez que `DATABASE_URL` est correct
- Testez la connexion avec :
```powershell
cd backend
py -c "import os; os.environ['DATABASE_URL']='votre_connection_string'; from app.database import get_db_connection; conn, _ = get_db_connection(); print('OK'); conn.close()"
```

### Port 8000 déjà utilisé
- Arrêtez l'autre application qui utilise le port 8000
- Ou changez le port dans la commande : `--port 8001`

## 📚 Documentation Complète

- **Guide PostgreSQL** : `backend/SETUP_POSTGRES.md`
- **Documentation API** : http://localhost:8000/api/docs (après démarrage)
- **README principal** : `README.md`

## 🎯 Prochaines Étapes

1. ✅ Configurez PostgreSQL (voir ci-dessus)
2. ✅ Démarrez l'application
3. ✅ Testez les fonctionnalités de scraping
4. ⚙️ Configurez les clés API (optionnel) pour les fonctionnalités LLM
5. ⚙️ Configurez les notifications email (optionnel)

---

**Besoin d'aide ?** Consultez `backend/SETUP_POSTGRES.md` pour la configuration PostgreSQL détaillée.


