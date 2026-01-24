"""
Unit Tests for Docker Architecture Components
=============================================
Tests for job_queue, db_postgres, worker, and scheduler_service.
"""
import pytest
import os
import sys
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestJobQueue:
    """Tests for the job queue system."""
    
    def test_import_job_queue(self):
        """Test that job_queue module can be imported."""
        from app.job_queue import (
            get_job_queue, Job, JobStatus, JobType,
            enqueue_scrape_job, enqueue_scrape_all_job
        )
        assert Job is not None
        assert JobStatus.PENDING == "pending"
        assert JobType.SCRAPE_SOURCE == "scrape_source"
    
    def test_job_creation(self):
        """Test Job dataclass creation."""
        from app.job_queue import Job, JobStatus
        
        job = Job(
            id="test-123",
            job_type="scrape_source",
            payload={"source": "trustpilot", "query": "OVH"}
        )
        
        assert job.id == "test-123"
        assert job.status == JobStatus.PENDING
        assert job.payload["source"] == "trustpilot"
        assert job.attempts == 0
        assert job.created_at is not None
    
    def test_job_to_dict(self):
        """Test Job serialization."""
        from app.job_queue import Job
        
        job = Job(
            id="test-456",
            job_type="backup",
            payload={"backup_type": "hourly"}
        )
        
        data = job.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "test-456"
        assert data["payload"]["backup_type"] == "hourly"
    
    def test_job_from_dict(self):
        """Test Job deserialization."""
        from app.job_queue import Job
        
        data = {
            "id": "test-789",
            "job_type": "cleanup",
            "payload": {},
            "status": "pending",
            "priority": 5,
            "attempts": 0,
            "max_attempts": 3,
            "created_at": "2026-01-25T00:00:00",
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "result": None
        }
        
        job = Job.from_dict(data)
        assert job.id == "test-789"
        assert job.priority == 5
    
    def test_in_memory_queue_enqueue(self):
        """Test InMemoryJobQueue enqueue."""
        from app.job_queue import InMemoryJobQueue
        
        queue = InMemoryJobQueue()
        job_id = queue.enqueue("scrape_source", {"source": "github"})
        
        assert job_id is not None
        assert len(job_id) == 36  # UUID length
        
        stats = queue.get_queue_stats()
        assert stats["pending"] == 1
    
    def test_in_memory_queue_dequeue(self):
        """Test InMemoryJobQueue dequeue."""
        from app.job_queue import InMemoryJobQueue, JobStatus
        
        queue = InMemoryJobQueue()
        queue.enqueue("test", {"data": 1})
        
        job = queue.dequeue()
        
        assert job is not None
        assert job.status == JobStatus.RUNNING
        assert job.attempts == 1
        
        stats = queue.get_queue_stats()
        assert stats["pending"] == 0
        assert stats["processing"] == 1
    
    def test_in_memory_queue_complete(self):
        """Test InMemoryJobQueue complete."""
        from app.job_queue import InMemoryJobQueue, JobStatus
        
        queue = InMemoryJobQueue()
        job_id = queue.enqueue("test", {})
        job = queue.dequeue()
        
        queue.complete(job_id, {"result": "success"})
        
        completed_job = queue.get_job(job_id)
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.result["result"] == "success"
    
    def test_in_memory_queue_fail_with_retry(self):
        """Test InMemoryJobQueue fail with retry."""
        from app.job_queue import InMemoryJobQueue, JobStatus
        
        queue = InMemoryJobQueue()
        job_id = queue.enqueue("test", {})
        queue.dequeue()
        
        queue.fail(job_id, "Test error", retry=True)
        
        stats = queue.get_queue_stats()
        assert stats["pending"] == 1  # Job re-queued
    
    def test_in_memory_queue_priority(self):
        """Test InMemoryJobQueue respects priority."""
        from app.job_queue import InMemoryJobQueue
        
        queue = InMemoryJobQueue()
        queue.enqueue("low", {}, priority=1)
        queue.enqueue("high", {}, priority=10)
        queue.enqueue("medium", {}, priority=5)
        
        job1 = queue.dequeue()
        job2 = queue.dequeue()
        job3 = queue.dequeue()
        
        assert job1.job_type == "high"
        assert job2.job_type == "medium"
        assert job3.job_type == "low"
    
    def test_enqueue_scrape_job(self):
        """Test enqueue_scrape_job convenience function."""
        from app.job_queue import enqueue_scrape_job, get_job_queue
        
        # Reset queue
        import app.job_queue as jq
        jq._job_queue = None
        
        job_id = enqueue_scrape_job("trustpilot", "OVH VPS", limit=25, priority=3)
        
        assert job_id is not None
        
        queue = get_job_queue()
        job = queue.get_job(job_id)
        assert job.payload["source"] == "trustpilot"
        assert job.payload["query"] == "OVH VPS"
        assert job.payload["limit"] == 25
        assert job.priority == 3
    
    def test_queue_health_check(self):
        """Test queue health check."""
        from app.job_queue import InMemoryJobQueue
        
        queue = InMemoryJobQueue()
        health = queue.health_check()
        
        assert health["status"] == "healthy"
        assert health["type"] == "in-memory"


