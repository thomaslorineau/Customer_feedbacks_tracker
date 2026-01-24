#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test direct de update_post_answered_status."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import db

# Test avec un post qui existe
post_id = 175
print(f"Test update_post_answered_status pour post {post_id}...")

# Vérifier que le post existe
conn, _ = db.get_db_connection()
c = conn.cursor()
c.execute('SELECT id, source, is_answered FROM posts WHERE id = ?', (post_id,))
row = c.fetchone()
conn.close()

if row:
    print(f"Post trouve: id={row[0]}, source={row[1]}, is_answered={row[2]}")
    
    # Tester la mise à jour
    print("\nTest 1: Marquer comme answered...")
    result1 = db.update_post_answered_status(post_id, True, method='manual')
    print(f"Resultat: {result1}")
    
    # Vérifier
    conn2, _ = db.get_db_connection()
    c2 = conn2.cursor()
    c2.execute('SELECT is_answered FROM posts WHERE id = ?', (post_id,))
    row2 = c2.fetchone()
    conn2.close()
    print(f"Statut apres: {row2[0] if row2 else 'None'}")
    
    print("\nTest 2: Marquer comme not answered...")
    result2 = db.update_post_answered_status(post_id, False, method='manual')
    print(f"Resultat: {result2}")
    
    # Vérifier
    conn3, _ = db.get_db_connection()
    c3 = conn3.cursor()
    c3.execute('SELECT is_answered FROM posts WHERE id = ?', (post_id,))
    row3 = c3.fetchone()
    conn3.close()
    print(f"Statut apres: {row3[0] if row3 else 'None'}")
else:
    print(f"Post {post_id} non trouve!")

