#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour re-vérifier immédiatement le statut answered de tous les posts.
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import db
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def recheck_all_answered():
    """Re-vérifie le statut answered de tous les posts."""
    logger.info("🔄 Starting re-check of answered status for all posts...")
    
    try:
        # Vérifier tous les posts (pas de limite)
        result = await db.recheck_posts_answered_status(limit=None, delay_between_requests=0.5)
        
        if result.get('success'):
            updated = result.get('updated_count', 0)
            errors = result.get('error_count', 0)
            skipped = result.get('skipped_count', 0)
            total = result.get('total_posts', 0)
            
            logger.info(f"\n📊 Results:")
            logger.info(f"  Total posts checked: {total}")
            logger.info(f"  Posts updated: {updated}")
            logger.info(f"  Errors: {errors}")
            logger.info(f"  Skipped: {skipped}")
            
            return result
        else:
            logger.error(f"❌ Re-check failed: {result.get('message', 'Unknown error')}")
            return result
            
    except Exception as e:
        logger.error(f"❌ Error during re-check: {e}", exc_info=True)
        return {
            'success': False,
            'message': str(e)
        }


if __name__ == '__main__':
    result = asyncio.run(recheck_all_answered())
    if result.get('success'):
        print(f"\n✅ Re-check completed successfully!")
        print(f"   Updated: {result.get('updated_count', 0)} posts")
    else:
        print(f"\n❌ Re-check failed: {result.get('message', 'Unknown error')}")
        sys.exit(1)