class TestJobsRouter:
    """Tests for the jobs API router."""
    
    def test_import_router(self):
        """Test that jobs router can be imported."""
        from app.routers.jobs import router
        assert router is not None
        assert router.prefix == "/jobs"
    
    def test_response_models(self):
        """Test response models are valid."""
        from app.routers.jobs import (
            JobResponse, JobStatusResponse, QueueStatsResponse,
            ScrapeJobRequest, ScrapeAllJobRequest
        )
        
        # Test JobResponse
        resp = JobResponse(
            job_id="123",
            job_type="scrape_source",
            status="pending",
            message="Test"
        )
        assert resp.job_id == "123"
        
        # Test ScrapeJobRequest validation
        req = ScrapeJobRequest(
            source="trustpilot",
            query="OVH",
            limit=50,
            priority=0
        )
        assert req.source == "trustpilot"


class TestDBPostgres:
    """Tests for PostgreSQL adapter (mocked)."""
    
    def test_import_db_postgres(self):
        """Test that db_postgres module can be imported."""
        from app.db_postgres import USE_POSTGRES
        # Should be False since DATABASE_URL not set
        assert USE_POSTGRES == False
    
    def test_postgres_functions_exist(self):
        """Test that all expected functions exist."""
        from app import db_postgres
        
        expected_functions = [
            'pg_insert_post',
            'pg_get_all_posts',
            'pg_get_post_count',
            'pg_delete_post',
            'pg_url_exists',
            'pg_get_sentiment_stats',
            'pg_get_source_stats',
            'pg_get_saved_queries',
            'pg_add_saved_query',
            'pg_enqueue_job',
            'pg_health_check'
        ]
        
        for func_name in expected_functions:
            assert hasattr(db_postgres, func_name), f"Missing function: {func_name}"


class TestWorker:
    """Tests for worker module."""
    
    def test_worker_import(self):
        """Test worker can be imported."""
        # We can't import worker directly as it runs main()
        # Just check the file exists
        import os
        worker_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "worker.py"
        )
        assert os.path.exists(worker_path)


class TestSchedulerService:
    """Tests for scheduler service module."""
    
    def test_scheduler_import(self):
        """Test scheduler service file exists."""
        import os
        scheduler_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scheduler_service.py"
        )
        assert os.path.exists(scheduler_path)


class TestDockerFiles:
    """Tests for Docker configuration files."""
    
    def test_dockerfile_exists(self):
        """Test Dockerfile exists."""
        import os
        dockerfile = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )
        assert os.path.exists(dockerfile)
    
    def test_dockerfile_worker_exists(self):
        """Test Dockerfile.worker exists."""
        import os
        dockerfile = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile.worker"
        )
        assert os.path.exists(dockerfile)
    
    def test_docker_compose_exists(self):
        """Test docker-compose.yml exists."""
        import os
        compose_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "docker-compose.yml"
        )
        assert os.path.exists(compose_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
