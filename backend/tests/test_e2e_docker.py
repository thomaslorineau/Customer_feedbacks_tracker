"""
E2E Tests for Docker Architecture
=================================
Integration tests for the full Docker stack.
Run with: pytest tests/test_e2e_docker.py -v
"""
import pytest
import httpx
import asyncio
import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 30


def is_server_running():
    """Check if the API server is running."""
    try:
        response = httpx.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def api_client():
    """Create HTTP client for API tests."""
    if not is_server_running():
        pytest.skip("API server is not running")
    
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
        yield client


class TestJobsEndpoints:
    """E2E tests for /jobs/* endpoints."""
    
    def test_jobs_status(self, api_client):
        """Test GET /jobs/status returns queue stats."""
        response = api_client.get("/jobs/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "pending" in data
        assert "processing" in data
        assert "completed_today" in data
        assert "health" in data
        assert data["health"]["status"] == "healthy"
    
    def test_enqueue_scrape_job(self, api_client):
        """Test POST /jobs/scrape enqueues a job."""
        payload = {
            "source": "trustpilot",
            "query": "OVH test",
            "limit": 10,
            "priority": 0
        }
        
        response = api_client.post("/jobs/scrape", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["job_type"] == "scrape_source"
        assert data["status"] == "pending"
    
    def test_get_job_status(self, api_client):
        """Test GET /jobs/{job_id} returns job details."""
        # First create a job
        payload = {"source": "github", "query": "OVH", "limit": 5}
        create_response = api_client.post("/jobs/scrape", json=payload)
        job_id = create_response.json()["job_id"]
        
        # Get job status
        response = api_client.get(f"/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == job_id
        assert data["job_type"] == "scrape_source"
        assert data["status"] in ["pending", "running", "completed", "failed"]
    
    def test_get_nonexistent_job(self, api_client):
        """Test GET /jobs/{job_id} returns 404 for unknown job."""
        response = api_client.get("/jobs/nonexistent-job-id-12345")
        
        assert response.status_code == 404
    
    def test_list_recent_jobs(self, api_client):
        """Test GET /jobs/ returns recent jobs."""
        response = api_client.get("/jobs/?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)
    
    def test_invalid_source_rejected(self, api_client):
        """Test POST /jobs/scrape rejects invalid source."""
        payload = {
            "source": "invalid_source",
            "query": "test",
            "limit": 10
        }
        
        response = api_client.post("/jobs/scrape", json=payload)
        
        assert response.status_code == 400
        assert "Invalid source" in response.json()["detail"]
    
    def test_cancel_pending_job(self, api_client):
        """Test DELETE /jobs/{job_id} cancels pending job."""
        # Create a job
        payload = {"source": "news", "query": "OVH", "limit": 5}
        create_response = api_client.post("/jobs/scrape", json=payload)
        job_id = create_response.json()["job_id"]
        
        # Cancel it
        response = api_client.delete(f"/jobs/{job_id}")
        
        # May succeed or fail depending on if worker picked it up
        assert response.status_code in [200, 400]
    
    def test_trigger_auto_scrape(self, api_client):
        """Test POST /jobs/auto-scrape triggers auto scrape."""
        response = api_client.post("/jobs/auto-scrape")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_type"] == "auto_scrape"
        assert data["status"] == "pending"
    
    def test_trigger_backup(self, api_client):
        """Test POST /jobs/backup triggers backup job."""
        response = api_client.post("/jobs/backup?backup_type=hourly")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_type"] == "backup"


class TestExistingEndpointsStillWork:
    """Verify existing endpoints still work after architecture changes."""
    
    def test_root_endpoint(self, api_client):
        """Test GET / returns welcome message."""
        response = api_client.get("/")
        assert response.status_code == 200
    
    def test_posts_endpoint(self, api_client):
        """Test GET /posts works."""
        response = api_client.get("/posts?limit=5")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_stats_endpoint(self, api_client):
        """Test GET /api/stats works."""
        response = api_client.get("/api/stats")
        assert response.status_code == 200
    
    def test_settings_queries(self, api_client):
        """Test GET /settings/queries works."""
        response = api_client.get("/settings/queries")
        assert response.status_code == 200
    
    def test_api_docs(self, api_client):
        """Test GET /api/docs returns OpenAPI docs."""
        response = api_client.get("/api/docs")
        assert response.status_code == 200


class TestHealthAndMonitoring:
    """Tests for health and monitoring endpoints."""
    
    def test_version_endpoint(self, api_client):
        """Test GET /api/version returns version info."""
        response = api_client.get("/api/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data


if __name__ == "__main__":
    if not is_server_running():
        print("ERROR: API server is not running at", API_BASE_URL)
        print("Start the server first: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        sys.exit(1)
    
    pytest.main([__file__, "-v"])
