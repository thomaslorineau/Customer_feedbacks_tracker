# 🚀 Mise à jour rapide sur Linux

## Commandes simples (copier-coller)

```bash
# 1. Aller dans le projet
cd ~/projects/Customer_feedbacks_tracker

# 2. Mettre à jour le code
git pull origin master

# 3. Activer l'environnement virtuel
source venv/bin/activate

# 4. Installer DuckDB
pip install duckdb==0.10.0

# 5. Vérifier l'installation
python -c "import duckdb; print(duckdb.__version__)"

# 6. Configurer les variables d'environnement (dans votre script de démarrage ou .env)
export ENVIRONMENT=production
export USE_DUCKDB=true

# 7. Redémarrer l'application
bash scripts/app/restart.sh
```

## Alternative : Utiliser le script d'update

```bash
cd ~/projects/Customer_feedbacks_tracker
bash update.sh
```

Puis installer DuckDB manuellement :
```bash
source venv/bin/activate
pip install duckdb==0.10.0
```

## Vérification finale

```bash
# Vérifier que DuckDB est installé
python -c "import duckdb; print(duckdb.__version__)"

# Vérifier que l'app utilise DuckDB
export ENVIRONMENT=production
export USE_DUCKDB=true
python3 -c "
import os
import sys
os.environ['ENVIRONMENT'] = 'production'
os.environ['USE_DUCKDB'] = 'true'
sys.path.insert(0, 'backend')
from app.db import get_db_connection
conn, is_duckdb = get_db_connection()
print('DuckDB' if is_duckdb else 'SQLite')
conn.close()
"
```

