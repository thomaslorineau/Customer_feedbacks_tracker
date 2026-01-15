"""Script pour créer un rapport de diagnostic de l'application"""
import sqlite3
from pathlib import Path
import json
from datetime import datetime

print("=" * 80)
print("RAPPORT DE DIAGNOSTIC - OVH Complaints Tracker")
print("=" * 80)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
db_file = Path(__file__).parent / "data.db"

print("1. BASE DE DONNÉES")
print("-" * 80)
if db_file.exists():
    print(f"✓ Fichier BDD existe: {db_file}")
    print(f"  Taille: {db_file.stat().st_size / 1024:.2f} KB")
    
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    
    # Stats globales
    c.execute("SELECT COUNT(*) FROM posts")
    total = c.fetchone()[0]
    print(f"  Total posts: {total}")
    
    # Par source
    print("\n  Répartition par source:")
    c.execute("SELECT source, COUNT(*) as count FROM posts GROUP BY source ORDER BY count DESC")
    for source, count in c.fetchall():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"    • {source}: {count} ({percentage:.1f}%)")
    
    # Par sentiment
    print("\n  Répartition par sentiment:")
    c.execute("SELECT sentiment_label, COUNT(*) as count FROM posts GROUP BY sentiment_label ORDER BY count DESC")
    for sentiment, count in c.fetchall():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"    • {sentiment or 'non analysé'}: {count} ({percentage:.1f}%)")
    
    # Par langue
    print("\n  Répartition par langue:")
    c.execute("SELECT language, COUNT(*) as count FROM posts GROUP BY language ORDER BY count DESC LIMIT 5")
    for lang, count in c.fetchall():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"    • {lang}: {count} ({percentage:.1f}%)")
    
    # Dates
    c.execute("SELECT MIN(created_at), MAX(created_at) FROM posts")
    min_date, max_date = c.fetchone()
    print(f"\n  Période: {min_date} → {max_date}")
    
    # Posts récents
    c.execute("SELECT COUNT(*) FROM posts WHERE created_at >= date('now', '-7 days')")
    recent = c.fetchone()[0]
    print(f"  Posts des 7 derniers jours: {recent}")
    
    conn.close()
else:
    print("✗ BASE DE DONNÉES INTROUVABLE")

print("\n2. API ENDPOINTS")
print("-" * 80)

import requests

endpoints = [
    ("GET", "/posts?limit=1", "Récupération posts"),
    ("GET", "/api/config", "Configuration API"),
    ("GET", "/api/pain-points?days=30&limit=5", "Pain points"),
    ("GET", "/api/product-opportunities", "Opportunités produits"),
    ("GET", "/api/improvements-summary", "Résumé améliorations"),
]

api_base = "http://localhost:8000"
api_ok_count = 0

for method, endpoint, description in endpoints:
    try:
        if method == "GET":
            response = requests.get(f"{api_base}{endpoint}", timeout=3)
        status = response.status_code
        if status == 200:
            print(f"✓ {description:30} [{endpoint}]")
            api_ok_count += 1
        else:
            print(f"⚠ {description:30} [{endpoint}] - Status {status}")
    except requests.exceptions.ConnectionError:
        print(f"✗ {description:30} [{endpoint}] - Connexion refusée")
    except Exception as e:
        print(f"✗ {description:30} [{endpoint}] - {str(e)[:50]}")

print(f"\nRésultat: {api_ok_count}/{len(endpoints)} endpoints OK")

print("\n3. CONFIGURATION")
print("-" * 80)

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print("✓ Fichier .env existe")
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if 'KEY' in key or 'TOKEN' in key:
                    if value and value != 'your_openai_api_key_here':
                        print(f"  • {key}: configuré ({len(value)} chars)")
                    else:
                        print(f"  ⚠ {key}: NON configuré")
                else:
                    print(f"  • {key}: {value}")
else:
    print("✗ Fichier .env introuvable")

print("\n4. DIAGNOSTIC FINAL")
print("-" * 80)

issues = []
warnings = []
ok_items = []

# Vérifications
if db_file.exists() and total > 0:
    ok_items.append(f"BDD opérationnelle avec {total} posts")
else:
    issues.append("BDD vide ou inexistante")

if api_ok_count >= len(endpoints) - 1:
    ok_items.append(f"API fonctionne ({api_ok_count}/{len(endpoints)} endpoints)")
elif api_ok_count > 0:
    warnings.append(f"Certains endpoints ne répondent pas ({api_ok_count}/{len(endpoints)})")
else:
    issues.append("API ne répond pas - serveur arrêté ?")

if recent == 0:
    warnings.append("Aucun post récent (7 derniers jours)")

print("\n✓ OK:")
for item in ok_items:
    print(f"  • {item}")

if warnings:
    print("\n⚠ AVERTISSEMENTS:")
    for item in warnings:
        print(f"  • {item}")

if issues:
    print("\n✗ PROBLÈMES:")
    for item in issues:
        print(f"  • {item}")
else:
    print("\n✓ Aucun problème critique détecté")

print("\n" + "=" * 80)
print("FIN DU RAPPORT")
print("=" * 80)
