"""
Worker Service
==============
Isolated process for handling scraping jobs.
Runs separately from the API to prevent server crashes.
"""
import os
import sys
import time
import signal
import logging
from datetime import datetime
from typing import Optional

# Setup path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.job_queue import (
    get_job_queue, close_job_queue, Job, JobStatus, JobType
)
from app import database as db
from app.config import keywords_base

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('worker')

# Worker configuration
WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', '2'))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '5'))
MAX_JOB_DURATION = int(os.getenv('MAX_JOB_DURATION', '600'))  # 10 minutes

# Graceful shutdown flag
_shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    _shutdown_requested = True


def process_scrape_source_job(job: Job) -> dict:
    """Process a single source scraping job."""
    from app.routers.scraping import _run_scrape_for_source
    
    payload = job.payload
    source = payload.get('source')
    query = payload.get('query')
    limit = payload.get('limit', 50)
    use_expansion = payload.get('use_keyword_expansion', True)
    
    logger.info(f"Scraping {source} for '{query}' (limit={limit})")
    
    try:
        added = _run_scrape_for_source(source, query, limit, use_expansion)
        return {
            'source': source,
            'query': query,
            'posts_added': added,
            'status': 'success'
        }
    except Exception as e:
        logger.error(f"Error scraping {source}: {e}")
        raise


def process_scrape_all_job(job: Job) -> dict:
    """Process a job to scrape multiple sources."""
    from app.routers.scraping import _run_scrape_for_source
    
    payload = job.payload
    queries = payload.get('queries', [])
    sources = payload.get('sources', [])
    limit = payload.get('limit_per_query', 50)
    
    total_added = 0
    errors = []
    results = []
    
    for query in queries:
        for source in sources:
            if _shutdown_requested:
                logger.info("Shutdown requested, stopping scrape job")
                break
            
            try:
                added = _run_scrape_for_source(source, query, limit, True)
                total_added += added
                results.append({
                    'source': source,
                    'query': query,
                    'posts_added': added
                })
                
                # Small delay between requests
                time.sleep(0.5)
                
            except Exception as e:
                error_msg = f"{source}/{query}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error: {error_msg}")
        
        if _shutdown_requested:
            break
        
        # Delay between queries
        time.sleep(1.0)
    
    # Cleanup duplicates
    try:
        duplicates = db.delete_duplicate_posts()
        if duplicates > 0:
            logger.info(f"Cleaned {duplicates} duplicate posts")
    except Exception as e:
        logger.warning(f"Could not clean duplicates: {e}")
    
    return {
        'total_posts_added': total_added,
        'sources_scraped': len(sources),
        'queries_processed': len(queries),
        'errors': errors,
        'details': results
    }


def process_auto_scrape_job(job: Job) -> dict:
    """Process automatic scraping job."""
    logger.info("Starting automatic scrape job")
    
    # Get keywords
    user_keywords = db.get_saved_queries()
    all_keywords = keywords_base.get_all_keywords(user_keywords)
    
    if not all_keywords:
        all_keywords = keywords_base.get_all_base_keywords()
    
    # Create a sub-job for scrape_all
    sub_job = Job(
        id=job.id + "_sub",
        job_type=JobType.SCRAPE_ALL,
        payload={
            'queries': all_keywords,
            'sources': ['trustpilot', 'github', 'stackoverflow', 
                       'reddit', 'news', 'ovh-forum'],
            'limit_per_query': 50
        }
    )
    
    return process_scrape_all_job(sub_job)


def process_backup_job(job: Job) -> dict:
    """Process database backup job."""
    from pathlib import Path
    
    try:
        # Import backup function
        sys.path.insert(0, str(Path(__file__).resolve().parents[0] / "scripts"))
        from scripts.backup_db import backup_database
        
        backup_type = job.payload.get('backup_type', 'hourly')
        db_path = Path(__file__).resolve().parent / "data.duckdb"
        
        if os.getenv('USE_POSTGRES', 'false').lower() == 'true':
            # PostgreSQL backup
            logger.info("PostgreSQL backup not yet implemented")
            return {'status': 'skipped', 'reason': 'PostgreSQL backup not implemented'}
        
        # DuckDB backup
        keep_backups = 24 if backup_type == 'hourly' else 30
        success = backup_database(db_path, "production", keep_backups, backup_type)
        
        return {
            'status': 'success' if success else 'failed',
            'backup_type': backup_type
        }
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise


def process_cleanup_job(job: Job) -> dict:
    """Process cleanup job."""
    results = {}
    
    try:
        # Delete sample posts
        deleted_samples = db.delete_sample_posts()
        results['deleted_samples'] = deleted_samples
    except Exception as e:
        results['sample_error'] = str(e)
    
    try:
        # Delete duplicates
        deleted_dupes = db.delete_duplicate_posts()
        results['deleted_duplicates'] = deleted_dupes
    except Exception as e:
        results['duplicate_error'] = str(e)
    
    try:
        # Delete non-OVH posts
        deleted_non_ovh = db.delete_non_ovh_posts()
        results['deleted_non_ovh'] = deleted_non_ovh
    except Exception as e:
        results['non_ovh_error'] = str(e)
    
    return results


def process_job(job: Job) -> dict:
    """Route job to appropriate handler."""
    handlers = {
        JobType.SCRAPE_SOURCE: process_scrape_source_job,
        JobType.SCRAPE_ALL: process_scrape_all_job,
        JobType.AUTO_SCRAPE: process_auto_scrape_job,
        JobType.BACKUP: process_backup_job,
        JobType.CLEANUP: process_cleanup_job,
    }
    
    handler = handlers.get(job.job_type)
    if not handler:
        raise ValueError(f"Unknown job type: {job.job_type}")
    
    return handler(job)


def worker_loop():
    """Main worker loop."""
    global _shutdown_requested
    
    logger.info("=" * 50)
    logger.info("VibeCoding Worker Started")
    logger.info(f"Concurrency: {WORKER_CONCURRENCY}")
    logger.info(f"Poll Interval: {POLL_INTERVAL}s")
    logger.info("=" * 50)
    
    # Initialize database
    try:
        db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    queue = get_job_queue()
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while not _shutdown_requested:
        try:
            # Get next job (blocking with timeout)
            job = queue.dequeue(timeout=POLL_INTERVAL)
            
            if job is None:
                consecutive_errors = 0  # Reset on successful poll
                continue
            
            logger.info(f"Processing job: {job.id} ({job.job_type})")
            start_time = time.time()
            
            try:
                result = process_job(job)
                duration = time.time() - start_time
                
                queue.complete(job.id, result)
                logger.info(f"Job {job.id} completed in {duration:.2f}s")
                
            except Exception as e:
                duration = time.time() - start_time
                error_msg = f"{type(e).__name__}: {str(e)}"
                
                # Decide if we should retry
                retry = job.attempts < job.max_attempts
                queue.fail(job.id, error_msg, retry=retry)
                
                if retry:
                    logger.warning(f"Job {job.id} failed, will retry: {error_msg}")
                else:
                    logger.error(f"Job {job.id} failed permanently: {error_msg}")
            
            consecutive_errors = 0
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            _shutdown_requested = True
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Worker error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.critical("Too many consecutive errors, shutting down")
                break
            
            time.sleep(min(30, POLL_INTERVAL * consecutive_errors))
    
    # Cleanup
    logger.info("Worker shutting down...")
    close_job_queue()
    logger.info("Worker stopped")


def main():
    """Entry point."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        worker_loop()
    except Exception as e:
        logger.critical(f"Worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
