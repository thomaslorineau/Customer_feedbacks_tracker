"""Simplified job processing with robust progress tracking.

This module provides a simplified, robust approach to job processing:
1. Simple heartbeat that ALWAYS increments progress
2. No complex calculations or race conditions
3. Clear separation of concerns
4. Guaranteed progress updates
"""
import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from ... import db

logger = logging.getLogger(__name__)

# Simple constants
HEARTBEAT_INTERVAL = 1.0  # Update progress every second
SCRAPER_TIMEOUT = 120  # Max 2 minutes per scraper


class SimpleJobRunner:
    """Simple, robust job runner with guaranteed progress updates."""
    
    def __init__(self, job_id: str, source: str, total_steps: int = 100):
        self.job_id = job_id
        self.source = source
        self.total_steps = total_steps
        self.current_step = 0
        self.is_running = False
        self.is_cancelled = False
        self._lock = threading.Lock()  # Protect concurrent access
    
    def update_progress(self, step: int):
        """Thread-safe progress update."""
        with self._lock:
            self.current_step = min(step, self.total_steps)
            try:
                db.update_job_progress(self.job_id, self.total_steps, self.current_step)
            except Exception as e:
                logger.warning(f"[{self.source}] Failed to update DB progress: {e}")
    
    def get_progress(self) -> int:
        """Thread-safe progress read."""
        with self._lock:
            return self.current_step
    
    def cancel(self):
        """Mark job as cancelled."""
        with self._lock:
            self.is_cancelled = True
            self.is_running = False


async def run_scraper_with_progress(
    job_id: str,
    source: str,
    scraper_func: Callable,
    query: str,
    limit: int,
    jobs_dict: Dict[str, Any],
    is_async: bool = True
) -> int:
    """
    Run a scraper with simple, reliable progress tracking.
    
    Returns: Number of items added
    """
    job = jobs_dict.get(job_id)
    if not job:
        logger.error(f"[{source}] Job {job_id[:8]} not found")
        return 0
    
    # Initialize job state
    job['status'] = 'running'
    job['progress'] = {'total': 100, 'completed': 0}
    
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, 100, 0)
    except Exception as e:
        logger.warning(f"[{source}] Failed to init job in DB: {e}")
    
    # Simple heartbeat: just increment every second
    heartbeat_running = True
    current_progress = 5  # Start at 5%
    
    async def simple_heartbeat():
        nonlocal current_progress, heartbeat_running
        while heartbeat_running and current_progress < 90:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            if job.get('cancelled'):
                logger.info(f"[{source}] Job cancelled, stopping heartbeat")
                break
            
            # Always increment by 1
            current_progress = min(current_progress + 1, 89)
            job['progress']['completed'] = current_progress
            
            try:
                db.update_job_progress(job_id, 100, current_progress)
            except Exception:
                pass
            
            # Log every 10%
            if current_progress % 10 == 0:
                logger.info(f"[{source}] Progress: {current_progress}%")
    
    # Start heartbeat
    heartbeat_task = asyncio.create_task(simple_heartbeat())
    
    try:
        # Run the scraper
        logger.info(f"[{source}] Starting scraper...")
        
        if is_async:
            try:
                result = await asyncio.wait_for(
                    scraper_func(query, limit),
                    timeout=SCRAPER_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"[{source}] Timeout after {SCRAPER_TIMEOUT}s")
                result = []
        else:
            # Run sync scraper in thread
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(scraper_func, query, limit),
                    timeout=SCRAPER_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"[{source}] Timeout after {SCRAPER_TIMEOUT}s")
                result = []
        
        if not isinstance(result, list):
            result = []
        
        logger.info(f"[{source}] Scraper returned {len(result)} items")
        
        # Process results
        added = 0
        for item in result:
            if job.get('cancelled'):
                break
            try:
                if isinstance(item, dict):
                    # Quick insert without heavy processing for now
                    if db.insert_post(item):
                        added += 1
            except Exception as e:
                logger.warning(f"[{source}] Error inserting item: {e}")
        
        return added
        
    finally:
        # Stop heartbeat
        heartbeat_running = False
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        
        # Finalize progress
        if job.get('cancelled'):
            job['status'] = 'cancelled'
            job['progress']['completed'] = current_progress
            try:
                db.finalize_job(job_id, 'cancelled')
            except Exception:
                pass
        else:
            # Complete progress animation
            for step in range(current_progress, 101, 2):
                job['progress']['completed'] = step
                try:
                    db.update_job_progress(job_id, 100, step)
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            
            job['status'] = 'completed'
            job['progress']['completed'] = 100
            try:
                db.finalize_job(job_id, 'completed')
            except Exception:
                pass


def start_job_thread(job_id: str, source: str, scraper_func: Callable, 
                     query: str, limit: int, jobs_dict: Dict[str, Any],
                     is_async: bool = True):
    """Start a job in a background thread with its own event loop."""
    
    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                run_scraper_with_progress(
                    job_id, source, scraper_func, query, limit, jobs_dict, is_async
                )
            )
            logger.info(f"[{source}] Job {job_id[:8]} completed with {result} items")
        except Exception as e:
            logger.error(f"[{source}] Job {job_id[:8]} failed: {e}", exc_info=True)
            job = jobs_dict.get(job_id)
            if job:
                job['status'] = 'failed'
                job['error'] = str(e)
                try:
                    db.finalize_job(job_id, 'failed', str(e))
                except Exception:
                    pass
        finally:
            loop.close()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
