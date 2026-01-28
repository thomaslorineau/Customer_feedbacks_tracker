# 🚀 Comment Démarrer l'Application

## Méthode Rapide (Recommandée)

### Étape 1 : Configurer PostgreSQL

**Option A : Service Cloud Gratuit (2 minutes) - RECOMMANDÉ**

1. Allez sur **https://supabase.com**
2. Créez un compte gratuit
3. Cliquez sur **"New Project"**
4. Remplissez le formulaire (nom du projet, mot de passe)
5. Attendez 2 minutes que le projet soit créé
6. Allez dans **Settings** > **Database**
7. Copiez la **"Connection string"** (URI) - elle ressemble à :
   ```
   postgresql://postgres:[VOTRE-MOT-DE-PASSE]@db.xxxxx.supabase.co:5432/postgres
   ```
8. Ouvrez le fichier `backend/.env` dans un éditeur de texte
9. Remplacez la ligne `DATABASE_URL=...` par votre connection string

**Option B : PostgreSQL Local**

Si vous avez PostgreSQL installé localement, modifiez `backend/.env` :
```env
DATABASE_URL=postgresql://utilisateur:mot_de_passe@localhost:5432/ocft_tracker
```

### Étape 2 : Démarrer l'Application

Ouvrez PowerShell dans le dossier `backend` et exécutez :

```powershell
.\start-now.ps1
```

Ou manuellement :

```powershell
py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Étape 3 : Accéder à l'Application

Une fois le serveur démarré, ouvrez votre navigateur :

- **Application** : http://localhost:8000
- **Documentation API** : http://localhost:8000/api/docs
- **Dashboard** : http://localhost:8000/dashboard

## ⚠️ Si vous voyez une erreur PostgreSQL

Si le serveur démarre mais affiche une erreur de connexion PostgreSQL :

1. Vérifiez que `DATABASE_URL` dans `backend/.env` est correct
2. Vérifiez que PostgreSQL est accessible (service cloud ou local)
3. Les tables seront créées automatiquement au premier démarrage réussi

## 🛑 Arrêter l'Application

Appuyez sur **Ctrl+C** dans le terminal où le serveur tourne.

## 📚 Besoin d'aide ?

- Guide PostgreSQL détaillé : `backend/SETUP_POSTGRES.md`
- Guide de démarrage complet : `GUIDE_DEMARRAGE.md`


