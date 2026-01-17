"""Tests E2E complets pour tous les scrapers."""
import pytest
import asyncio
import httpx
import time
from typing import Dict, List
import json


API_BASE = "http://127.0.0.1:8000"
TIMEOUT = 30.0


class TestE2EScrapers:
    """Tests end-to-end pour tous les scrapers."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Client HTTP pour les tests."""
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_trustpilot_e2e(self, client):
        """Test E2E complet pour Trustpilot."""
        response = await client.post("/scrape/trustpilot", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_github_e2e(self, client):
        """Test E2E complet pour GitHub."""
        response = await client.post("/scrape/github", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_stackoverflow_e2e(self, client):
        """Test E2E complet pour StackOverflow."""
        response = await client.post("/scrape/stackoverflow", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_reddit_e2e(self, client):
        """Test E2E complet pour Reddit."""
        response = await client.post("/scrape/reddit", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_news_e2e(self, client):
        """Test E2E complet pour Google News."""
        response = await client.post("/scrape/news", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_mastodon_e2e(self, client):
        """Test E2E complet pour Mastodon."""
        response = await client.post("/scrape/mastodon", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_linkedin_e2e(self, client):
        """Test E2E complet pour LinkedIn."""
        response = await client.post("/scrape/linkedin", params={"query": "OVH", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert "added" in data
        assert isinstance(data["added"], int)
        # LinkedIn peut retourner 0 si pas de credentials
        assert data["added"] >= 0
    
    @pytest.mark.asyncio
    async def test_concurrent_scraping(self, client):
        """Test scraping concurrent de plusieurs sources."""
        tasks = [
            client.post("/scrape/trustpilot", params={"query": "OVH", "limit": 3}),
            client.post("/scrape/github", params={"query": "OVH", "limit": 3}),
            client.post("/scrape/stackoverflow", params={"query": "OVH", "limit": 3}),
            client.post("/scrape/reddit", params={"query": "OVH", "limit": 3}),
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Vérifier que tous les appels ont réussi
        success_count = 0
        for result in results:
            if isinstance(result, Exception):
                continue
            if result.status_code == 200:
                success_count += 1
        
        assert success_count >= 3, f"Seulement {success_count}/4 scrapers ont réussi"
        assert duration < 15.0, f"Trop lent: {duration}s (devrait être < 15s)"
    
    @pytest.mark.asyncio
    async def test_logs_api(self, client):
        """Test API des logs."""
        # Test récupération des logs
        response = await client.get("/api/logs", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "count" in data
        assert isinstance(data["logs"], list)
        
        # Test filtrage par source
        response = await client.get("/api/logs", params={"source": "Trustpilot", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        if data["logs"]:
            assert all(log["source"] == "Trustpilot" for log in data["logs"])
        
        # Test filtrage par niveau
        response = await client.get("/api/logs", params={"level": "error", "limit": 5})
        assert response.status_code == 200
        data = response.json()
        if data["logs"]:
            assert all(log["level"] == "error" for log in data["logs"])
    
    @pytest.mark.asyncio
    async def test_keywords_job(self, client):
        """Test job de scraping avec keywords."""
        payload = {"keywords": ["OVH", "ovhcloud"]}
        response = await client.post("/scrape/keywords", params={"limit": 3, "concurrency": 2, "delay": 0.5}, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        
        job_id = data["job_id"]
        
        # Attendre un peu pour que le job démarre
        await asyncio.sleep(2)
        
        # Vérifier le statut du job
        response = await client.get(f"/scrape/jobs/{job_id}")
        assert response.status_code == 200
        job_data = response.json()
        assert "status" in job_data
        assert job_data["status"] in ["running", "completed", "failed", "cancelled"]
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test gestion des erreurs."""
        # Test avec query invalide
        response = await client.post("/scrape/trustpilot", params={"query": "", "limit": 5})
        assert response.status_code == 200  # Devrait retourner 200 avec added=0
        
        # Test avec limit trop élevé
        response = await client.post("/scrape/github", params={"query": "OVH", "limit": 10000})
        assert response.status_code == 200
        data = response.json()
        assert data["added"] >= 0


class TestE2ELogsUI:
    """Tests E2E pour l'interface UI des logs."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Client HTTP pour les tests."""
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    @pytest.mark.asyncio
    async def test_logs_page_loads(self, client):
        """Test que la page des logs se charge."""
        response = await client.get("/logs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Scraping Logs" in response.text
    
    @pytest.mark.asyncio
    async def test_logs_api_endpoint(self, client):
        """Test endpoint API des logs."""
        response = await client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


