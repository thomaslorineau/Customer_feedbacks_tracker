"""Job processing functions and endpoints for async scraping jobs."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Callable, Any
import uuid
import threading
import asyncio
import logging
import os
import functools

from ... import db
from ...scraper import x_scraper, stackoverflow, github, reddit, trustpilot, ovh_forum, mastodon, g2_crowd, linkedin, discord
from ...scraper import keyword_expander
from ...analysis import sentiment, country_detection, relevance_scorer
from ...config import keywords_base
from .base import should_insert_post, log_scraping, RELEVANCE_THRESHOLD
from .endpoints import KeywordsPayload

logger = logging.getLogger(__name__)

# Global timeout for scraper calls (in seconds)
SCRAPER_TIMEOUT = 120  # 2 minutes max per scraper call


def safe_scraper_wrapper(scraper_func: Callable, source_name: str, is_async: bool = False):
    """Wrapper to make scraper calls robust and prevent server crashes.
    
    Features:
    - Timeout protection (prevents infinite hangs)
    - Exception handling (prevents crashes)
    - Result validation (ensures correct format)
    - Error logging (for debugging)
    
    Args:
        scraper_func: The scraper function to wrap
        source_name: Name of the source (for logging)
        is_async: Whether the scraper is async
    
    Returns:
        Wrapped function that always returns a list (empty on error)
    """
    if is_async:
        @functools.wraps(scraper_func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Add timeout to async scraper
                try:
                    result = await asyncio.wait_for(
                        scraper_func(*args, **kwargs),
                        timeout=SCRAPER_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.error(f"[{source_name}] Scraper timeout after {SCRAPER_TIMEOUT}s")
                    return []
                
                # Validate result is a list
                if not isinstance(result, list):
                    logger.warning(f"[{source_name}] Scraper returned non-list: {type(result)}")
                    return []
                
                # Validate items in list
                validated_result = []
                for item in result:
                    if isinstance(item, dict):
                        # Ensure required fields exist
                        if 'source' not in item:
                            item['source'] = source_name
                        validated_result.append(item)
                    else:
                        logger.warning(f"[{source_name}] Invalid item type in result: {type(item)}")
                
                return validated_result
                
            except Exception as e:
                logger.error(f"[{source_name}] Scraper error: {e}", exc_info=True)
                return []  # Always return empty list on error
        
        return async_wrapper
    else:
        @functools.wraps(scraper_func)
        def sync_wrapper(*args, **kwargs):
            try:
                # For sync scrapers, run in thread with timeout
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(scraper_func, *args, **kwargs)
                    try:
                        result = future.result(timeout=SCRAPER_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        logger.error(f"[{source_name}] Scraper timeout after {SCRAPER_TIMEOUT}s")
                        return []
                
                # Validate result is a list
                if not isinstance(result, list):
                    logger.warning(f"[{source_name}] Scraper returned non-list: {type(result)}")
                    return []
                
                # Validate items in list
                validated_result = []
                for item in result:
                    if isinstance(item, dict):
                        # Ensure required fields exist
                        if 'source' not in item:
                            item['source'] = source_name
                        validated_result.append(item)
                    else:
                        logger.warning(f"[{source_name}] Invalid item type in result: {type(item)}")
                
                return validated_result
                
            except Exception as e:
                logger.error(f"[{source_name}] Scraper error: {e}", exc_info=True)
                return []  # Always return empty list on error
        
        return sync_wrapper

router = APIRouter()

# Job tracking
JOBS = {}

# Track problematic job IDs that should be blocked (to prevent spam)
BLOCKED_JOB_IDS = {
    '84d4fd06-ae2e-43a1-9387-e037a668f75a': True  # Known stale job ID
}
BLOCKED_JOB_REQUEST_COUNT = {}  # Track request count per blocked job


async def _run_scrape_for_source_async(source: str, query: str, limit: int, use_keyword_expansion: bool = True, job_id: Optional[str] = None):
    """Async version: Call the appropriate scraper and insert results into DB; return count added."""
    try:
        # Check if job was cancelled before starting
        if job_id:
            job = JOBS.get(job_id)
            if job and job.get('cancelled'):
                logger.info(f"[{source}] Job {job_id[:8]} was cancelled, aborting scraping")
                return 0
        # Wrap all scrapers with safety wrapper
        async_mapper = {
            'github': safe_scraper_wrapper(github.scrape_github_issues_async, 'GitHub', is_async=True),
            'trustpilot': safe_scraper_wrapper(trustpilot.scrape_trustpilot_reviews_async, 'Trustpilot', is_async=True),
            'stackoverflow': safe_scraper_wrapper(stackoverflow.scrape_stackoverflow_async, 'StackOverflow', is_async=True),
            'reddit': safe_scraper_wrapper(reddit.scrape_reddit_async, 'Reddit', is_async=True),
            'mastodon': safe_scraper_wrapper(mastodon.scrape_mastodon_async, 'Mastodon', is_async=True),
            'linkedin': safe_scraper_wrapper(linkedin.scrape_linkedin_async, 'LinkedIn', is_async=True),
            'discord': safe_scraper_wrapper(discord.scrape_discord_async, 'Discord', is_async=True),
        }
        sync_mapper = {
            'x': safe_scraper_wrapper(x_scraper.scrape_x, 'X/Twitter', is_async=False),
            'ovh-forum': safe_scraper_wrapper(ovh_forum.scrape_ovh_forum, 'OVH Forum', is_async=False),
            'g2-crowd': safe_scraper_wrapper(g2_crowd.scrape_g2_crowd, 'G2 Crowd', is_async=False),
        }
        
        async_func = async_mapper.get(source)
        sync_func = sync_mapper.get(source)
        
        if async_func is None and sync_func is None:
            return 0
        
        func = async_func if async_func else sync_func
        is_async = async_func is not None
        
        queries_to_try = [query]
        if use_keyword_expansion:
            try:
                expanded = keyword_expander.expand_keywords([query])
                if len(expanded) > 1:
                    queries_to_try = [query] + expanded[1:5]
                    logger.info(f"[Keyword Expansion] Using {len(queries_to_try)} query variants for {source}: {queries_to_try[:3]}...")
            except Exception as e:
                logger.warning(f"[Keyword Expansion] Failed to expand keywords: {e}, using original query only")
                queries_to_try = [query]
        
        all_items = []
        seen_urls = set()
        
        for query_variant in queries_to_try:
            # Check if job was cancelled before processing each query variant
            if job_id:
                job = JOBS.get(job_id)
                if job and job.get('cancelled'):
                    logger.info(f"[{source}] Job {job_id[:8]} was cancelled during scraping, stopping")
                    break
            
            try:
                per_query_limit = max(limit // len(queries_to_try), 20)  # Minimum 20 par query pour meilleure couverture
                
                if is_async:
                    items = await func(query_variant, per_query_limit)
                else:
                    items = await asyncio.to_thread(func, query_variant, per_query_limit)
                
                # Validate items is a list (safety wrapper should ensure this, but double-check)
                if not isinstance(items, list):
                    logger.warning(f"[{source}] Scraper returned non-list: {type(items)}, converting to empty list")
                    items = []
                
                # Check again after scraping this variant
                if job_id:
                    job = JOBS.get(job_id)
                    if job and job.get('cancelled'):
                        logger.info(f"[{source}] Job {job_id[:8]} was cancelled after scraping variant, stopping")
                        break
                
                # Process items safely
                for item in items:
                    try:
                        # Validate item is a dict
                        if not isinstance(item, dict):
                            logger.warning(f"[{source}] Skipping invalid item (not a dict): {type(item)}")
                            continue
                        
                        url = item.get('url', '')
                        if url and url not in seen_urls:
                            all_items.append(item)
                            seen_urls.add(url)
                        elif not url:
                            all_items.append(item)
                    except Exception as item_error:
                        logger.warning(f"[{source}] Error processing item: {item_error}")
                        continue
                
                if len(all_items) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"[{source}] Error in query variant processing: {e}", exc_info=True)
                try:
                    if job_id:
                        job = JOBS.get(job_id)
                        if job:
                            db.append_job_error(job_id, f"{source} (query: {query_variant}): {str(e)}")
                except Exception:
                    pass
                continue  # Continue with next query variant
        
        all_items = all_items[:limit]
        
        added = 0
        duplicates = 0
        filtered_by_relevance = 0
        
        # Check if job was cancelled before processing items
        if job_id:
            job = JOBS.get(job_id)
            if job and job.get('cancelled'):
                logger.info(f"[{source}] Job {job_id[:8]} was cancelled before processing items")
                return 0
        
        for it in all_items:
            # Check if job was cancelled during item processing
            if job_id:
                job = JOBS.get(job_id)
                if job and job.get('cancelled'):
                    logger.info(f"[{source}] Job {job_id[:8]} was cancelled during item processing")
                    break
            
            try:
                is_relevant, relevance_score = should_insert_post(it)
                if not is_relevant:
                    filtered_by_relevance += 1
                    logger.debug(f"[{source}] Skipping post (relevance={relevance_score:.2f} < {RELEVANCE_THRESHOLD}): {it.get('content', '')[:100]}")
                    continue
                
                # Detect language first
                try:
                    from ...analysis import language_detection
                    detected_language = language_detection.detect_language_from_post(it)
                    it['language'] = detected_language
                except Exception as e:
                    logger.debug(f"[{source}] Language detection failed: {e}")
                    it['language'] = it.get('language', 'unknown')
                
                # Analyze sentiment with language awareness
                content = it.get('content') or ''
                language = it.get('language', 'unknown')
                try:
                    an = sentiment.analyze(content, language=language)
                except Exception as e:
                    logger.warning(f"[{source}] Sentiment analysis failed: {e}, using neutral")
                    an = {'label': 'neutral', 'score': 0.0}
                
                try:
                    country = country_detection.detect_country_from_post(it)
                except Exception as e:
                    logger.debug(f"[{source}] Country detection failed: {e}")
                    country = None
                
                try:
                    if db.insert_post({
                        'source': it.get('source'),
                        'author': it.get('author'),
                        'content': it.get('content'),
                        'url': it.get('url'),
                        'created_at': it.get('created_at'),
                        'sentiment_score': an['score'],
                        'sentiment_label': an['label'],
                        'language': it.get('language', 'unknown'),
                        'country': country,
                        'relevance_score': relevance_score,
                    }):
                        added += 1
                    else:
                        duplicates += 1
                except Exception as db_error:
                    logger.warning(f"[{source}] Failed to insert post to DB: {db_error}")
                    # Continue processing other items even if one fails
                    continue
            except Exception as item_error:
                logger.warning(f"[{source}] Error processing item: {item_error}")
                # Continue processing other items even if one fails
                continue
        
        if filtered_by_relevance > 0:
            logger.info(f"[{source}] Filtered {filtered_by_relevance} posts by relevance threshold")
        
        if duplicates > 0:
            logger.warning(f"  ⚠️ Skipped {duplicates} duplicate(s) from {source}")
        
        return added
    except Exception as e:
        error_msg = f"{source} (query: {query}): {str(e)}"
        logger.error(f"Error in _run_scrape_for_source_async: {error_msg}", exc_info=True)
        try:
            for job_id, info in JOBS.items():
                if info.get('status') == 'running':
                    db.append_job_error(job_id, error_msg)
        except Exception:
            pass
        return 0


def _run_scrape_for_source(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """Synchronous wrapper for backward compatibility."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _run_scrape_for_source_sync(source, query, limit, use_keyword_expansion)
        else:
            return loop.run_until_complete(_run_scrape_for_source_async(source, query, limit, use_keyword_expansion))
    except RuntimeError:
        return asyncio.run(_run_scrape_for_source_async(source, query, limit, use_keyword_expansion))


