"""
Redis Job Queue System
======================
Handles async job processing for scraping operations.
Decouples API from heavy scraping work to prevent server crashes.
"""
from __future__ import annotations
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, TYPE_CHECKING
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Import redis conditionally
redis = None
REDIS_AVAILABLE = False
try:
    import redis as redis_module
    redis = redis_module
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not installed, job queue will use in-memory fallback")


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    SCRAPE_SOURCE = "scrape_source"
    SCRAPE_ALL = "scrape_all"
    AUTO_SCRAPE = "auto_scrape"
    BACKUP = "backup"
    CLEANUP = "cleanup"
    RECHECK_ANSWERED = "recheck_answered"


@dataclass
class Job:
    """Represents a job in the queue."""
    id: str
    job_type: str
    payload: Dict[str, Any]
    status: str = JobStatus.PENDING
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    error_message: str = None
    result: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.id is None:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Job':
        return cls(**data)


class RedisJobQueue:
    """Redis-based job queue with priority support."""
    
    QUEUE_KEY = "ocft:jobs:queue"
    PROCESSING_KEY = "ocft:jobs:processing"
    RESULTS_KEY = "ocft:jobs:results"
    JOB_PREFIX = "ocft:job:"
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or REDIS_URL
        self._client: Optional[Any] = None
    
    @property
    def client(self) -> Any:
        if self._client is None:
            # Increase timeouts for production Docker environments
            # socket_timeout should be higher than bzpopmax timeout to avoid premature disconnections
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=30,  # Increased from 5 to 30 seconds
                socket_connect_timeout=10,  # Increased from 5 to 10 seconds
                socket_keepalive=True,  # Enable keepalive to maintain connection
                socket_keepalive_options={}  # Use system defaults
            )
        return self._client
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        try:
            self.client.ping()
            info = self.client.info('memory')
            return {
                'status': 'healthy',
                'type': 'redis',
                'used_memory': info.get('used_memory_human', 'unknown'),
                'queue_size': self.client.zcard(self.QUEUE_KEY),
                'processing': self.client.scard(self.PROCESSING_KEY)
            }
        except Exception as e:
            return {'status': 'unhealthy', 'type': 'redis', 'error': str(e)}
    
    def enqueue(self, job_type: str, payload: Dict, priority: int = 0) -> str:
        """Add a job to the queue."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            priority=priority
        )
        
        # Store job data
        self.client.set(
            f"{self.JOB_PREFIX}{job.id}",
            json.dumps(job.to_dict()),
            ex=86400 * 7  # Expire after 7 days
        )
        
        # Add to priority queue (higher priority = processed first)
        # Score = priority * 1000000 - timestamp (so higher priority and older = first)
        score = priority * 1000000 - time.time()
        self.client.zadd(self.QUEUE_KEY, {job.id: score})
        
        logger.info(f"Job enqueued: {job.id} ({job_type})")
        return job.id
    
    def dequeue(self, timeout: int = 0) -> Optional[Job]:
        """Get the next job from queue (blocking)."""
        try:
            # Get highest priority job
            if timeout > 0:
                try:
                    result = self.client.bzpopmax(self.QUEUE_KEY, timeout=timeout)
                    if not result:
                        return None
                    job_id = result[1]
                except Exception as timeout_error:
                    # Handle timeout and connection errors gracefully
                    error_str = str(timeout_error).lower()
                    error_type = type(timeout_error).__name__
                    
                    # Check for timeout errors (can be TimeoutError or generic timeout messages)
                    if (error_type == "TimeoutError" or 
                        "timeout" in error_str or 
                        "timed out" in error_str or
                        "reading from socket" in error_str):
                        # Normal timeout - no job available, this is expected
                        return None
                    elif ("connection" in error_str or 
                          "socket" in error_str or
                          error_type == "ConnectionError"):
                        logger.warning(f"Redis connection error during dequeue: {timeout_error}")
                        # Try to reconnect on next call
                        self.close()
                        return None
                    else:
                        # Re-raise unexpected errors
                        logger.error(f"Unexpected error during dequeue: {timeout_error}")
                        raise
            else:
                result = self.client.zpopmax(self.QUEUE_KEY, count=1)
                if not result:
                    return None
                job_id = result[0][0]
            
            # Mark as processing
            self.client.sadd(self.PROCESSING_KEY, job_id)
            
            # Get job data
            job_data = self.client.get(f"{self.JOB_PREFIX}{job_id}")
            if not job_data:
                self.client.srem(self.PROCESSING_KEY, job_id)
                return None
            
            job = Job.from_dict(json.loads(job_data))
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()
            job.attempts += 1
            
            # Update job data
            self.client.set(
                f"{self.JOB_PREFIX}{job_id}",
                json.dumps(job.to_dict()),
                ex=86400 * 7
            )
            
            return job
            
        except Exception as e:
            logger.error(f"Error dequeuing job: {e}")
            return None
    
    def complete(self, job_id: str, result: Dict = None):
        """Mark a job as completed."""
        self._finish_job(job_id, JobStatus.COMPLETED, result=result)
    
    def fail(self, job_id: str, error: str, retry: bool = True):
        """Mark a job as failed, optionally retry."""
        job_data = self.client.get(f"{self.JOB_PREFIX}{job_id}")
        if not job_data:
            return
        
        job = Job.from_dict(json.loads(job_data))
        
        if retry and job.attempts < job.max_attempts:
            # Re-queue with lower priority
            job.status = JobStatus.PENDING
            job.error_message = error
            self.client.set(
                f"{self.JOB_PREFIX}{job_id}",
                json.dumps(job.to_dict()),
                ex=86400 * 7
            )
            
            # Add back to queue with delay (exponential backoff)
            delay = min(300, 30 * (2 ** job.attempts))  # Max 5 min delay
            score = (job.priority - 1) * 1000000 - time.time() + delay
            self.client.zadd(self.QUEUE_KEY, {job_id: score})
            self.client.srem(self.PROCESSING_KEY, job_id)
            
            logger.info(f"Job {job_id} will retry in {delay}s (attempt {job.attempts}/{job.max_attempts})")
        else:
            self._finish_job(job_id, JobStatus.FAILED, error_message=error)
    
    def _finish_job(self, job_id: str, status: str, 
                    result: Dict = None, error_message: str = None):
        """Finish a job (complete or fail)."""
        job_data = self.client.get(f"{self.JOB_PREFIX}{job_id}")
        if not job_data:
            return
        
        job = Job.from_dict(json.loads(job_data))
        job.status = status
        job.completed_at = datetime.now().isoformat()
        job.result = result
        job.error_message = error_message
        
        # Update job data
        self.client.set(
            f"{self.JOB_PREFIX}{job_id}",
            json.dumps(job.to_dict()),
            ex=86400 * 7
        )
        
        # Store in results (keep last 1000)
        self.client.lpush(self.RESULTS_KEY, job_id)
        self.client.ltrim(self.RESULTS_KEY, 0, 999)
        
        # Remove from processing
        self.client.srem(self.PROCESSING_KEY, job_id)
        
        logger.info(f"Job {job_id} finished with status: {status}")
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        job_data = self.client.get(f"{self.JOB_PREFIX}{job_id}")
        if not job_data:
            return None
        return Job.from_dict(json.loads(job_data))
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        return {
            'pending': self.client.zcard(self.QUEUE_KEY),
            'processing': self.client.scard(self.PROCESSING_KEY),
            'completed_today': self._count_completed_today()
        }
    
    def _count_completed_today(self) -> int:
        """Count jobs completed today."""
        today = datetime.now().date().isoformat()
        count = 0
        for job_id in self.client.lrange(self.RESULTS_KEY, 0, -1):
            job = self.get_job(job_id)
            if job and job.completed_at and job.completed_at.startswith(today):
                count += 1
        return count
    
    def get_recent_jobs(self, limit: int = 20) -> List[Job]:
        """Get recent completed/failed jobs."""
        jobs = []
        for job_id in self.client.lrange(self.RESULTS_KEY, 0, limit - 1):
            job = self.get_job(job_id)
            if job:
                jobs.append(job)
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        removed = self.client.zrem(self.QUEUE_KEY, job_id)
        if removed:
            self._finish_job(job_id, JobStatus.CANCELLED)
            return True
        return False
    
    def clear_queue(self) -> int:
        """Clear all pending jobs."""
        count = self.client.zcard(self.QUEUE_KEY)
        self.client.delete(self.QUEUE_KEY)
        return count


class InMemoryJobQueue:
    """Fallback in-memory queue for development/testing."""
    
    def __init__(self):
        self._queue: List[Job] = []
        self._processing: Dict[str, Job] = {}
        self._results: List[Job] = []
    
    def health_check(self) -> Dict[str, Any]:
        return {
            'status': 'healthy',
            'type': 'in-memory',
            'queue_size': len(self._queue),
            'processing': len(self._processing)
        }
    
    def enqueue(self, job_type: str, payload: Dict, priority: int = 0) -> str:
        job = Job(
            id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            priority=priority
        )
        self._queue.append(job)
        self._queue.sort(key=lambda j: (-j.priority, j.created_at))
        logger.info(f"Job enqueued (in-memory): {job.id}")
        return job.id
    
    def dequeue(self, timeout: int = 0) -> Optional[Job]:
        if not self._queue:
            return None
        job = self._queue.pop(0)
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        job.attempts += 1
        self._processing[job.id] = job
        return job
    
    def complete(self, job_id: str, result: Dict = None):
        if job_id in self._processing:
            job = self._processing.pop(job_id)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            job.result = result
            self._results.insert(0, job)
            if len(self._results) > 100:
                self._results = self._results[:100]
    
    def fail(self, job_id: str, error: str, retry: bool = True):
        if job_id in self._processing:
            job = self._processing.pop(job_id)
            if retry and job.attempts < job.max_attempts:
                job.status = JobStatus.PENDING
                job.error_message = error
                self._queue.append(job)
            else:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now().isoformat()
                job.error_message = error
                self._results.insert(0, job)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        for job in self._queue + list(self._processing.values()) + self._results:
            if job.id == job_id:
                return job
        return None
    
    def get_queue_stats(self) -> Dict[str, int]:
        return {
            'pending': len(self._queue),
            'processing': len(self._processing),
            'completed_today': len([j for j in self._results 
                                   if j.completed_at and 
                                   j.completed_at.startswith(datetime.now().date().isoformat())])
        }
    
    def get_recent_jobs(self, limit: int = 20) -> List[Job]:
        return self._results[:limit]
    
    def cancel_job(self, job_id: str) -> bool:
        for i, job in enumerate(self._queue):
            if job.id == job_id:
                self._queue.pop(i)
                job.status = JobStatus.CANCELLED
                self._results.insert(0, job)
                return True
        return False
    
    def clear_queue(self) -> int:
        count = len(self._queue)
        self._queue.clear()
        return count
    
    def close(self):
        pass


# ============================================
# Global queue instance
# ============================================

_job_queue = None


def get_job_queue():
    """Get the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        if REDIS_AVAILABLE:
            try:
                _job_queue = RedisJobQueue()
                _job_queue.client.ping()  # Test connection
                logger.info("Using Redis job queue")
            except Exception as e:
                logger.warning(f"Redis not available ({e}), using in-memory queue")
                _job_queue = InMemoryJobQueue()
        else:
            _job_queue = InMemoryJobQueue()
    return _job_queue


