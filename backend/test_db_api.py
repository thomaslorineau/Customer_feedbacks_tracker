"""Script pour tester la base de données et l'API"""
import sqlite3
from pathlib import Path
import requests
import json

# Test 1: Vérifier la base de données
print("=" * 60)
print("TEST 1: Vérification de la base de données")
print("=" * 60)

db_file = Path(__file__).parent / "data.db"
print(f"\nChemin de la base de données: {db_file}")
print(f"La base de données existe: {db_file.exists()}\n")

if db_file.exists():
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Compter les posts
    c.execute("SELECT COUNT(*) FROM posts")
    count = c.fetchone()[0]
    print(f"Nombre total de posts dans la BDD: {count}")
    
    # Récupérer quelques posts
    c.execute("SELECT id, source, author, content, created_at, sentiment_label FROM posts LIMIT 5")
    posts = c.fetchall()
    
    if posts:
        print("\n--- Premiers posts (échantillon) ---")
        for post in posts:
            print(f"\nID: {post[0]}")
            print(f"Source: {post[1]}")
            print(f"Auteur: {post[2]}")
            print(f"Contenu: {post[3][:100]}...")
            print(f"Date: {post[4]}")
            print(f"Sentiment: {post[5]}")
    else:
        print("\n⚠️ AUCUN POST trouvé dans la base de données!")
    
    # Vérifier les sources
    c.execute("SELECT source, COUNT(*) FROM posts GROUP BY source")
    sources = c.fetchall()
    if sources:
        print("\n--- Répartition par source ---")
        for source, count in sources:
            print(f"{source}: {count} posts")
    
    conn.close()
else:
    print("⚠️ LA BASE DE DONNÉES N'EXISTE PAS!")

# Test 2: Tester l'API
print("\n" + "=" * 60)
print("TEST 2: Vérification de l'API")
print("=" * 60)

api_url = "http://localhost:8000"

try:
    # Test posts endpoint (basé sur l'API frontend)
    print(f"\n1. Test endpoint posts: {api_url}/posts?limit=5")
    response = requests.get(f"{api_url}/posts?limit=5", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        posts_data = response.json()
        if posts_data:
            print(f"   ✓ Nombre de posts retournés: {len(posts_data)}")
            if len(posts_data) > 0:
                print(f"   ✓ Premier post: {posts_data[0].get('content', '')[:100]}...")
        else:
            print("   ⚠️ AUCUN POST retourné par l'API!")
    else:
        print(f"   ⚠️ Erreur: {response.text}")
    
    # Test API config
    print(f"\n2. Test endpoint config: {api_url}/api/config")
    response = requests.get(f"{api_url}/api/config", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        config = response.json()
        print(f"   ✓ Config récupérée: {config}")
    
    # Test recommended actions
    print(f"\n3. Test endpoint recommended-actions: {api_url}/api/recommended-actions")
    test_data = {
        "posts": [],
        "recent_posts": [],
        "stats": {"total_posts": 218},
        "max_actions": 3
    }
    response = requests.post(f"{api_url}/api/recommended-actions", json=test_data, timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Endpoint fonctionne")
    
    # Test pain points
    print(f"\n4. Test endpoint pain-points: {api_url}/api/pain-points?days=30&limit=5")
    response = requests.get(f"{api_url}/api/pain-points?days=30&limit=5", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        pain_points = response.json()
        print(f"   ✓ Nombre de pain points: {len(pain_points)}")
        if pain_points:
            for pp in pain_points[:3]:
                print(f"      - {pp.get('topic', 'N/A')}: {pp.get('frequency', 0)} mentions")
    
except requests.exceptions.ConnectionError:
    print("\n⚠️ ERREUR: Impossible de se connecter à l'API!")
    print("   Vérifiez que le serveur est bien lancé sur http://localhost:8000")
except Exception as e:
    print(f"\n⚠️ ERREUR lors du test de l'API: {e}")

print("\n" + "=" * 60)
print("FIN DES TESTS")
print("=" * 60)
