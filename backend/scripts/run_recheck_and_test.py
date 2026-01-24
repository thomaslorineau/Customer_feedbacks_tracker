#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour lancer la re-verification et tester le bouton mark as answered.
"""
import requests
import sys
import time

API_BASE = "http://127.0.0.1:8000"

def test_mark_answered():
    """Test le bouton mark as answered."""
    print("\n" + "="*60)
    print("TEST DU BOUTON MARK AS ANSWERED")
    print("="*60)
    
    # 1. Récupérer un post
    print("\n1. Recuperation d'un post...")
    r = requests.get(f"{API_BASE}/posts?limit=1")
    if r.status_code != 200:
        print(f"ERROR: {r.status_code}")
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
    try:
        r = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=true", timeout=10)
        if r.status_code != 200:
            print(f"ERROR: {r.status_code} - {r.text[:200]}")
            return False
        
        result = r.json()
        print(f"OK Reponse: {result}")
        
        # Attendre un peu pour que la DB se mette à jour
        time.sleep(1)
        
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
            print(f"ERROR: Le statut n'a pas ete mis a jour (attendu: 1, obtenu: {new_status})")
            return False
        
        # 4. Tester le marquage comme not answered
        print(f"\n4. Marquage du post {post_id} comme not answered...")
        r = requests.post(f"{API_BASE}/posts/{post_id}/mark-answered?answered=false", timeout=10)
        if r.status_code != 200:
            print(f"ERROR: {r.status_code} - {r.text[:200]}")
            return False
        
        result = r.json()
        print(f"OK Reponse: {result}")
        
        # Attendre un peu
        time.sleep(1)
        
        # 5. Vérifier que le statut a changé
        print(f"\n5. Verification du statut final...")
        r = requests.get(f"{API_BASE}/posts?limit=1000")
        if r.status_code != 200:
            print(f"ERROR: {r.status_code}")
            return False
        
        posts = r.json()
        updated_post = next((p for p in posts if p['id'] == post_id), None)
        if not updated_post:
            print(f"ERROR: Post {post_id} non trouve")
            return False
        
        final_status = updated_post.get('is_answered', 0)
        print(f"OK Statut final: is_answered={final_status}")
        
        if final_status != 0:
            print(f"ERROR: Le statut n'a pas ete mis a jour (attendu: 0, obtenu: {final_status})")
            return False
        
        print("\n" + "="*60)
        print("SUCCESS: Tous les tests sont passes !")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def recheck_all_answered():
    """Re-verifie le statut answered de tous les posts."""
    print("\n" + "="*60)
    print("RE-VERIFICATION DU STATUT ANSWERED")
    print("="*60)
    
    print("\nAppel de l'endpoint de re-verification...")
    print("ATTENTION: Cela peut prendre plusieurs minutes...")
    
    try:
        r = requests.post(
            f"{API_BASE}/admin/recheck-answered-status",
            json={'limit': None},
            headers={'Content-Type': 'application/json'},
            timeout=600
        )
        
        if r.status_code != 200:
            print(f"ERROR: {r.status_code}")
            print(f"Reponse: {r.text[:500]}")
            return False
        
        result = r.json()
        
        print("\n" + "="*60)
        print("RESULTATS")
        print("="*60)
        print(f"  Total posts verifies: {result.get('total_posts', 0)}")
        print(f"  Posts mis a jour: {result.get('updated_count', 0)}")
        print(f"  Erreurs: {result.get('error_count', 0)}")
        print(f"  Ignores: {result.get('skipped_count', 0)}")
        print(f"  Message: {result.get('message', 'N/A')}")
        
        if result.get('success'):
            print("\nSUCCESS: Re-verification terminee avec succes !")
            return True
        else:
            print("\nWARNING: Re-verification terminee avec des erreurs")
            return False
            
    except requests.exceptions.Timeout:
        print("\nERROR: Timeout - La re-verification prend trop de temps")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("SCRIPT DE RE-VERIFICATION ET TEST")
    print("="*60)
    
    # 1. Tester le bouton
    test_success = test_mark_answered()
    
    # 2. Lancer la re-verification
    print("\n\nVoulez-vous lancer la re-verification de tous les posts maintenant ?")
    print("(Cela peut prendre plusieurs minutes)")
    print("Appuyez sur Entree pour continuer ou Ctrl+C pour annuler...")
    try:
        input()
        recheck_success = recheck_all_answered()
    except KeyboardInterrupt:
        print("\nAnnule par l'utilisateur")
        recheck_success = None
    
    # Résumé
    print("\n" + "="*60)
    print("RESUME")
    print("="*60)
    print(f"  Test bouton mark as answered: {'SUCCESS' if test_success else 'FAILED'}")
    if recheck_success is not None:
        print(f"  Re-verification: {'SUCCESS' if recheck_success else 'FAILED'}")
    else:
        print(f"  Re-verification: SKIPPED")
    
    sys.exit(0 if test_success else 1)

