#!/usr/bin/env python3
"""Initialisation de la base de données OCFT."""
import psycopg2
import sys
import os

def main():
    # Récupérer le mot de passe depuis l'environnement ou utiliser 'postgres' par défaut
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    try:
        # Se connecter en tant que postgres
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=postgres_password,
            database='postgres'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Créer la base de données
        try:
            cur.execute('CREATE DATABASE ocft_tracker;')
            print('[OK] Base de donnees ocft_tracker creee')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('[INFO] Base de donnees ocft_tracker existe deja')
            else:
                raise
        
        # Créer l'utilisateur
        try:
            cur.execute("CREATE USER ocft_user WITH PASSWORD 'ocft_secure_password_2026';")
            print('[OK] Utilisateur ocft_user cree')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('[INFO] Utilisateur ocft_user existe deja')
            else:
                raise
        
        # Donner les permissions
        cur.execute('ALTER DATABASE ocft_tracker OWNER TO ocft_user;')
        cur.execute('GRANT ALL PRIVILEGES ON DATABASE ocft_tracker TO ocft_user;')
        print('[OK] Permissions configurees')
        
        cur.close()
        conn.close()
        
        # Maintenant initialiser le schéma
        print('')
        print('Initialisation du schéma...')
        
        # Changer vers le répertoire backend
        backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
        os.chdir(backend_dir)
        sys.path.insert(0, backend_dir)
        
        os.environ['DATABASE_URL'] = 'postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker'
        os.environ['USE_POSTGRES'] = 'true'
        
        from app.database import init_db
        init_db()
        print('[OK] Schema initialise')
        
        return 0
        
    except psycopg2.OperationalError as e:
        if 'password authentication failed' in str(e).lower():
            print('[ERREUR] Erreur d\'authentification')
            print('Le mot de passe PostgreSQL par defaut n\'est pas "postgres"')
            print('')
            print('Solutions:')
            print('1. Utilisez le mot de passe de votre installation PostgreSQL')
            print('2. Ou configurez: $env:POSTGRES_PASSWORD = "votre_mot_de_passe"')
            return 1
        else:
            print(f'[ERREUR] {e}')
            import traceback
            traceback.print_exc()
            return 1
    except Exception as e:
        print(f'[ERREUR] {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
