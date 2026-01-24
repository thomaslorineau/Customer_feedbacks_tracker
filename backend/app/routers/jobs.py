"""
Async Job Queue Endpoints
=========================
API endpoints for managing async scraping jobs.
These endpoints enqueue jobs instead of running them synchronously.
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os

from ..job_queue import (
    get_job_queue, Job, JobStatus, JobType,
    enqueue_scrape_job, enqueue_scrape_all_job, 
    enqueue_auto_scrape_job, enqueue_backup_job
)
from .. import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Async Jobs"])

# Check if async mode is enabled
USE_ASYNC_JOBS = os.getenv('USE_ASYNC_JOBS', 'false').lower() == 'true'


# ============================================
# Response Models
# ============================================

class JobResponse(BaseModel):
    """Response for job creation."""
    job_id: str
    job_type: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    id: str
    job_type: str
    status: str
    attempts: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""
    pending: int
    processing: int
    completed_today: int
    health: Dict[str, Any]


class ScrapeJobRequest(BaseModel):
    """Request for scraping job."""
    source: str = Field(..., description="Source to scrape: x, github, stackoverflow, reddit, news, trustpilot, ovh-forum")
    query: str = Field(..., description="Search query")
    limit: int = Field(50, ge=1, le=200, description="Maximum posts to scrape")
    priority: int = Field(0, ge=0, le=10, description="Job priority (higher = processed first)")


class ScrapeAllJobRequest(BaseModel):
    """Request for scraping all sources."""
    queries: List[str] = Field(..., min_items=1, max_items=50, description="Search queries")
    sources: Optional[List[str]] = Field(None, description="Sources to scrape (default: all)")
    priority: int = Field(0, ge=0, le=10, description="Job priority")


# ============================================
# Endpoints
# ============================================

@router.get(
    "/status",
    response_model=QueueStatsResponse,
    summary="Get queue status",
    description="Get current job queue statistics and health status."
)
async def get_queue_status():
    """Get job queue statistics."""
    queue = get_job_queue()
    stats = queue.get_queue_stats()
    health = queue.health_check()
    
    return QueueStatsResponse(
        pending=stats['pending'],
        processing=stats['processing'],
        completed_today=stats['completed_today'],
        health=health
    )


@router.post(
    "/scrape",
    response_model=JobResponse,
    summary="Enqueue scrape job",
    description="""
    Enqueue a scraping job to be processed asynchronously by a worker.
    
    The job will be added to the queue and processed in the background.
    Use the returned job_id to check status via /jobs/{job_id}.
    
    **Available sources:**
    - x (X/Twitter)
    - github
    - stackoverflow
    - reddit
    - news
    - trustpilot
    - ovh-forum
    - mastodon
    - g2-crowd
    - linkedin
    """
)
async def create_scrape_job(request: ScrapeJobRequest):
    """Enqueue a scraping job."""
    valid_sources = ['x', 'github', 'stackoverflow', 'reddit', 'news', 
                     'trustpilot', 'ovh-forum', 'mastodon', 'g2-crowd', 'linkedin']
    
    if request.source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
        )
    
    job_id = enqueue_scrape_job(
        source=request.source,
        query=request.query,
        limit=request.limit,
        priority=request.priority
    )
    
    return JobResponse(
        job_id=job_id,
        job_type=JobType.SCRAPE_SOURCE,
        status=JobStatus.PENDING,
        message=f"Scrape job for {request.source} queued successfully"
    )


@router.post(
    "/scrape-all",
    response_model=JobResponse,
    summary="Enqueue full scrape job",
    description="Enqueue a job to scrape multiple sources with multiple queries."
)
async def create_scrape_all_job(request: ScrapeAllJobRequest):
    """Enqueue a full scrape job."""
    job_id = enqueue_scrape_all_job(
        queries=request.queries,
        sources=request.sources,
        priority=request.priority
    )
    
    sources_str = ', '.join(request.sources) if request.sources else 'all'
    
    return JobResponse(
        job_id=job_id,
        job_type=JobType.SCRAPE_ALL,
        status=JobStatus.PENDING,
        message=f"Full scrape job queued ({len(request.queries)} queries, sources: {sources_str})"
    )


@router.post(
    "/auto-scrape",
    response_model=JobResponse,
    summary="Trigger auto-scrape",
    description="Manually trigger an automatic scrape job using saved keywords."
)
async def trigger_auto_scrape():
    """Trigger automatic scraping."""
    job_id = enqueue_auto_scrape_job()
    
    return JobResponse(
        job_id=job_id,
        job_type=JobType.AUTO_SCRAPE,
        status=JobStatus.PENDING,
        message="Auto-scrape job queued successfully"
    )


@router.post(
    "/backup",
    response_model=JobResponse,
    summary="Trigger backup",
    description="Enqueue a database backup job."
)
async def trigger_backup(
    backup_type: str = Query('hourly', enum=['hourly', 'daily'])
):
    """Trigger database backup."""
    job_id = enqueue_backup_job(backup_type)
    
    return JobResponse(
        job_id=job_id,
        job_type=JobType.BACKUP,
        status=JobStatus.PENDING,
        message=f"{backup_type.capitalize()} backup job queued"
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status",
    description="Get the current status of a specific job."
)
async def get_job_status(job_id: str):
    """Get job status by ID."""
    queue = get_job_queue()
    job = queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        attempts=job.attempts,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        result=job.result
    )


@router.delete(
    "/{job_id}",
    summary="Cancel job",
    description="Cancel a pending job. Running jobs cannot be cancelled."
)
async def cancel_job(job_id: str):
    """Cancel a pending job."""
    queue = get_job_queue()
    job = queue.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status '{job.status}'"
        )
    
    success = queue.cancel_job(job_id)
    
    if success:
        return {"message": "Job cancelled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


@router.get(
    "/",
    summary="List recent jobs",
    description="Get a list of recent completed/failed jobs."
)
async def list_recent_jobs(
    limit: int = Query(20, ge=1, le=100, description="Number of jobs to return")
):
    """List recent jobs."""
    queue = get_job_queue()
    jobs = queue.get_recent_jobs(limit)
    
    return {
        "jobs": [
            {
                "id": j.id,
                "job_type": j.job_type,
                "status": j.status,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
                "duration": _calculate_duration(j)
            }
            for j in jobs
        ],
        "total": len(jobs)
    }


@router.delete(
    "/",
    summary="Clear queue",
    description="Clear all pending jobs from the queue. Use with caution."
)
async def clear_queue():
    """Clear all pending jobs."""
    queue = get_job_queue()
    count = queue.clear_queue()
    
    return {"message": f"Cleared {count} pending jobs"}


def _calculate_duration(job: Job) -> Optional[float]:
    """Calculate job duration in seconds."""
    if not job.started_at or not job.completed_at:
        return None
    
    try:
        start = datetime.fromisoformat(job.started_at)
        end = datetime.fromisoformat(job.completed_at)
        return (end - start).total_seconds()
    except Exception:
        return None
