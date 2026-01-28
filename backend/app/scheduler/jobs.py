"""Scheduled background jobs."""
import time
import logging
import sys
from pathlib import Path

from .. import database as db
from ..keywords import keywords_base
from ..routers.scraping import _run_scrape_for_source

logger = logging.getLogger(__name__)

# Backup functions are now implemented directly using pg_dump


def auto_scrape_job():
    """Scheduled job to scrape all sources automatically.

    Uses base keywords (fixed) + user keywords (saved queries) from the DB.
    Adds small sleeps to avoid hammering third-party endpoints (basic throttling).
    Verifies relevance score and filters non-OVH posts.
    Uses keyword expansion for better coverage (same as manual scraping).
    Reuses existing scraping logic to avoid code duplication.
    """
    logger.info("🔄 Running scheduled scrape...")

    # Get user keywords (saved queries)
    user_keywords = db.get_saved_queries()
    
    # Combine base keywords (fixed) + user keywords
    all_keywords = keywords_base.get_all_keywords(user_keywords)
    
    if not all_keywords:
        # Fallback si vraiment rien
        all_keywords = keywords_base.get_all_base_keywords()
    
    queries = all_keywords

    # Configuration pour le scraping automatique
    per_query_limit = 50  # Augmenté pour meilleure couverture
    use_keyword_expansion = True  # Activer l'expansion (comme scraping manuel)
    
    # Toutes les sources disponibles (aligné avec scraping manuel)
    sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 
               'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    
    total_added = 0
    total_errors = 0
    
    for qi, query in enumerate(queries):
        logger.info(f"[AUTO SCRAPE] Query {qi+1}/{len(queries)}: {query}")
        
        for source in sources:
            try:
                # Utiliser la même logique que le scraping manuel
                # Cette fonction gère déjà : expansion, pertinence, doublons, etc.
                added = _run_scrape_for_source(source, query, per_query_limit, use_keyword_expansion)
                
                if added > 0:
                    logger.info(f"  ✓ {source}: {added} posts added")
                    total_added += added
                else:
                    logger.debug(f"  - {source}: no new posts")
                
                # Pause entre sources pour éviter de surcharger les APIs
                time.sleep(0.5)
                
            except Exception as e:
                total_errors += 1
                logger.error(f"  ✗ {source}: Error ({type(e).__name__}): {e}")
                # Continue avec les autres sources même en cas d'erreur
        
        # Pause entre queries pour éviter les bursts
        if qi < len(queries) - 1:  # Pas de pause après la dernière query
            time.sleep(1.0)
    
    # Nettoyer les doublons à la fin du job automatique
    try:
        deleted_duplicates = db.delete_duplicate_posts()
        if deleted_duplicates > 0:
            logger.info(f"🧹 [AUTO SCRAPE] Cleaned up {deleted_duplicates} duplicate post(s)")
    except Exception as e:
        logger.warning(f"⚠️ [AUTO SCRAPE] Warning: Could not clean duplicates: {e}")
    
    logger.info(f"✅ Scheduled scrape completed: {total_added} total posts added, {total_errors} errors")


def auto_backup_job():
    """Scheduled job to backup PostgreSQL database automatically.
    
    Creates regular backups using pg_dump:
    - Hourly backups: kept for 24 hours (24 backups)
    """
    logger.info("💾 Running scheduled database backup...")
    
    try:
        from ..utils.backup import create_postgres_backup
        
        result = create_postgres_backup(
            backup_type='hourly',
            keep_backups=24
        )
        
        logger.info(f"✅ Scheduled backup completed successfully: {result['backup_file']} ({result['size_mb']} MB)")
    except ValueError as e:
        logger.warning(f"⚠️  DATABASE_URL not configured, skipping backup: {e}")
    except Exception as e:
        logger.error(f"❌ Error during scheduled backup: {e}", exc_info=True)


def daily_backup_job():
    """Daily backup job - creates a PostgreSQL backup that will be kept longer."""
    logger.info("💾 Running daily database backup...")
    
    try:
        from ..utils.backup import create_postgres_backup
        
        result = create_postgres_backup(
            backup_type='daily',
            keep_backups=30
        )
        
        logger.info(f"✅ Daily backup completed successfully: {result['backup_file']} ({result['size_mb']} MB)")
    except ValueError as e:
        logger.warning(f"⚠️  DATABASE_URL not configured, skipping backup: {e}")
    except Exception as e:
        logger.error(f"❌ Error during daily backup: {e}", exc_info=True)


def recheck_answered_status_job():
    """Scheduled job to re-check answered status of all posts.
    
    Runs every 3 hours to update the answered status of posts by re-scraping
    their metadata from their URLs. This ensures that posts that have been
    answered since the last scrape are correctly marked as answered.
    
    Vérifie progressivement tous les posts non answered (par batch de 50 pour éviter les timeouts).
    Note: This is a synchronous wrapper that runs the async function.
    """
    import asyncio
    logger.info("🔄 Running scheduled re-check of answered status...")
    
    try:
        # Créer un event loop si nécessaire
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si un loop est déjà en cours, créer une tâche dans un thread séparé
                import threading
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # Vérifier par batch de 50 posts pour éviter les timeouts
                        # Le job planifié vérifie progressivement tous les posts sur plusieurs exécutions
                        return new_loop.run_until_complete(
                            db.recheck_posts_answered_status(limit=50, delay_between_requests=0.5)
                        )
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=600)  # 10 minutes max
            else:
                # Vérifier par batch de 50 posts
                result = loop.run_until_complete(
                    db.recheck_posts_answered_status(limit=50, delay_between_requests=0.5)
                )
        except RuntimeError:
            # Pas de loop existant, créer un nouveau
            # Vérifier par batch de 50 posts
            result = asyncio.run(
                db.recheck_posts_answered_status(limit=50, delay_between_requests=0.5)
            )
        
        if result.get('success'):
            updated = result.get('updated_count', 0)
            errors = result.get('error_count', 0)
            total = result.get('total_posts', 0)
            skipped = result.get('skipped_count', 0)
            logger.info(f"[OK] Re-check completed: {updated} posts updated, {errors} errors, {skipped} skipped, {total} total checked")
        else:
            logger.error(f"[ERROR] Re-check failed: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"[ERROR] Error during re-check answered status: {e}", exc_info=True)


