# 🔧 Résoudre le conflit de merge

## Problème
```
error: Your local changes to the following files would be overwritten by merge:
        scripts/install/check_access.sh
        update.sh
```

## Solutions rapides

### Option 1: Stasher (recommandé)
```bash
git stash
git pull origin master
git stash pop
```

### Option 2: Écraser les modifications locales
```bash
git checkout -- scripts/install/check_access.sh update.sh
git pull origin master
```

### Option 3: Commiter vos modifications
```bash
git add scripts/install/check_access.sh update.sh
git commit -m "Local changes"
git pull origin master
```

## Après le pull

```bash
# Installer DuckDB
source venv/bin/activate
pip install duckdb==0.10.0

# Configurer l'environnement
export ENVIRONMENT=production
export USE_DUCKDB=true

# Redémarrer
bash scripts/app/restart.sh
```


