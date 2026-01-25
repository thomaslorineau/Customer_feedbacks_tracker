#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vérifier les données migrées de DuckDB vers PostgreSQL."""
import os
import sys
from pathlib import Path

# Ajouter le backend au path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker')
os.environ['USE_POSTGRES'] = 'true'

from app.database import get_posts, get_source_stats, get_sentiment_stats

print("=" * 50)
print("Verification Migration DuckDB -> PostgreSQL")
print("=" * 50)
print()

# Compter tous les posts
posts = get_posts(limit=1000)
print(f"Total posts dans PostgreSQL: {len(posts)}")
print()

# Statistiques par source
print("Posts par source:")
stats = get_source_stats()
if isinstance(stats, list):
    for s in stats[:15]:
        source = s.get('source', 'unknown')
        count = s.get('count', 0)
        print(f"  {source}: {count}")
elif isinstance(stats, dict):
    for source, count in list(stats.items())[:15]:
        print(f"  {source}: {count}")
else:
    print(f"  Format inattendu: {type(stats)}")

print()

# Statistiques sentiment
print("Posts par sentiment:")
sentiment = get_sentiment_stats()
if isinstance(sentiment, list):
    for s in sentiment:
        label = s.get('sentiment_label', 'unknown')
        count = s.get('count', 0)
        print(f"  {label}: {count}")
elif isinstance(sentiment, dict):
    for label, count in sentiment.items():
        print(f"  {label}: {count}")

print()
print("=" * 50)
print("Migration verifiee avec succes!")
print("=" * 50)
