# 🗄️ Installation PostgreSQL pour OCFT

Le script `start-localhost.ps1` nécessite PostgreSQL. Voici comment l'installer.

## Option 1 : Scoop (Recommandé - Le plus simple)

### Étape 1 : Installer Scoop (si pas déjà installé)

Ouvrez PowerShell en administrateur et exécutez :

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
```

### Étape 2 : Installer PostgreSQL

```powershell
scoop install postgresql
```

### Étape 3 : Initialiser PostgreSQL

```powershell
# Créer le répertoire de données
mkdir C:\Users\$env:USERNAME\scoop\apps\postgresql\current\data

# Initialiser la base de données
C:\Users\$env:USERNAME\scoop\apps\postgresql\current\bin\initdb.exe -D C:\Users\$env:USERNAME\scoop\apps\postgresql\current\data -U postgres -A password -E UTF8
```

### Étape 4 : Démarrage

Le script `start-localhost.ps1` démarrera automatiquement PostgreSQL.

## Option 2 : Installateur Windows

1. Téléchargez PostgreSQL depuis : https://www.postgresql.org/download/windows/
2. Installez PostgreSQL (notez le mot de passe de l'utilisateur `postgres`)
3. Le script détectera automatiquement PostgreSQL dans `C:\Program Files\PostgreSQL`

## Option 3 : Service Cloud Gratuit (Pas besoin d'installer PostgreSQL)

Si vous préférez utiliser un service cloud gratuit (Supabase/Neon) :

1. Allez sur https://supabase.com
2. Créez un compte et un projet
3. Récupérez la connection string
4. Modifiez `backend/.env` avec votre `DATABASE_URL`
5. Utilisez `backend/start-now.ps1` au lieu de `start-localhost.ps1`

## Vérification

Après installation, vérifiez que PostgreSQL fonctionne :

```powershell
# Trouver pg_ctl
Get-Command pg_ctl

# Ou tester la connexion
psql -U postgres -c "SELECT version();"
```

## Note

Le script `start-localhost.ps1` détecte automatiquement PostgreSQL dans :
- Scoop : `C:\Users\$env:USERNAME\scoop\apps\postgresql\current\bin`
- Program Files : `C:\Program Files\PostgreSQL\*\bin`
- PATH : Si PostgreSQL est dans votre PATH