def _run_scrape_for_source_sync(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """Synchronous fallback implementation."""
    mapper = {
        'x': lambda q, l: x_scraper.scrape_x(q, limit=l),
        'github': lambda q, l: github.scrape_github_issues(q, limit=l),
        'stackoverflow': lambda q, l: stackoverflow.scrape_stackoverflow(q, limit=l),
        'reddit': lambda q, l: reddit.scrape_reddit(q, limit=l),
        'trustpilot': lambda q, l: trustpilot.scrape_trustpilot_reviews(q, limit=l),
    }
    func = mapper.get(source)
    if func is None:
        return 0
    
    queries_to_try = [query]
    if use_keyword_expansion:
        try:
            expanded = keyword_expander.expand_keywords([query])
            if len(expanded) > 1:
                queries_to_try = [query] + expanded[1:5]
                logger.info(f"[Keyword Expansion] Using {len(queries_to_try)} query variants for {source}: {queries_to_try[:3]}...")
        except Exception as e:
            logger.warning(f"[Keyword Expansion] Failed to expand keywords: {e}, using original query only")
            queries_to_try = [query]
    
    all_items = []
    seen_urls = set()
    
    for query_variant in queries_to_try:
        try:
            per_query_limit = max(limit // len(queries_to_try), 10)
            items = func(query_variant, per_query_limit)
            
            for item in items:
                url = item.get('url', '')
                if url and url not in seen_urls:
                    all_items.append(item)
                    seen_urls.add(url)
                elif not url:
                    all_items.append(item)
            
            if len(all_items) >= limit:
                break
                
        except Exception as e:
            try:
                for job_id, info in JOBS.items():
                    if info.get('status') == 'running':
                        db.append_job_error(job_id, f"{source} (query: {query_variant}): {str(e)}")
            except Exception:
                pass
            continue
    
    all_items = all_items[:limit]
    
    added = 0
    duplicates = 0
    for it in all_items:
        try:
            # Detect language first
            try:
                from ...analysis import language_detection
                detected_language = language_detection.detect_language_from_post(it)
                it['language'] = detected_language
            except Exception:
                it['language'] = it.get('language', 'unknown')
            
            # Analyze sentiment with language awareness
            content = it.get('content') or ''
            language = it.get('language', 'unknown')
            an = sentiment.analyze(content, language=language)
            
            country = country_detection.detect_country_from_post(it)
            if db.insert_post({
                'source': it.get('source'),
                'author': it.get('author'),
                'content': it.get('content'),
                'url': it.get('url'),
                'created_at': it.get('created_at'),
                'sentiment_score': an['score'],
                'sentiment_label': an['label'],
                'language': it.get('language', 'unknown'),
                'country': country,
            }):
                added += 1
            else:
                duplicates += 1
        except Exception:
            continue
    
    if duplicates > 0:
        logger.warning(f"  ⚠️ Skipped {duplicates} duplicate(s) from {source}")
    
    return added


async def _process_keyword_job_async(job_id: str, keywords: List[str], limit: int, concurrency: int, delay: float):
    """Async version of keyword job processing using asyncio.gather."""
    job = JOBS.get(job_id)
    if job is None:
        return
    
    # Update status to running immediately
    job['status'] = 'running'
    try:
        db.create_job_record(job_id)
        # Update status in DB immediately - use finalize_job but without error
        import datetime
        with db.get_db() as conn:
            c = conn.cursor()
            now = datetime.datetime.utcnow().isoformat()
            c.execute('UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?', ('running', now, job_id))
            # commit is automatic with context manager
    except Exception as e:
        logger.warning(f"Failed to update job status to running: {e}")
    
    sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    total_tasks = len(keywords) * len(sources)
    job['progress'] = {'total': total_tasks, 'completed': 0}
    try:
        db.update_job_progress(job_id, total_tasks, 0)
    except Exception:
        pass

    try:
        tasks = []
        for kw in keywords:
            if job.get('cancelled'):
                job['status'] = 'cancelled'
                return
            for s in sources:
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    return
                tasks.append(_run_scrape_for_source_async(s, kw, limit))
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_with_semaphore(task):
            async with semaphore:
                nonlocal started_count
                started_count += 1
                logger.debug(f"Job {job_id[:8]}: Starting task {started_count}/{total_tasks}")
                
                if job.get('cancelled'):
                    return None
                try:
                    result = await asyncio.wait_for(task, timeout=300.0)
                    return result
                except asyncio.TimeoutError:
                    error_msg = "Task timed out after 5 minutes"
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.warning(f"Task timed out for job {job_id}")
                    return None
                except Exception as e:
                    error_msg = str(e)
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.warning(f"Task error for job {job_id}: {error_msg}")
                    return None
        
        wrapped_tasks = [asyncio.create_task(process_with_semaphore(task)) for task in tasks]
        
        completed_count = 0
        started_count = 0  # Track how many tasks have started
        
        async def progress_heartbeat():
            nonlocal completed_count, started_count
            # Estimate progress: assume tasks take time, so show partial progress based on started tasks
            while job.get('status') == 'running' and completed_count < total_tasks:
                await asyncio.sleep(2.0)  # Update every 2 seconds
                if job.get('cancelled'):
                    break
                
                # Update progress: show at least some progress even if tasks are still running
                # Use a combination of completed and estimated progress
                estimated_progress = completed_count
                if started_count > completed_count:
                    # Estimate: if tasks are running, assume they're 50% done
                    estimated_progress = completed_count + int((started_count - completed_count) * 0.5)
                
                # Always update progress, even if it's 0 (to show the job is alive)
                job['progress']['completed'] = min(estimated_progress, total_tasks)
                job['progress']['total'] = total_tasks  # Ensure total is always set
                try:
                    db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                    # Log progress updates periodically for debugging
                    if completed_count % max(1, total_tasks // 20) == 0 or completed_count == 1:
                        logger.info(f"Job {job_id[:8]}: Progress updated to {job['progress']['completed']}/{total_tasks} (DB synced)")
                except Exception as e:
                    logger.warning(f"Failed to update job progress in DB: {e}")
                
                # Log progress every 10% or every 10 tasks
                if completed_count > 0 and completed_count % max(1, total_tasks // 10) == 0:
                    logger.info(f"Job {job_id[:8]}: {completed_count}/{total_tasks} tasks completed ({completed_count*100//total_tasks}%)")
        
        heartbeat_task = asyncio.create_task(progress_heartbeat())
        
        try:
            for completed_task in asyncio.as_completed(wrapped_tasks):
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    heartbeat_task.cancel()
                    return
                
                try:
                    result = await completed_task
                    
                    completed_count += 1
                    # Update progress immediately when a task completes
                    estimated_progress = completed_count
                    if started_count > completed_count:
                        estimated_progress = completed_count + int((started_count - completed_count) * 0.5)
                    
                    job['progress']['completed'] = min(estimated_progress, total_tasks)
                    try:
                        db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                    except Exception:
                        pass
                    
                    logger.debug(f"Job {job_id[:8]}: Task completed ({completed_count}/{total_tasks})")
                    
                    if isinstance(result, Exception):
                        error_msg = str(result)
                        if job.get('status') == 'running':
                            job['errors'].append(error_msg)
                            try:
                                db.append_job_error(job_id, error_msg)
                            except Exception:
                                pass
                        logger.warning(f"Task failed for job {job_id}: {error_msg}")
                    elif result is None:
                        logger.debug(f"Task returned None for job {job_id}")
                    else:
                        job['results'].append({'added': result})
                        try:
                            db.append_job_result(job_id, {'added': result})
                        except Exception:
                            pass
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    error_msg = str(e)
                    if job.get('status') == 'running':
                        job['errors'].append(error_msg)
                        try:
                            db.append_job_error(job_id, error_msg)
                        except Exception:
                            pass
                    logger.error(f"Error processing completed task for job {job_id}: {error_msg}", exc_info=True)
                    
                    completed_count += 1
                    # Update progress even on error
                    estimated_progress = completed_count
                    if started_count > completed_count:
                        estimated_progress = completed_count + int((started_count - completed_count) * 0.5)
                    
                    job['progress']['completed'] = min(estimated_progress, total_tasks)
                    try:
                        db.update_job_progress(job_id, total_tasks, job['progress']['completed'])
                    except Exception:
                        pass
        
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        job['status'] = 'completed'
        try:
            db.finalize_job(job_id, 'completed')
        except Exception:
            pass
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        try:
            db.append_job_error(job_id, str(e))
            db.finalize_job(job_id, 'failed', str(e))
        except Exception:
            pass


def _process_keyword_job(job_id: str, keywords: List[str], limit: int, concurrency: int, delay: float):
    """Synchronous wrapper that runs async job processing."""
    def run_async():
        """Run async job in a completely isolated event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))
        except Exception as e:
            logger.error(f"Error in keyword job thread {job_id[:8]}: {e}", exc_info=True)
            # Update job status to failed
            try:
                job = JOBS.get(job_id)
                if job:
                    job['status'] = 'failed'
                    job['error'] = str(e)
                    db.append_job_error(job_id, str(e))
                    db.finalize_job(job_id, 'failed', str(e))
            except Exception:
                pass
        finally:
            try:
                # Cancel all pending tasks
                pending = asyncio.all_tasks(new_loop)
                for task in pending:
                    task.cancel()
                # Wait for cancellation
                if pending:
                    new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            new_loop.close()
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()


async def _process_single_source_job_async(job_id: str, source: str, query: str, limit: int):
    """Process a single source scraping job with granular progress updates."""
    try:
        logger.info(f"[{source}] Async function started for job {job_id[:8]}")
    except Exception:
        pass
    
    job = JOBS.get(job_id)
    if job is None:
        try:
            logger.error(f"[{source}] Job {job_id[:8]} not found in JOBS dict!")
        except Exception:
            pass
        return
    
    try:
        logger.info(f"[{source}] Setting job {job_id[:8]} status to 'running' (was: {job.get('status')})")
    except Exception:
        pass
    
    # CRITICAL: Set status to running IMMEDIATELY, before anything else
    # This must happen before any await or DB operations
    job['status'] = 'running'
    
    # Also update in DB immediately to ensure consistency
    try:
        import datetime
        with db.get_db() as conn:
            c = conn.cursor()
            now = datetime.datetime.utcnow().isoformat()
            c.execute('UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?', ('running', now, job_id))
    except Exception as db_err:
        try:
            logger.warning(f"[{source}] Failed to update job status in DB: {db_err}")
        except Exception:
            pass
    
    try:
        logger.info(f"[{source}] Job {job_id[:8]} status is now: {job.get('status')}")
    except Exception:
        pass
    
    total_steps = 100
    init_steps = 5
    scraping_start = init_steps
    scraping_end = 90
    processing_start = scraping_end
    
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, total_steps, 0)
    except Exception:
        pass
    
    job['progress'] = {'total': total_steps, 'completed': 0}
    
    heartbeat_running = True
    heartbeat_step = scraping_start
    
    async def progress_heartbeat():
        """Simplified heartbeat: just increment progress every second."""
        nonlocal heartbeat_step, heartbeat_running
        logger.info(f"[{source}] Heartbeat started for job {job_id[:8]} (from {heartbeat_step} to {scraping_end})")
        
        while heartbeat_running and heartbeat_step < scraping_end:
            # Check cancellation
            if job.get('cancelled'):
                logger.info(f"[{source}] Job cancelled, stopping heartbeat")
                heartbeat_running = False
                break
            
            # Wait 1 second
            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception:
                break
            
            # Increment progress
            if heartbeat_step < scraping_end - 1:
                heartbeat_step += 1
            
            # Update progress in memory and DB
            job['progress']['completed'] = heartbeat_step
            job['progress']['total'] = total_steps
            
            try:
                db.update_job_progress(job_id, total_steps, heartbeat_step)
                # Log every 10%
                if heartbeat_step % 10 == 0:
                    logger.info(f"[{source}] Progress: {heartbeat_step}%")
            except Exception as e:
                logger.debug(f"[{source}] DB update failed: {e}")
        
        logger.info(f"[{source}] Heartbeat finished at {heartbeat_step}%")
    
    try:
        if job.get('cancelled'):
            job['status'] = 'cancelled'
            db.finalize_job(job_id, 'cancelled', 'cancelled by user')
            return
        
        for step in range(1, init_steps + 1):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        if not query or query.strip() == "":
            base_keywords = keywords_base.get_all_base_keywords()
            if base_keywords:
                query = base_keywords[0] if len(base_keywords) == 1 else " ".join(base_keywords[:3])
                log_scraping(source, "info", f"Using base keywords: {query}")
        
        job['progress']['completed'] = scraping_start
        job['progress']['total'] = total_steps
        try:
            db.update_job_progress(job_id, total_steps, scraping_start)
            logger.info(f"[{source}] Initial progress set to {scraping_start}/{total_steps} before scraping starts")
        except Exception as e:
            logger.warning(f"[{source}] Failed to set initial progress: {e}")
        
        # Start heartbeat BEFORE scraping to ensure progress updates
        heartbeat_task = None
        try:
            logger.info(f"[{source}] Starting heartbeat task for job {job_id[:8]}...")
            heartbeat_task = asyncio.create_task(progress_heartbeat())
            logger.info(f"[{source}] Heartbeat task created for job {job_id[:8]}, task={heartbeat_task}")
        except Exception as heartbeat_error:
            logger.error(f"[{source}] Failed to create heartbeat task: {heartbeat_error}", exc_info=True)
            # Don't fail the job, but log the error
            heartbeat_task = None
        
        # Give heartbeat a moment to start and update progress
        if heartbeat_task:
            try:
                await asyncio.sleep(0.5)  # Increased delay to ensure heartbeat starts
                logger.info(f"[{source}] Heartbeat task status: done={heartbeat_task.done()}, cancelled={heartbeat_task.cancelled()}, exception={heartbeat_task.exception() if heartbeat_task.done() else None}")
                # Check if heartbeat crashed immediately
                if heartbeat_task.done() and heartbeat_task.exception():
                    logger.error(f"[{source}] Heartbeat task crashed immediately: {heartbeat_task.exception()}", exc_info=True)
                    # Try to restart heartbeat
                    try:
                        heartbeat_running = True
                        heartbeat_task = asyncio.create_task(progress_heartbeat())
                        logger.info(f"[{source}] Restarted heartbeat task")
                    except Exception as restart_err:
                        logger.error(f"[{source}] Failed to restart heartbeat: {restart_err}", exc_info=True)
            except Exception as check_err:
                logger.error(f"[{source}] Error checking heartbeat status: {check_err}", exc_info=True)
        else:
            logger.error(f"[{source}] Heartbeat task is None - heartbeat will not run!")
        
        try:
            # Check if job was cancelled before starting scraping
            if job.get('cancelled'):
                logger.info(f"[{source}] Job {job_id[:8]} was cancelled before scraping started")
                return
            
            logger.info(f"[{source}] Starting scraping for job {job_id[:8]}...")
            
            # Wrap scraping in try/except to prevent server crash
            try:
                added = await _run_scrape_for_source_async(source, query, limit, use_keyword_expansion=False, job_id=job_id)
            except Exception as scrape_error:
                logger.error(f"[{source}] Error during scraping for job {job_id[:8]}: {scrape_error}", exc_info=True)
                # Don't crash - just log the error and continue
                added = 0
                # Add error to job
                try:
                    db.append_job_error(job_id, f"Scraping error: {str(scrape_error)}")
                except Exception:
                    pass
            
            # Check again after scraping (job might have been cancelled during scraping)
            if job.get('cancelled'):
                logger.info(f"[{source}] Job {job_id[:8]} was cancelled during scraping")
                return
            
            logger.info(f"[{source}] Scraping completed for job {job_id[:8]}, added {added} posts")
        finally:
            # Don't stop heartbeat immediately - let it finish naturally to show progress
            # Set flag but let heartbeat continue until it reaches scraping_end
            heartbeat_running = False
            try:
                logger.info(f"[{source}] Scraping finished, stopping heartbeat. Current progress: {job['progress']['completed']}/{total_steps}")
            except Exception:
                pass
            # Wait a bit for heartbeat to catch up if scraping finished quickly
            await asyncio.sleep(1.0)
            # Now cancel heartbeat if it's still running
            if heartbeat_task and not heartbeat_task.done():
                try:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                except Exception as cancel_err:
                    try:
                        logger.warning(f"[{source}] Error cancelling heartbeat: {cancel_err}")
                    except Exception:
                        pass
            # Ensure we're at scraping_end
            current_progress = job['progress']['completed']
            if current_progress < scraping_end:
                logger.info(f"[{source}] Updating progress from {current_progress} to {scraping_end}")
                job['progress']['completed'] = scraping_end
                try:
                    db.update_job_progress(job_id, total_steps, scraping_end)
                except Exception as e:
                    logger.warning(f"[{source}] Failed to update progress to scraping_end: {e}")
        
        for step in range(processing_start, processing_start + 5):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.1)
        
        job['results'].append({'added': added, 'source': source})
        
        for step in range(processing_start + 5, total_steps):
            job['progress']['completed'] = step
            try:
                db.update_job_progress(job_id, total_steps, step)
            except Exception:
                pass
            await asyncio.sleep(0.05)
        
        job['progress']['completed'] = total_steps - 1
        try:
            db.update_job_progress(job_id, total_steps, total_steps - 1)
        except Exception:
            pass
        
        try:
            deleted_duplicates = db.delete_duplicate_posts()
            if deleted_duplicates > 0:
                logger.info(f"[{source}] Cleaned up {deleted_duplicates} duplicate posts after scraping")
                job['results'].append({'duplicates_removed': deleted_duplicates})
        except Exception as e:
            logger.warning(f"[{source}] Failed to cleanup duplicates: {e}")
        
        job['progress']['completed'] = total_steps
        try:
            db.update_job_progress(job_id, total_steps, total_steps)
            db.append_job_result(job_id, {'added': added, 'source': source})
        except Exception:
            pass
        
        job['status'] = 'completed'
        db.finalize_job(job_id, 'completed')
        
    except Exception as e:
        heartbeat_running = False
        error_msg = str(e)
        job['status'] = 'failed'
        job['error'] = error_msg
        job['errors'].append(error_msg)
        try:
            db.append_job_error(job_id, error_msg)
            db.finalize_job(job_id, 'failed', error_msg)
        except Exception:
            pass
        logger.error(f"Error in single source job {job_id}: {error_msg}", exc_info=True)


def _process_single_source_job(job_id: str, source: str, query: str, limit: int):
    """Wrapper to run async job processing in a thread."""
    def run_in_new_loop():
        """Run async job in a completely isolated event loop."""
        new_loop = None
        try:
            try:
                logger.info(f"[{source}] Thread function started for job {job_id[:8]}")
            except Exception:
                pass  # Don't crash if logging fails
            
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                logger.info(f"[{source}] Calling async function for job {job_id[:8]}...")
            except Exception:
                pass
            
            new_loop.run_until_complete(_process_single_source_job_async(job_id, source, query, limit))
            
            try:
                logger.info(f"[{source}] Async function completed for job {job_id[:8]}")
            except Exception:
                pass
        except KeyboardInterrupt:
            # Don't catch keyboard interrupts
            raise
        except SystemExit:
            # Don't catch system exits
            raise
        except Exception as e:
            try:
                logger.error(f"Error in single source job thread {job_id[:8]}: {e}", exc_info=True)
            except Exception:
                # If logging fails, at least print to stderr
                import sys
                print(f"ERROR: Failed to log error for job {job_id[:8]}: {e}", file=sys.stderr)
            
            # Update job status to failed
            try:
                job = JOBS.get(job_id)
                if job:
                    job['status'] = 'failed'
                    job['error'] = str(e)
                    try:
                        db.append_job_error(job_id, str(e))
                        db.finalize_job(job_id, 'failed', str(e))
                    except Exception:
                        pass  # DB operations might fail, but don't crash
            except Exception:
                pass  # Don't crash if updating job status fails
        finally:
            if new_loop:
                try:
                    # Cancel all pending tasks
                    pending = asyncio.all_tasks(new_loop)
                    for task in pending:
                        try:
                            task.cancel()
                        except Exception:
                            pass
                    # Wait for cancellation
                    if pending:
                        try:
                            new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    new_loop.close()
                except Exception:
                    pass
    
    try:
        t = threading.Thread(target=run_in_new_loop, daemon=True)
        t.start()
    except Exception as e:
        # If thread creation fails, mark job as failed
        try:
            logger.error(f"Failed to start thread for job {job_id[:8]}: {e}", exc_info=True)
            job = JOBS.get(job_id)
            if job:
                job['status'] = 'failed'
                job['error'] = f"Failed to start thread: {str(e)}"
        except Exception:
            pass


@router.post('/scrape/{source}/job')
async def start_single_source_job(
    source: str,
    query: str = "",
    limit: int = 100
):
    """Start a background job for a single scraper source."""
    try:
        valid_sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
        if source not in valid_sources:
            raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}")
        
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            'id': job_id,
            'status': 'pending',
            'progress': {'total': 100, 'completed': 0},  # Initialize with correct total
            'results': [],
            'errors': [],
            'cancelled': False,
            'error': None,
        }
        
        try:
            db.create_job_record(job_id)
            db.update_job_progress(job_id, 100, 0)
        except Exception as db_error:
            # Log but don't fail - job can still proceed
            try:
                logger.warning(f"Failed to create DB record for job {job_id[:8]}: {db_error}")
            except Exception:
                pass
        
        try:
            logger.info(f"[{source}] Starting job {job_id[:8]} in background thread...")
        except Exception:
            pass
        
        # Start thread BEFORE setting status to running (thread will set it)
        try:
            t = threading.Thread(target=_process_single_source_job, args=(job_id, source, query, limit), daemon=True)
            t.start()
            try:
                logger.info(f"[{source}] Thread started for job {job_id[:8]}, thread alive: {t.is_alive()}")
            except Exception:
                pass
        except Exception as thread_error:
            # If thread creation fails, mark job as failed and return error
            try:
                logger.error(f"Failed to create thread for job {job_id[:8]}: {thread_error}", exc_info=True)
                job = JOBS.get(job_id)
                if job:
                    job['status'] = 'failed'
                    job['error'] = f"Failed to start thread: {str(thread_error)}"
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to start scraping job: {str(thread_error)}")
        
        return {
            'job_id': job_id,
            'source': source,
            'query': query,
            'limit': limit,
            'total_tasks': 1
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        try:
            logger.error(f"Unexpected error in start_single_source_job: {e}", exc_info=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post('/scrape/keywords')
async def start_keyword_scrape(request: Request, payload: KeywordsPayload, limit: int = 100, concurrency: int = 2, delay: float = 0.5):
    """Start a background job that scrapes multiple keywords across sources with throttling."""
    user_keywords = payload.keywords or []
    
    all_keywords = keywords_base.get_all_keywords(user_keywords)
    
    if not all_keywords:
        raise HTTPException(status_code=400, detail='No keywords available (base + user)')

    sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    total_tasks = len(all_keywords) * len(sources)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': {'total': total_tasks, 'completed': 0},
        'results': [],
        'errors': [],
        'cancelled': False,
        'error': None,
    }

    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, total_tasks, 0)
    except Exception:
        pass

    t = threading.Thread(target=_process_keyword_job, args=(job_id, all_keywords, limit, concurrency, delay), daemon=True)
    t.start()

    return {'job_id': job_id, 'total_keywords': len(all_keywords), 'base_keywords': len(keywords_base.get_all_base_keywords()), 'user_keywords': len(user_keywords)}


@router.get('/scrape/jobs')
async def get_all_jobs_endpoint(status: Optional[str] = None, limit: int = 100):
    """Get all scraping jobs with optional filters."""
    try:
        jobs = db.get_all_jobs(status=status, limit=limit)
        return {
            'jobs': jobs,
            'total': len(jobs)
        }
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/scrape/jobs/{job_id}')
async def get_job_status(job_id: str):
    """Get status of a specific scraping job."""
    # Block known stale/problematic job IDs to prevent spam
    if job_id in BLOCKED_JOB_IDS:
        count = BLOCKED_JOB_REQUEST_COUNT.get(job_id, 0)
        BLOCKED_JOB_REQUEST_COUNT[job_id] = count + 1
        
        # After 3 requests, stop logging (but still return 404)
        if count < 3:
            logger.warning(f"Blocked request for stale job {job_id} (request #{count + 1})")
        
        # Return 410 Gone (instead of 404) to indicate the resource is permanently gone
        # This might help some clients stop retrying
        raise HTTPException(
            status_code=410,
            detail=f'Job {job_id} has been permanently removed. Please clear your browser cache and localStorage.'
        )
    
    # First check in-memory JOBS dict (for active jobs)
    job = JOBS.get(job_id)
    if job:
        try:
            db_job = db.get_job_record(job_id)
            if db_job:
                # For running jobs, use whichever progress is higher (memory or DB)
                # This handles cases where DB updates fail but memory is still updated
                if db_job.get('progress') and job.get('progress'):
                    db_completed = db_job['progress'].get('completed', 0) or 0
                    mem_completed = job['progress'].get('completed', 0) or 0
                    # Use the higher value (memory may be ahead if DB update failed)
                    if db_completed > mem_completed:
                        job['progress'] = db_job['progress']
                        logger.debug(f"Synced progress from DB for job {job_id[:8]}: {db_job['progress']}")
                    # else keep memory progress (it's more up to date)
                elif db_job.get('progress') and not job.get('progress'):
                    job['progress'] = db_job['progress']
                
                # Sync status for final states
                if db_job.get('status') in ('completed', 'failed', 'cancelled'):
                    if db_job['status'] != job.get('status'):
                        job['status'] = db_job['status']
        except Exception as e:
            logger.debug(f"Could not sync job {job_id} with DB: {e}")
        
        if 'progress' not in job:
            job['progress'] = {'total': 0, 'completed': 0}
        
        # Ensure progress values are integers (not None)
        if job.get('progress'):
            job['progress']['total'] = int(job['progress'].get('total', 0) or 0)
            job['progress']['completed'] = int(job['progress'].get('completed', 0) or 0)
        
        # Log current state for debugging
        logger.info(f"Returning job {job_id[:8]}: status={job.get('status')}, progress={job.get('progress')}")
        
        return job
    
    # If not in memory, check database (for completed/failed jobs)
    try:
        rec = db.get_job_record(job_id)
        if rec:
            # If job is in DB with status "running" but not in memory, it's likely stuck (server restarted)
            # Mark it as failed after checking if it's been running for too long
            if rec.get('status') == 'running':
                import time
                from datetime import datetime
                # Check if job has been running for more than 30 minutes (likely stuck)
                updated_at = rec.get('updated_at')
                if updated_at:
                    try:
                        # Parse timestamp (format: ISO string or timestamp)
                        if isinstance(updated_at, str):
                            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        else:
                            updated_dt = datetime.fromtimestamp(updated_at)
                        
                        time_diff = (datetime.now(updated_dt.tzinfo) - updated_dt).total_seconds()
                        # If job hasn't been updated in 30 minutes, mark as failed
                        if time_diff > 30 * 60:  # 30 minutes
                            logger.warning(f"Job {job_id[:8]} appears stuck (no update for {int(time_diff/60)} min), marking as failed")
                            try:
                                db.finalize_job(job_id, 'failed', 'Job appears stuck - no progress update for over 30 minutes')
                                rec['status'] = 'failed'
                                rec['error'] = 'Job appears stuck - no progress update for over 30 minutes'
                            except Exception as e:
                                logger.error(f"Failed to mark stuck job as failed: {e}")
                    except Exception as e:
                        logger.debug(f"Could not check job age: {e}")
            
            # Ensure progress exists and values are integers
            if 'progress' not in rec:
                rec['progress'] = {'total': 0, 'completed': 0}
            else:
                rec['progress']['total'] = int(rec['progress'].get('total', 0) or 0)
                rec['progress']['completed'] = int(rec['progress'].get('completed', 0) or 0)
            
            logger.info(f"Returning job {job_id[:8]} from DB: status={rec.get('status')}, progress={rec.get('progress')}")
            return rec
    except Exception as e:
        logger.debug(f"Error retrieving job {job_id} from DB: {e}")
    
    # Job not found - return 404 with helpful message
    logger.warning(f"Job {job_id} not found in memory or database")
    raise HTTPException(
        status_code=404, 
        detail=f'Job {job_id} not found. It may have been completed and cleaned up, or the server was restarted.'
    )


@router.post('/scrape/jobs/{job_id}/cancel')
async def cancel_job(job_id: str):
    """Cancel a specific scraping job."""
    try:
        job = JOBS.get(job_id)
        if not job:
            # Job not in memory, try to cancel in DB only
            try:
                db.append_job_error(job_id, 'cancelled by user')
                db.finalize_job(job_id, 'cancelled', 'cancelled by user')
                logger.info(f"Job {job_id[:8]} cancelled (was not in memory)")
                return {'cancelled': True}
            except Exception as e:
                logger.warning(f"Failed to cancel job {job_id[:8]} in DB: {e}")
                raise HTTPException(status_code=404, detail='Job not found')
        
        # Mark job as cancelled FIRST (before DB operations)
        # This ensures heartbeat and scraping loops will see the cancellation flag immediately
        job['cancelled'] = True
        job['status'] = 'cancelled'
        
        # Stop heartbeat by setting the flag (heartbeat checks cancelled flag in its loop)
        # The heartbeat will check job.get('cancelled') and stop itself
        
        # Update DB (wrap in try/except to prevent crashes)
        # Even if DB update fails, the job is already cancelled in memory
        try:
            db.append_job_error(job_id, 'cancelled by user')
        except Exception as e:
            logger.warning(f"Failed to append error when cancelling job {job_id[:8]}: {e}")
            # Continue anyway - job is already cancelled in memory
        
        try:
            db.finalize_job(job_id, 'cancelled', 'cancelled by user')
            logger.info(f"Job {job_id[:8]} cancelled successfully")
        except Exception as e:
            logger.warning(f"Failed to finalize job {job_id[:8]} in DB: {e}")
            # Don't fail the cancellation request even if DB update fails
            # The job is already marked as cancelled in memory
        
        return {'cancelled': True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error cancelling job {job_id[:8]}: {e}", exc_info=True)
        # Return success even on error to prevent server crash
        # The job might still be cancelled in memory
        return {'cancelled': True, 'warning': f'Job cancellation requested but error occurred: {str(e)}'}


@router.post('/scrape/jobs/cancel-all')
async def cancel_all_jobs():
    """Cancel all running jobs."""
    try:
        cancelled_count = 0
        
        for job_id, job in list(JOBS.items()):
            if job.get('status') in ['running', 'pending']:
                job['cancelled'] = True
                job['status'] = 'cancelled'
                try:
                    db.append_job_error(job_id, 'cancelled by user (cancel-all)')
                    db.finalize_job(job_id, 'cancelled', 'cancelled by user (cancel-all)')
                except Exception:
                    pass
                cancelled_count += 1
        
        all_jobs = db.get_all_jobs(status='running')
        for job in all_jobs:
            try:
                db.append_job_error(job['id'], 'cancelled by user (cancel-all)')
                db.finalize_job(job['id'], 'cancelled', 'cancelled by user (cancel-all)')
                cancelled_count += 1
            except Exception:
                pass
        
        pending_jobs = db.get_all_jobs(status='pending')
        for job in pending_jobs:
            try:
                db.append_job_error(job['id'], 'cancelled by user (cancel-all)')
                db.finalize_job(job['id'], 'cancelled', 'cancelled by user (cancel-all)')
                cancelled_count += 1
            except Exception:
                pass
        
        return {
            'cancelled': cancelled_count,
            'message': f'Successfully cancelled {cancelled_count} job(s)'
        }
    except Exception as e:
        logger.error(f"Error cancelling all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

