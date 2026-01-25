#!/bin/bash
# ============================================
# Docker Entrypoint avec Migration Auto
# ============================================

# Ne pas sortir immédiatement en cas d'erreur pour la migration
# (on veut continuer même si la migration échoue)
set +e

echo "=========================================="
echo "Docker Entrypoint - VibeCoding API"
echo "=========================================="
echo ""

# Vérifier si DATABASE_URL est configuré
if [ -z "$DATABASE_URL" ]; then
    echo "ERREUR: DATABASE_URL n'est pas configuré"
    exit 1
fi

# Vérifier si on doit migrer depuis DuckDB
DUCKDB_FILE="/tmp/data.duckdb"
MIGRATE_FLAG="/app/.migration_done"

# Si le fichier DuckDB existe et que la migration n'a pas été faite
if [ -f "$DUCKDB_FILE" ] && [ ! -f "$MIGRATE_FLAG" ]; then
    echo "=========================================="
    echo "Migration automatique DuckDB -> PostgreSQL"
    echo "=========================================="
    echo ""
    echo "Fichier DuckDB détecté: $DUCKDB_FILE"
    echo "Vérification de PostgreSQL..."
    
    # Attendre que PostgreSQL soit prêt (augmenter le délai car depends_on peut ne pas suffire)
    MAX_ATTEMPTS=60
    ATTEMPT=0
    
    # Extraire les infos de connexion depuis DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    
    if [ -z "$DB_HOST" ]; then
        DB_HOST="postgres"
    fi
    if [ -z "$DB_PORT" ]; then
        DB_PORT="5432"
    fi
    
    echo "Attente de PostgreSQL sur $DB_HOST:$DB_PORT..."
    
    # Utiliser pg_isready si disponible, sinon psycopg2
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        # Essayer d'abord avec pg_isready (plus rapide)
        if command -v pg_isready >/dev/null 2>&1; then
            if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
                # Vérifier aussi la connexion réelle avec psycopg2
                if python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=2)
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
                    echo "✓ PostgreSQL est prêt"
                    break
                fi
            fi
        else
            # Fallback sur psycopg2 uniquement
            if python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=2)
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
                echo "✓ PostgreSQL est prêt"
                break
            fi
        fi
        ATTEMPT=$((ATTEMPT + 1))
        if [ $((ATTEMPT % 5)) -eq 0 ]; then
            echo "  Tentative $ATTEMPT/$MAX_ATTEMPTS... (attente de PostgreSQL)"
        fi
        sleep 2
    done
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo ""
        echo "⚠️  PostgreSQL n'est pas prêt après $MAX_ATTEMPTS tentatives (2 minutes), migration reportée"
        echo "   La migration sera ignorée pour ce démarrage"
        echo "   L'API va démarrer quand même, mais sans migration automatique"
        echo "   Pour migrer manuellement plus tard:"
        echo "     docker-compose exec api python scripts/migrate_to_postgres.py --duckdb /tmp/data.duckdb --postgres \$DATABASE_URL"
        echo ""
        # Ne pas créer le flag pour permettre une nouvelle tentative au prochain démarrage
        # Mais continuer quand même le démarrage de l'API
    else
        # Vérifier si des données existent déjà dans PostgreSQL
        echo "Vérification des données existantes..."
        EXISTING_POSTS=$(python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM posts')
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(count)
except Exception as e:
    print('0')
" 2>/dev/null || echo "0")
        
        if [ "$EXISTING_POSTS" = "0" ] || [ -z "$EXISTING_POSTS" ]; then
            echo "Aucune donnée dans PostgreSQL, lancement de la migration..."
            echo ""
            
            # Exécuter la migration
            python scripts/migrate_to_postgres.py \
                --duckdb "$DUCKDB_FILE" \
                --postgres "$DATABASE_URL"
            
            MIGRATION_EXIT=$?
            
            if [ $MIGRATION_EXIT -eq 0 ]; then
                echo ""
                echo "✓ Migration réussie!"
                # Marquer la migration comme faite
                touch "$MIGRATE_FLAG"
            else
                echo ""
                echo "⚠️  Migration échouée (code: $MIGRATION_EXIT)"
                echo "   Vous pouvez réessayer manuellement"
            fi
        else
            echo "✓ Des données existent déjà dans PostgreSQL ($EXISTING_POSTS posts)"
            echo "  Migration ignorée pour éviter les doublons"
            echo "  Pour forcer la migration, supprimez le fichier: $MIGRATE_FLAG"
            # Marquer quand même pour éviter de réessayer
            touch "$MIGRATE_FLAG"
        fi
    fi
    
    echo ""
fi

# Réactiver set -e pour le reste du script
set -e

# Initialiser la base de données (créer les tables si nécessaire)
echo "Initialisation de la base de données..."
python -c "
import os
import sys
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', '')
os.environ['USE_POSTGRES'] = 'true'

try:
    from app.database import init_db
    init_db()
    print('✓ Base de données initialisée')
except Exception as e:
    print(f'⚠️  Erreur lors de l\'initialisation: {e}')
    # Ne pas bloquer le démarrage si init_db échoue
    import traceback
    traceback.print_exc()
" || echo "⚠️  Erreur lors de l'initialisation (non bloquant)"

echo ""
echo "=========================================="
echo "Démarrage de l'API..."
echo "=========================================="
echo ""

# Exécuter la commande passée en argument (CMD du Dockerfile)
exec "$@"
