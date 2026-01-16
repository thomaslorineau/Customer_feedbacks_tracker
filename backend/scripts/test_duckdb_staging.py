#!/usr/bin/env python3
"""
Script de test de DuckDB en staging
Teste toutes les fonctionnalités avec DuckDB activé
"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# Configurer l'environnement staging avec DuckDB
os.environ['ENVIRONMENT'] = 'staging'
os.environ['USE_DUCKDB'] = 'true'

def test_db_connection():
    """Test de connexion à la base."""
    print("1. Test de connexion...", end=" ")
    try:
        from app.db import get_db_connection
        conn, is_duckdb = get_db_connection()
        if is_duckdb:
            print("✓ DuckDB")
        else:
            print("⚠️ SQLite (fallback)")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False

def test_get_posts():
    """Test de récupération des posts."""
    print("2. Test get_posts()...", end=" ")
    try:
        from app.db import get_posts
        posts = get_posts(limit=10)
        print(f"✓ {len(posts)} posts")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False

def test_insert_post():
    """Test d'insertion d'un post."""
    print("3. Test insert_post()...", end=" ")
    try:
        from app.db import insert_post
        test_post = {
            'source': 'test',
            'content': 'Test post for DuckDB',
            'author': 'test_user',
            'url': 'https://test.com',
            'created_at': '2026-01-16T12:00:00',
            'sentiment_score': 0.5,
            'sentiment_label': 'neutral',
            'language': 'en'
        }
        insert_post(test_post)
        print("✓")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False

def test_jobs():
    """Test des fonctions jobs."""
    print("4. Test jobs...", end=" ")
    try:
        from app.db import create_job_record, get_job_record, update_job_progress
        job_id = 'test_job_duckdb'
        create_job_record(job_id)
        job = get_job_record(job_id)
        if job and job['id'] == job_id:
            update_job_progress(job_id, 10, 5)
            print("✓")
            return True
        else:
            print("❌ Job not found")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False

def test_saved_queries():
    """Test des saved queries."""
    print("5. Test saved_queries()...", end=" ")
    try:
        from app.db import save_queries, get_saved_queries
        save_queries(['test1', 'test2'])
        queries = get_saved_queries()
        if len(queries) >= 2:
            print("✓")
            return True
        else:
            print("❌ Queries not saved")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False

def test_logs():
    """Test des logs."""
    print("6. Test scraping_logs()...", end=" ")
    try:
        from app.db import add_scraping_log, get_scraping_logs
        add_scraping_log('test', 'info', 'Test log')
        logs = get_scraping_logs(limit=5)
        print(f"✓ {len(logs)} logs")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False

def main():
    """Point d'entrée principal."""
    print("=" * 70)
    print("Tests DuckDB en Staging")
    print("=" * 70)
    print()
    
    tests = [
        test_db_connection,
        test_get_posts,
        test_insert_post,
        test_jobs,
        test_saved_queries,
        test_logs
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print()
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("✅ Tous les tests sont passés!")
        return 0
    else:
        print("❌ Certains tests ont échoué")
        return 1

if __name__ == '__main__':
    sys.exit(main())

