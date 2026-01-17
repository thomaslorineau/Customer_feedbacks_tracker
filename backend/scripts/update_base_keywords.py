"""
Script pour mettre à jour les keywords de base dans la base de données.
Supprime Soyoustart, RunAbove, Hubic et met à jour les produits OVHcloud.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set environment to staging by default
if 'ENVIRONMENT' not in os.environ:
    os.environ['ENVIRONMENT'] = 'staging'
if 'USE_DUCKDB' not in os.environ:
    os.environ['USE_DUCKDB'] = 'true'

from app import db
from app.config.keywords_base import (
    DEFAULT_BRAND_KEYWORDS,
    DEFAULT_PRODUCT_KEYWORDS,
    DEFAULT_PROBLEM_KEYWORDS,
    DEFAULT_LEADERSHIP_KEYWORDS
)

def update_base_keywords():
    """Met à jour les keywords de base avec les nouvelles valeurs."""
    print("🔄 Mise à jour des keywords de base...")
    
    keywords_by_category = {
        'brands': DEFAULT_BRAND_KEYWORDS,
        'products': DEFAULT_PRODUCT_KEYWORDS,
        'problems': DEFAULT_PROBLEM_KEYWORDS,
        'leadership': DEFAULT_LEADERSHIP_KEYWORDS
    }
    
    try:
        db.save_base_keywords(keywords_by_category)
        print(f"✅ Keywords de base mis à jour avec succès!")
        print(f"   - Brands: {len(DEFAULT_BRAND_KEYWORDS)} keywords")
        print(f"   - Products: {len(DEFAULT_PRODUCT_KEYWORDS)} keywords")
        print(f"   - Problems: {len(DEFAULT_PROBLEM_KEYWORDS)} keywords")
        print(f"   - Leadership: {len(DEFAULT_LEADERSHIP_KEYWORDS)} keywords")
        print(f"   Total: {sum(len(kw) for kw in keywords_by_category.values())} keywords")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        return False

if __name__ == '__main__':
    update_base_keywords()

