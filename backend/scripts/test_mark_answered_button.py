#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour tester le bouton "mark as answered".
"""
import sys
import requests
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

API_BASE = "http://127.0.0.1:8000"


def test_mark_answered():
    """Test le bouton mark as answered."""
    print("Test du bouton 'mark as answered'...\n")
    
    # Récupérer un post pour tester
    try:
        r = requests.get(f"{API_BASE}/posts?limit=1")
        if r.status_code != 200:
            print(f"[ERROR] Impossible de recuperer les posts: {r.status_code}")
            return False
        
        posts = r.json()
        if not posts:
            print("[WARNING] Aucun post trouve dans la base de donnees")
            return False
        
        post = posts[0]
        post_id = post['id']
        initial_status = post.get('is_answered', 0)
        
        print(f"Post ID: {post_id}")
        print(f"Statut initial: {'answered' if initial_status == 1 else 'not answered'}")
        
        # Tester marquer comme answered
        print(f"\n1. Test: Marquer comme answered...")
        r1 = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=true")
        if r1.status_code == 200:
            result1 = r1.json()
            print(f"   [OK] Reponse: {result1}")
            
            # Vérifier le statut
            r_check = requests.get(f"{API_BASE}/posts/{post_id}")
            if r_check.status_code == 200:
                post_after = r_check.json()
                new_status = post_after.get('is_answered', 0)
                print(f"   Statut apres: {'answered' if new_status == 1 else 'not answered'}")
                if new_status == 1:
                    print(f"   [OK] Le post est maintenant marque comme answered")
                else:
                    print(f"   [ERROR] Le post n'est pas marque comme answered!")
                    return False
            else:
                print(f"   [ERROR] Impossible de verifier le statut: {r_check.status_code}")
                return False
        else:
            print(f"   [ERROR] Erreur lors du marquage: {r1.status_code} - {r1.text}")
            return False
        
        # Tester marquer comme not answered
        print(f"\n2. Test: Marquer comme not answered...")
        r2 = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=false")
        if r2.status_code == 200:
            result2 = r2.json()
            print(f"   [OK] Reponse: {result2}")
            
            # Vérifier le statut
            r_check2 = requests.get(f"{API_BASE}/posts/{post_id}")
            if r_check2.status_code == 200:
                post_after2 = r_check2.json()
                new_status2 = post_after2.get('is_answered', 0)
                print(f"   Statut apres: {'answered' if new_status2 == 1 else 'not answered'}")
                if new_status2 == 0:
                    print(f"   [OK] Le post est maintenant marque comme not answered")
                else:
                    print(f"   [ERROR] Le post n'est pas marque comme not answered!")
                    return False
            else:
                print(f"   [ERROR] Impossible de verifier le statut: {r_check2.status_code}")
                return False
        else:
            print(f"   [ERROR] Erreur lors du marquage: {r2.status_code} - {r2.text}")
            return False
        
        # Restaurer le statut initial
        print(f"\n3. Restauration du statut initial...")
        restore_value = 'true' if initial_status == 1 else 'false'
        r3 = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered={restore_value}")
        if r3.status_code == 200:
            print(f"   [OK] Statut initial restaure")
        else:
            print(f"   [WARNING] Impossible de restaurer le statut initial")
        
        print(f"\n[SUCCESS] Tous les tests du bouton 'mark as answered' ont reussi !")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Impossible de se connecter au serveur. Assurez-vous qu'il est demarre sur {API_BASE}")
        return False
    except Exception as e:
        print(f"[ERROR] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_mark_answered()
    sys.exit(0 if success else 1)

