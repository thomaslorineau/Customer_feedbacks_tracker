"""
Script de test pour les notifications email.
Permet de créer un trigger de test, tester l'envoi, et le supprimer facilement.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

import asyncio
import httpx
import json

API_BASE = "http://localhost:8000"
TEST_EMAIL = "thomas.lorineau@ovhcloud.com"

async def main():
    print("=" * 60)
    print("Test des notifications email")
    print("=" * 60)
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Vérifier la configuration SMTP
        print("1. Vérification de la configuration SMTP...")
        try:
            res = await client.get(f"{API_BASE}/api/email/config")
            if res.status_code == 200:
                config = res.json()
                if config.get('smtp_configured'):
                    print(f"   ✅ SMTP configuré: {config.get('smtp_host')} (port {config.get('smtp_port')})")
                else:
                    print("   ❌ SMTP non configuré. Configurez SMTP_HOST, SMTP_USER, SMTP_PASSWORD dans .env")
                    return
            else:
                print(f"   ❌ Erreur: {res.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Erreur de connexion: {e}")
            print("   Assurez-vous que le serveur est démarré sur http://localhost:8000")
            return
        
        print()
        
        # 2. Créer un trigger de test
        print("2. Création d'un trigger de test...")
        test_trigger = {
            "name": "TEST - Posts négatifs (à supprimer)",
            "enabled": True,
            "conditions": {
                "sentiment": "negative",
                "relevance_score_min": 0.3,
                "sources": [],
                "language": "all"
            },
            "emails": [TEST_EMAIL],
            "cooldown_minutes": 5,  # Court pour les tests
            "max_posts_per_email": 5
        }
        
        try:
            res = await client.post(
                f"{API_BASE}/api/email/triggers",
                json=test_trigger
            )
            if res.status_code == 200:
                data = res.json()
                trigger_id = data.get('id')
                print(f"   ✅ Trigger créé avec ID: {trigger_id}")
                print(f"   📧 Email de test: {TEST_EMAIL}")
                print(f"   ⚠️  NOTE: Ce trigger sera automatiquement supprimé si vous utilisez delete_test_trigger.py")
            else:
                error = res.json().get('detail', 'Unknown error')
                print(f"   ❌ Erreur: {error}")
                # Essayer de trouver un trigger existant
                res2 = await client.get(f"{API_BASE}/api/email/triggers")
                if res2.status_code == 200:
                    data2 = res2.json()
                    existing = [t for t in data2.get('triggers', []) if 'TEST' in t.get('name', '')]
                    if existing:
                        trigger_id = existing[0]['id']
                        print(f"   ℹ️  Trigger de test existant trouvé (ID: {trigger_id})")
                    else:
                        return
                else:
                    return
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return
        
        print()
        
        # 3. Tester l'envoi d'email
        print("3. Test d'envoi d'email...")
        try:
            res = await client.post(f"{API_BASE}/api/email/test")
            if res.status_code == 200:
                data = res.json()
                print(f"   ✅ {data.get('message', 'Email envoyé avec succès')}")
            else:
                error = res.json().get('detail', 'Unknown error')
                print(f"   ❌ Erreur: {error}")
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
        
        print()
        
        # 4. Lister les triggers pour montrer comment supprimer
        print("4. Liste des triggers (pour vérification)...")
        try:
            res = await client.get(f"{API_BASE}/api/email/triggers")
            if res.status_code == 200:
                data = res.json()
                triggers = data.get('triggers', [])
                test_triggers = [t for t in triggers if 'TEST' in t.get('name', '')]
                
                if test_triggers:
                    print(f"   📋 {len(test_triggers)} trigger(s) de test trouvé(s):")
                    for trigger in test_triggers:
                        print(f"      - ID: {trigger['id']}, Nom: {trigger['name']}, Enabled: {trigger['enabled']}")
                else:
                    print("   ℹ️  Aucun trigger de test trouvé")
            else:
                print(f"   ⚠️  Erreur lors de la récupération: {res.status_code}")
        except Exception as e:
            print(f"   ⚠️  Erreur: {e}")
        
        print()
        print("=" * 60)
        if 'trigger_id' in locals():
            print("Pour supprimer le trigger de test:")
            print(f"  python backend/scripts/delete_test_trigger.py")
            print(f"  Ou via API: DELETE {API_BASE}/api/email/triggers/{trigger_id}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

