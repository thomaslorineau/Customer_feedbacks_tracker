# 🗄️ Configuration PostgreSQL - Guide Rapide

Ce projet nécessite PostgreSQL pour fonctionner. Voici comment le configurer rapidement.

## Option 1 : Service Cloud Gratuit (RECOMMANDÉ) ⭐

### Supabase (Gratuit jusqu'à 500MB)

1. Allez sur https://supabase.com
2. Créez un compte gratuit
3. Créez un nouveau projet
4. Allez dans **Settings** > **Database**
5. Copiez la **Connection string** (format: `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres`)
6. Remplacez `[YOUR-PASSWORD]` par le mot de passe de votre projet
7. Mettez à jour `DATABASE_URL` dans `backend/.env`

### Neon (Gratuit jusqu'à 3GB)

1. Allez sur https://neon.tech
2. Créez un compte gratuit
3. Créez un nouveau projet
4. Copiez la connection string
5. Mettez à jour `DATABASE_URL` dans `backend/.env`

## Option 2 : PostgreSQL Local

### Installation sur Windows

1. Téléchargez PostgreSQL depuis https://www.postgresql.org/download/windows/
2. Installez PostgreSQL (notez le mot de passe du superutilisateur `postgres`)
3. Ouvrez **pgAdmin** ou **psql**

### Création de la base de données

Ouvrez **psql** ou **pgAdmin** et exécutez :

```sql
-- Créer la base de données
CREATE DATABASE ocft_tracker;

-- Créer un utilisateur (optionnel, vous pouvez utiliser postgres)
CREATE USER ocft_user WITH PASSWORD 'votre_mot_de_passe_securise';

-- Donner les permissions
GRANT ALL PRIVILEGES ON DATABASE ocft_tracker TO ocft_user;

-- Se connecter à la base de données
\c ocft_tracker

-- Créer les tables (le script init_postgres.sql sera exécuté automatiquement au premier démarrage)
```

### Configuration dans .env

Mettez à jour `DATABASE_URL` dans `backend/.env` :

```env
DATABASE_URL=postgresql://ocft_user:votre_mot_de_passe_securise@localhost:5432/ocft_tracker
```

## Option 3 : Docker (Le plus simple)

Si vous avez Docker Desktop installé :

```powershell
# Démarrer PostgreSQL dans Docker
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

## Vérification

Après avoir configuré PostgreSQL, testez la connexion :

```powershell
cd backend
py -c "import os; os.environ['DATABASE_URL']='votre_connection_string'; from app.database import get_db_connection; conn, _ = get_db_connection(); print('✅ Connexion réussie!'); conn.close()"
```

## Initialisation des tables

Les tables seront créées automatiquement au premier démarrage de l'application. Le script `backend/scripts/init_postgres.sql` contient le schéma de base de données.

## Besoin d'aide ?

- Documentation PostgreSQL : https://www.postgresql.org/docs/
- Supabase Docs : https://supabase.com/docs
- Neon Docs : https://neon.tech/docs


