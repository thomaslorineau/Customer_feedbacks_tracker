"""
Migration script to add country detection to existing posts.
Run this once to backfill country data for existing posts.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db
from app.analysis import country_detection

def migrate_posts():
    """Add country detection to all posts that don't have a country."""
    print("Starting migration: Adding country detection to existing posts...")
    print("=" * 60)
    
    # Get all posts
    posts = db.get_posts(limit=100000, offset=0)
    print(f"Found {len(posts)} posts to process")
    
    updated = 0
    skipped = 0
    no_country_detected = 0
    
    import sqlite3
    conn = sqlite3.connect(db.DB_FILE)
    c = conn.cursor()
    
    for i, post in enumerate(posts, 1):
        # Skip if country already exists
        if post.get('country'):
            skipped += 1
            continue
        
        # Detect country
        country = country_detection.detect_country_from_post(post)
        
        if country:
            # Update post with country
            c.execute('UPDATE posts SET country = ? WHERE id = ?', (country, post['id']))
            updated += 1
            
            if updated % 100 == 0:
                print(f"  Progress: {i}/{len(posts)} - Updated {updated} posts...")
                conn.commit()
        else:
            no_country_detected += 1
    
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print(f"Migration complete!")
    print(f"  ✅ Updated: {updated} posts (country detected)")
    print(f"  ⏭️  Skipped: {skipped} posts (already had country)")
    print(f"  ❌ No country: {no_country_detected} posts (could not detect)")
    print(f"  📊 Total: {len(posts)} posts")
    print("=" * 60)

if __name__ == '__main__':
    migrate_posts()

