#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour tester le bouton "mark as answered".
"""
import requests
import sys

API_BASE = "http://127.0.0.1:8000"

def test_mark_answered():
    """Test le bouton mark as answered."""
    print("Test du bouton 'Mark as Answered'")
    print("=" * 60)
    
    # 1. Récupérer un post
    print("\n1. Récupération d'un post...")
    r = requests.get(f"{API_BASE}/posts?limit=1")
    if r.status_code != 200:
        print(f"❌ Erreur: {r.status_code}")
        return False
    
    posts = r.json()
    if not posts:
        print("ERROR: Aucun post trouve")
        return False
    
    post = posts[0]
    post_id = post['id']
    current_status = post.get('is_answered', 0)
    
    print(f"OK Post trouve: ID={post_id}, is_answered={current_status}")
    
    # 2. Tester le marquage comme answered
    print(f"\n2. Marquage du post {post_id} comme answered...")
    r = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=true")
    if r.status_code != 200:
        print(f"ERROR: {r.status_code} - {r.text}")
        return False
    
    result = r.json()
    print(f"OK Reponse: {result}")
    
    # 3. Vérifier que le statut a changé
    print(f"\n3. Verification du statut mis a jour...")
    r = requests.get(f"{API_BASE}/posts?limit=1000")
    if r.status_code != 200:
        print(f"ERROR: {r.status_code}")
        return False
    
    posts = r.json()
    updated_post = next((p for p in posts if p['id'] == post_id), None)
    if not updated_post:
        print(f"ERROR: Post {post_id} non trouve apres mise a jour")
        return False
    
    new_status = updated_post.get('is_answered', 0)
    print(f"OK Nouveau statut: is_answered={new_status}")
    
    if new_status != 1:
        print(f"ERROR: Le statut n'a pas ete mis a jour correctement (attendu: 1, obtenu: {new_status})")
        return False
    
    # 4. Tester le marquage comme not answered
    print(f"\n4. Marquage du post {post_id} comme not answered...")
    r = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=false")
    if r.status_code != 200:
        print(f"ERROR: {r.status_code} - {r.text}")
        return False
    
    result = r.json()
    print(f"OK Reponse: {result}")
    
    # 5. Vérifier que le statut a changé
    print(f"\n5. Verification du statut mis a jour...")
    r = requests.get(f"{API_BASE}/posts?limit=1000")
    if r.status_code != 200:
        print(f"ERROR: {r.status_code}")
        return False
    
    posts = r.json()
    updated_post = next((p for p in posts if p['id'] == post_id), None)
    if not updated_post:
        print(f"ERROR: Post {post_id} non trouve apres mise a jour")
        return False
    
    final_status = updated_post.get('is_answered', 0)
    print(f"OK Statut final: is_answered={final_status}")
    
    if final_status != 0:
        print(f"ERROR: Le statut n'a pas ete mis a jour correctement (attendu: 0, obtenu: {final_status})")
        return False
    
    print("\n" + "=" * 60)
    print("SUCCESS: Tous les tests sont passes ! Le bouton fonctionne correctement.")
    return True


if __name__ == '__main__':
    try:
        success = test_mark_answered()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

