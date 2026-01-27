"""Tests E2E complets pour tous les scrapers."""
import pytest
import asyncio
import httpx
import time
from typing import Dict, List
import json
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
TIMEOUT = 60.0  # Augmenté pour les scrapers lents


class TestE2EScrapers:
    """Tests end-to-end pour tous les scrapers."""
    
    @pytest.fixture(scope="class")
    def client(self):
        """Client HTTP pour les tests."""
        return httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT)
    
    def validate_scrape_result(self, data: dict, source: str):
        """Valide la structure d'une réponse de scraping."""
        assert "added" in data, f"Response should contain 'added' field: {data}"
        assert isinstance(data["added"], int), f"'added' should be int, got {type(data['added'])}"
        assert data["added"] >= 0, f"'added' should be >= 0, got {data['added']}"
        print(f"✅ {source}: {data['added']} posts ajoutés")
    
    @pytest.mark.asyncio
    async def test_trustpilot_e2e(self, client):
        """Test E2E complet pour Trustpilot."""
        print(f"\n🔍 Testing Trustpilot scraper...")
        start_time = time.time()
        response = await client.post("/scrape/trustpilot", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "Trustpilot")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_x_twitter_e2e(self, client):
        """Test E2E complet pour X/Twitter."""
        print(f"\n🔍 Testing X/Twitter scraper...")
        start_time = time.time()
        response = await client.post("/scrape/x", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "X/Twitter")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_github_e2e(self, client):
        """Test E2E complet pour GitHub."""
        print(f"\n🔍 Testing GitHub scraper...")
        start_time = time.time()
        response = await client.post("/scrape/github", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "GitHub")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_stackoverflow_e2e(self, client):
        """Test E2E complet pour StackOverflow."""
        print(f"\n🔍 Testing StackOverflow scraper...")
        start_time = time.time()
        response = await client.post("/scrape/stackoverflow", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "StackOverflow")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_reddit_e2e(self, client):
        """Test E2E complet pour Reddit."""
        print(f"\n🔍 Testing Reddit scraper...")
        start_time = time.time()
        response = await client.post("/scrape/reddit", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "Reddit")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_ovh_forum_e2e(self, client):
        """Test E2E complet pour OVH Forum."""
        print(f"\n🔍 Testing OVH Forum scraper...")
        start_time = time.time()
        response = await client.post("/scrape/ovh-forum", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "OVH Forum")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_g2_crowd_e2e(self, client):
        """Test E2E complet pour G2 Crowd."""
        print(f"\n🔍 Testing G2 Crowd scraper...")
        start_time = time.time()
        response = await client.post("/scrape/g2-crowd", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "G2 Crowd")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_mastodon_e2e(self, client):
        """Test E2E complet pour Mastodon."""
        print(f"\n🔍 Testing Mastodon scraper...")
        start_time = time.time()
        response = await client.post("/scrape/mastodon", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "Mastodon")
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_linkedin_e2e(self, client):
        """Test E2E complet pour LinkedIn."""
        print(f"\n🔍 Testing LinkedIn scraper...")
        start_time = time.time()
        response = await client.post("/scrape/linkedin", params={"query": "OVH", "limit": 5})
        duration = time.time() - start_time
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        self.validate_scrape_result(data, "LinkedIn")
        # LinkedIn peut retourner 0 si pas de credentials
        assert duration < 30.0, f"Trop lent: {duration}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_scraping(self, client):
        """Test scraping concurrent de plusieurs sources."""
        print(f"\n🔍 Testing concurrent scraping...")
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
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Task {i} raised exception: {result}")
                continue
            if result.status_code == 200:
                success_count += 1
                data = result.json()
                print(f"  ✅ Concurrent task {i}: {data.get('added', 0)} posts")
            else:
                errors.append(f"Task {i} returned {result.status_code}: {result.text}")
        
        if errors:
            print(f"  ⚠️ Errors: {errors}")
        
        assert success_count >= 3, f"Seulement {success_count}/4 scrapers ont réussi. Errors: {errors}"
        assert duration < 60.0, f"Trop lent: {duration}s (devrait être < 60s)"
        print(f"  ✅ Concurrent scraping completed in {duration:.2f}s")
    
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
        print(f"\n🔍 Testing keywords job...")
        payload = {"keywords": ["OVH", "ovhcloud"]}
        response = await client.post("/scrape/keywords", params={"limit": 3, "concurrency": 2, "delay": 0.5}, json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "job_id" in data, f"Response should contain 'job_id': {data}"
        
        job_id = data["job_id"]
        print(f"  📋 Job ID: {job_id}")
        
        # Attendre un peu pour que le job démarre
        await asyncio.sleep(2)
        
        # Vérifier le statut du job
        response = await client.get(f"/scrape/jobs/{job_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        job_data = response.json()
        assert "status" in job_data, f"Job data should contain 'status': {job_data}"
        assert job_data["status"] in ["running", "completed", "failed", "cancelled"], \
            f"Invalid status: {job_data['status']}"
        print(f"  📊 Job status: {job_data['status']}")
        
        # Si le job est en cours, vérifier la progression
        if job_data["status"] == "running":
            assert "progress" in job_data or "current" in job_data, "Running job should have progress info"
        
        # Si le job est terminé, vérifier les résultats
        if job_data["status"] == "completed":
            assert "total_added" in job_data or "added" in job_data, "Completed job should have results"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client):
        """Test gestion des erreurs."""
        print(f"\n🔍 Testing error handling...")
        
        # Test avec query invalide (vide)
        response = await client.post("/scrape/trustpilot", params={"query": "", "limit": 5})
        assert response.status_code == 200, "Empty query should return 200 with added=0"
        data = response.json()
        assert data["added"] >= 0, "Should return valid added count even with empty query"
        print(f"  ✅ Empty query handled correctly: {data['added']} posts")
        
        # Test avec limit trop élevé
        response = await client.post("/scrape/github", params={"query": "OVH", "limit": 10000})
        assert response.status_code == 200, "High limit should return 200"
        data = response.json()
        assert data["added"] >= 0, "Should return valid added count even with high limit"
        print(f"  ✅ High limit handled correctly: {data['added']} posts")
        
        # Test avec endpoint inexistant
        response = await client.post("/scrape/invalid-source", params={"query": "OVH", "limit": 5})
        # Devrait retourner 404 ou 422
        assert response.status_code in [404, 422, 500], \
            f"Invalid endpoint should return error status, got {response.status_code}"
        print(f"  ✅ Invalid endpoint handled correctly: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_database_integration(self, client):
        """Test que les posts sont bien sauvegardés en base."""
        print(f"\n🔍 Testing database integration...")
        
        # Scraper quelques posts
        response = await client.post("/scrape/stackoverflow", params={"query": "OVH", "limit": 3})
        assert response.status_code == 200
        scrape_data = response.json()
        added_count = scrape_data.get("added", 0)
        print(f"  📊 Posts ajoutés: {added_count}")
        
        # Vérifier que les posts sont dans la base via l'API
        response = await client.get("/posts", params={"limit": 100, "offset": 0})
        assert response.status_code == 200
        posts_data = response.json()
        assert isinstance(posts_data, list), "Should return list of posts"
        
        # Vérifier qu'il y a des posts Stack Overflow
        stackoverflow_posts = [p for p in posts_data if p.get("source") == "Stack Overflow"]
        if added_count > 0:
            assert len(stackoverflow_posts) > 0, "Should have Stack Overflow posts in database"
            print(f"  ✅ Found {len(stackoverflow_posts)} Stack Overflow posts in database")
            
            # Vérifier la structure d'un post
            post = stackoverflow_posts[0]
            required_fields = ["source", "content", "url"]
            for field in required_fields:
                assert field in post, f"Post should have '{field}' field"
            print(f"  ✅ Post structure is valid")
    
    @pytest.mark.asyncio
    async def test_all_scrapers_health_check(self, client):
        """Test rapide de santé pour tous les scrapers."""
        print(f"\n🔍 Running health check on all scrapers...")
        
        scrapers = [
            ("trustpilot", "Trustpilot"),
            ("x", "X/Twitter"),
            ("github", "GitHub"),
            ("stackoverflow", "StackOverflow"),
            ("reddit", "Reddit"),
            ("ovh-forum", "OVH Forum"),
            ("mastodon", "Mastodon"),
            ("g2-crowd", "G2 Crowd"),
            ("linkedin", "LinkedIn"),
        ]
        
        results = {}
        for endpoint, name in scrapers:
            try:
                start_time = time.time()
                response = await client.post(f"/scrape/{endpoint}", params={"query": "OVH", "limit": 1}, timeout=30.0)
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    results[name] = {
                        "status": "ok",
                        "added": data.get("added", 0),
                        "duration": duration
                    }
                    print(f"  ✅ {name}: {data.get('added', 0)} posts in {duration:.2f}s")
                else:
                    results[name] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "duration": duration
                    }
                    print(f"  ❌ {name}: HTTP {response.status_code}")
            except Exception as e:
                results[name] = {
                    "status": "exception",
                    "error": str(e)
                }
                print(f"  ❌ {name}: Exception - {e}")
        
        # Au moins 70% des scrapers doivent fonctionner
        success_count = sum(1 for r in results.values() if r.get("status") == "ok")
        total_count = len(scrapers)
        success_rate = success_count / total_count
        
        print(f"\n📊 Health check results: {success_count}/{total_count} scrapers OK ({success_rate*100:.1f}%)")
        assert success_rate >= 0.7, f"Only {success_count}/{total_count} scrapers are working (need at least 70%)"


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