def close_job_queue():
    """Close the job queue connection."""
    global _job_queue
    if _job_queue:
        _job_queue.close()
        _job_queue = None


# ============================================
# Convenience functions
# ============================================

def enqueue_scrape_job(source: str, query: str, limit: int = 50, 
                       priority: int = 0) -> str:
    """Enqueue a scraping job."""
    return get_job_queue().enqueue(
        JobType.SCRAPE_SOURCE,
        {
            'source': source,
            'query': query,
            'limit': limit,
            'use_keyword_expansion': True
        },
        priority=priority
    )


def enqueue_scrape_all_job(queries: List[str], sources: List[str] = None,
                           priority: int = 0) -> str:
    """Enqueue a job to scrape all sources."""
    return get_job_queue().enqueue(
        JobType.SCRAPE_ALL,
        {
            'queries': queries,
            'sources': sources or ['trustpilot', 'github', 'stackoverflow', 
                                   'reddit', 'news', 'ovh-forum'],
            'limit_per_query': 50
        },
        priority=priority
    )


def enqueue_auto_scrape_job() -> str:
    """Enqueue automatic scraping job (scheduled)."""
    return get_job_queue().enqueue(
        JobType.AUTO_SCRAPE,
        {'triggered_by': 'scheduler'},
        priority=1  # Lower priority than manual
    )


def enqueue_backup_job(backup_type: str = 'hourly') -> str:
    """Enqueue a database backup job."""
    return get_job_queue().enqueue(
        JobType.BACKUP,
        {'backup_type': backup_type},
        priority=2  # High priority
    )
