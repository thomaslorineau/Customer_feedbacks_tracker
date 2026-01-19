"""
Script pour supprimer facilement le trigger de test.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import asyncio
import httpx

API_BASE = "http://localhost:8000"
TEST_EMAIL = "thomas.lorineau@ovhcloud.com"

async def main():
    print("=" * 60)
    print("Suppression du trigger de test")
    print("=" * 60)
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Lister les triggers de test
        print("1. Recherche des triggers de test...")
        try:
            res = await client.get(f"{API_BASE}/api/email/triggers")
            if res.status_code != 200:
                print(f"   ❌ Erreur: {res.status_code}")
                return
            
            data = res.json()
            triggers = data.get('triggers', [])
            
            # Trouver les triggers de test (qui contiennent TEST dans le nom ou l'email de test)
            test_triggers = []
            for trigger in triggers:
                name = trigger.get('name', '')
                emails = trigger.get('emails', '')
                if isinstance(emails, str):
                    try:
                        import json
                        emails = json.loads(emails)
                    except:
                        emails = []
                
                if 'TEST' in name.upper() or TEST_EMAIL in str(emails):
                    test_triggers.append(trigger)
            
            if not test_triggers:
                print("   ℹ️  Aucun trigger de test trouvé")
                return
            
            print(f"   📋 {len(test_triggers)} trigger(s) de test trouvé(s):")
            for i, trigger in enumerate(test_triggers, 1):
                print(f"      {i}. ID: {trigger['id']}, Nom: {trigger['name']}")
            
            print()
            
            # 2. Supprimer tous les triggers de test
            print("2. Suppression des triggers de test...")
            deleted = 0
            for trigger in test_triggers:
                trigger_id = trigger['id']
                try:
                    res = await client.delete(f"{API_BASE}/api/email/triggers/{trigger_id}")
                    if res.status_code == 200:
                        print(f"   ✅ Trigger {trigger_id} supprimé: {trigger['name']}")
                        deleted += 1
                    else:
                        error = res.json().get('detail', 'Unknown error')
                        print(f"   ❌ Erreur pour trigger {trigger_id}: {error}")
                except Exception as e:
                    print(f"   ❌ Erreur pour trigger {trigger_id}: {e}")
            
            print()
            print(f"✅ {deleted}/{len(test_triggers)} trigger(s) supprimé(s)")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            print("   Assurez-vous que le serveur est démarré sur http://localhost:8000")
        
        print()
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

