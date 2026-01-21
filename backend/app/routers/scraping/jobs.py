"""Job processing functions and endpoints for async scraping jobs."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
import threading
import asyncio
import logging
import os

from ... import db
from ...scraper import x_scraper, stackoverflow, news, github, reddit, trustpilot, ovh_forum, mastodon, g2_crowd, linkedin
from ...scraper import keyword_expander
from ...analysis import sentiment, country_detection, relevance_scorer
from ...config import keywords_base
from .base import should_insert_post, log_scraping, RELEVANCE_THRESHOLD
from .endpoints import KeywordsPayload

logger = logging.getLogger(__name__)

router = APIRouter()

# Job tracking
JOBS = {}

# Track problematic job IDs that should be blocked (to prevent spam)
BLOCKED_JOB_IDS = {
    '84d4fd06-ae2e-43a1-9387-e037a668f75a': True  # Known stale job ID
}
BLOCKED_JOB_REQUEST_COUNT = {}  # Track request count per blocked job


async def _run_scrape_for_source_async(source: str, query: str, limit: int, use_keyword_expansion: bool = True):
    """Async version: Call the appropriate scraper and insert results into DB; return count added."""
    try:
        async_mapper = {
            'github': lambda q, l: github.scrape_github_issues_async(q, limit=l),
            'trustpilot': lambda q, l: trustpilot.scrape_trustpilot_reviews_async(q, limit=l),
            'stackoverflow': lambda q, l: stackoverflow.scrape_stackoverflow_async(q, limit=l),
            'reddit': lambda q, l: reddit.scrape_reddit_async(q, limit=l),
            'news': lambda q, l: news.scrape_google_news_async(q, limit=l),
            'mastodon': lambda q, l: mastodon.scrape_mastodon_async(q, limit=l),
            'linkedin': lambda q, l: linkedin.scrape_linkedin_async(q, limit=l),
        }
        sync_mapper = {
            'x': lambda q, l: x_scraper.scrape_x(q, limit=l),
            'ovh-forum': lambda q, l: ovh_forum.scrape_ovh_forum(q, limit=l),
            'g2-crowd': lambda q, l: g2_crowd.scrape_g2_crowd(q, limit=l),
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
            try:
                per_query_limit = max(limit // len(queries_to_try), 20)  # Minimum 20 par query pour meilleure couverture
                
                if is_async:
                    items = await func(query_variant, per_query_limit)
                else:
                    items = await asyncio.to_thread(func, query_variant, per_query_limit)
                
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
        filtered_by_relevance = 0
        for it in all_items:
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
                    'relevance_score': relevance_score,
                }):
                    added += 1
                else:
                    duplicates += 1
            except Exception:
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
        'news': lambda q, l: news.scrape_google_news(q, limit=l),
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
    job['status'] = 'running'
    try:
        db.create_job_record(job_id)
    except Exception:
        pass
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
        
        async def progress_heartbeat():
            nonlocal completed_count
            while job.get('status') == 'running' and completed_count < total_tasks:
                await asyncio.sleep(1.0)
                if job.get('cancelled'):
                    break
                if completed_count > 0:
                    job['progress']['completed'] = completed_count
                    try:
                        db.update_job_progress(job_id, total_tasks, completed_count)
                    except Exception:
                        pass
        
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
                    job['progress']['completed'] = completed_count
                    try:
                        db.update_job_progress(job_id, total_tasks, completed_count)
                    except Exception:
                        pass
                    
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
                    job['progress']['completed'] = completed_count
                    try:
                        db.update_job_progress(job_id, total_tasks, completed_count)
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
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))
                finally:
                    new_loop.close()
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
        else:
            loop.run_until_complete(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))
    except RuntimeError:
        asyncio.run(_process_keyword_job_async(job_id, keywords, limit, concurrency, delay))


async def _process_single_source_job_async(job_id: str, source: str, query: str, limit: int):
    """Process a single source scraping job with granular progress updates."""
    job = JOBS.get(job_id)
    if job is None:
        return
    
    job['status'] = 'running'
    
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
    scraping_start_time = None
    
    async def progress_heartbeat():
        nonlocal heartbeat_step, scraping_start_time
        import time as time_module
        scraping_start_time = time_module.time()
        logger.info(f"[{source}] Starting heartbeat for job {job_id[:8]}... (step {heartbeat_step} -> {scraping_end})")
        
        target_duration = 60.0  # Increased to 60 seconds for longer scrapings (Trustpilot can take time)
        steps_to_progress = scraping_end - scraping_start
        
        while heartbeat_running and heartbeat_step < scraping_end:
            await asyncio.sleep(0.5)  # Update every 0.5 seconds
            if not heartbeat_running:
                logger.info(f"[{source}] Heartbeat stopped (heartbeat_running=False)")
                break
            
            current_time = time_module.time()
            if scraping_start_time:
                elapsed = current_time - scraping_start_time
                # Calculate progress based on elapsed time, but cap at scraping_end - 1
                if elapsed > 0 and target_duration > 0:
                    time_based_step = scraping_start + int((elapsed / target_duration) * steps_to_progress)
                    time_based_step = min(time_based_step, scraping_end - 1)
                    
                    # Always move forward, but use time-based if it's ahead
                    if time_based_step > heartbeat_step:
                        heartbeat_step = time_based_step
                    elif heartbeat_step < scraping_end - 1:
                        # Increment by at least 1 every 0.5 seconds to show progress
                        heartbeat_step = min(heartbeat_step + 1, scraping_end - 1)
                else:
                    # Fallback: increment slowly
                    if heartbeat_step < scraping_end - 1:
                        heartbeat_step = min(heartbeat_step + 1, scraping_end - 1)
            else:
                if heartbeat_step < scraping_end - 1:
                    heartbeat_step += 1
            
            # Always update progress in memory and DB every iteration
            job['progress']['completed'] = heartbeat_step
            job['progress']['total'] = total_steps
            try:
                db.update_job_progress(job_id, total_steps, heartbeat_step)
                # Log every 5% to avoid spam but show progress
                if heartbeat_step % 5 == 0 or heartbeat_step == scraping_start + 1:
                    logger.info(f"[{source}] Heartbeat progress: {heartbeat_step}/{total_steps} ({heartbeat_step*100//total_steps}%)")
            except Exception as e:
                logger.warning(f"[{source}] Failed to update job progress in DB: {e}")
        
        logger.info(f"[{source}] Heartbeat finished at step {heartbeat_step}")
    
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
        except Exception:
            pass
        
        logger.info(f"[{source}] Starting heartbeat task for job {job_id[:8]}...")
        heartbeat_task = asyncio.create_task(progress_heartbeat())
        
        try:
            added = await _run_scrape_for_source_async(source, query, limit, use_keyword_expansion=False)
        finally:
            heartbeat_running = False
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            job['progress']['completed'] = scraping_end
            try:
                db.update_job_progress(job_id, total_steps, scraping_end)
            except Exception:
                pass
        
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
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            def run_in_new_loop():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(_process_single_source_job_async(job_id, source, query, limit))
                finally:
                    new_loop.close()
            t = threading.Thread(target=run_in_new_loop, daemon=True)
            t.start()
        else:
            loop.run_until_complete(_process_single_source_job_async(job_id, source, query, limit))
    except RuntimeError:
        asyncio.run(_process_single_source_job_async(job_id, source, query, limit))


@router.post('/scrape/{source}/job')
async def start_single_source_job(
    source: str,
    query: str = "",
    limit: int = 100
):
    """Start a background job for a single scraper source."""
    valid_sources = ['x', 'github', 'stackoverflow', 'news', 'reddit', 'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}")
    
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        'id': job_id,
        'status': 'pending',
        'progress': {'total': 1, 'completed': 0},
        'results': [],
        'errors': [],
        'cancelled': False,
        'error': None,
    }
    
    try:
        db.create_job_record(job_id)
        db.update_job_progress(job_id, 1, 0)
    except Exception:
        pass
    
    t = threading.Thread(target=_process_single_source_job, args=(job_id, source, query, limit), daemon=True)
    t.start()
    
    return {
        'job_id': job_id,
        'source': source,
        'query': query,
        'limit': limit,
        'total_tasks': 1
    }


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
                if db_job.get('status') in ('completed', 'failed', 'cancelled'):
                    if db_job['status'] != job.get('status'):
                        job['status'] = db_job['status']
                    if db_job.get('progress'):
                        job['progress'] = db_job['progress']
        except Exception as e:
            logger.debug(f"Could not sync job {job_id} with DB: {e}")
        
        if 'progress' not in job:
            job['progress'] = {'total': 0, 'completed': 0}
        
        return job
    
    # If not in memory, check database (for completed/failed jobs)
    try:
        rec = db.get_job_record(job_id)
        if rec:
            # Ensure progress exists
            if 'progress' not in rec:
                rec['progress'] = {'total': 0, 'completed': 0}
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
    job = JOBS.get(job_id)
    if not job:
        try:
            db.append_job_error(job_id, 'cancelled by user')
            db.finalize_job(job_id, 'cancelled', 'cancelled by user')
            return {'cancelled': True}
        except Exception:
            raise HTTPException(status_code=404, detail='Job not found')
    job['cancelled'] = True
    try:
        db.append_job_error(job_id, 'cancelled by user')
        db.finalize_job(job_id, 'cancelled', 'cancelled by user')
    except Exception:
        pass
    return {'cancelled': True}


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

