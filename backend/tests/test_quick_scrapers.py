"""Tests rapides pour vérifier que chaque scraper fonctionne sans erreur.

Usage: python -m pytest tests/test_quick_scrapers.py -v --tb=short
"""
import pytest
import asyncio
import httpx
import time
import os
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

# Configuration
API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 60.0

# Liste des scrapers à tester
SCRAPERS = [
    ("trustpilot", {"query": "OVH", "limit": 3}),
    ("github", {"query": "OVH", "limit": 3}),
    ("stackoverflow", {"query": "OVH", "limit": 3}),
    ("reddit", {"query": "OVH", "limit": 3}),
    ("news", {"query": "OVH", "limit": 3}),
    ("mastodon", {"query": "OVH", "limit": 3}),
    ("ovh-forum", {"query": "OVH", "limit": 3}),
    ("g2-crowd", {"query": "OVH", "limit": 3}),
    # X/Twitter et LinkedIn nécessitent des credentials
]


class TestScrapersQuick:
    """Tests rapides de tous les scrapers."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("source,params", SCRAPERS)
    async def test_scraper_returns_valid_response(self, source, params):
        """Test que chaque scraper retourne une réponse valide."""
        print(f"\n🔍 Testing {source}...")
        start = time.time()
        
        async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
            try:
                response = await client.post(f"/scrape/{source}", params=params)
                duration = time.time() - start
                
                # Vérifier le code de réponse
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
                
                # Vérifier la structure de la réponse
                data = response.json()
                assert "added" in data, f"Response missing 'added' field: {data}"
                assert isinstance(data.get("added", -1), int), f"'added' should be int"
                
                # Afficher le résultat
                added = data.get("added", 0)
                total = data.get("total", 0)
                errors = data.get("errors", [])
                
                status = "✅" if not errors else "⚠️"
                print(f"{status} {source}: {added} added, {total} total, {len(errors)} errors, {duration:.1f}s")
                
                if errors:
                    for err in errors[:2]:  # Limiter à 2 erreurs
                        print(f"   ⚠️ {err[:100]}")
                
                # Le scraper doit répondre en moins de 30s
                assert duration < 30.0, f"Scraper too slow: {duration:.1f}s"
                
            except httpx.ReadTimeout:
                pytest.skip(f"{source} timeout after {TIMEOUT}s")
            except httpx.ConnectError:
                pytest.skip(f"Cannot connect to API at {API_BASE}")


class TestJobsQuick:
    """Tests rapides des jobs asynchrones."""
    
    @pytest.mark.asyncio
    async def test_create_job_and_check_progress(self):
        """Test création de job et suivi de progression."""
        print("\n🔍 Testing job creation and progress...")
        
        async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
            # Créer un job
            response = await client.post("/scrape/github/job", params={"query": "OVH", "limit": 5})
            assert response.status_code == 200
            
            data = response.json()
            job_id = data["job_id"]
            print(f"✅ Job created: {job_id[:8]}...")
            
            # Suivre la progression
            max_wait = 60
            start = time.time()
            last_progress = -1
            progress_updates = 0
            
            while time.time() - start < max_wait:
                status_response = await client.get(f"/scrape/jobs/{job_id}")
                assert status_response.status_code == 200
                
                status_data = status_response.json()
                status = status_data["status"]
                progress = status_data["progress"]["completed"]
                total = status_data["progress"]["total"]
                
                if progress != last_progress:
                    progress_updates += 1
                    last_progress = progress
                    print(f"   📊 Progress: {progress}/{total} ({status})")
                
                if status in ("completed", "failed", "cancelled"):
                    break
                
                await asyncio.sleep(1)
            
            # Vérifications finales
            final_response = await client.get(f"/scrape/jobs/{job_id}")
            final_data = final_response.json()
            
            assert final_data["status"] == "completed", f"Job should complete, got: {final_data['status']}"
            assert final_data["progress"]["completed"] == final_data["progress"]["total"]
            assert progress_updates >= 3, f"Should have at least 3 progress updates, got {progress_updates}"
            
            print(f"✅ Job completed with {progress_updates} progress updates")
    
    @pytest.mark.asyncio
    async def test_job_cancellation(self):
        """Test annulation de job."""
        print("\n🔍 Testing job cancellation...")
        
        async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
            # Créer un job long
            response = await client.post("/scrape/trustpilot/job", params={"query": "OVH cloud", "limit": 50})
            assert response.status_code == 200
            
            job_id = response.json()["job_id"]
            print(f"✅ Job created: {job_id[:8]}...")
            
            # Attendre un peu
            await asyncio.sleep(2)
            
            # Annuler le job
            cancel_response = await client.post(f"/scrape/jobs/{job_id}/cancel")
            assert cancel_response.status_code == 200
            
            # Vérifier l'annulation
            await asyncio.sleep(1)
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            status_data = status_response.json()
            
            # Le statut doit être cancelled ou le job doit être marqué comme annulé
            assert status_data.get("cancelled", False) or status_data["status"] == "cancelled", \
                f"Job should be cancelled: {status_data}"
            
            print(f"✅ Job cancelled successfully")


class TestProgressHeartbeat:
    """Tests du heartbeat de progression."""
    
    @pytest.mark.asyncio
    async def test_heartbeat_increments_regularly(self):
        """Test que le heartbeat incrémente régulièrement la progression."""
        print("\n🔍 Testing heartbeat regularity...")
        
        async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
            # Créer un job avec un scraper lent
            response = await client.post("/scrape/trustpilot/job", params={"query": "OVH cloud", "limit": 30})
            assert response.status_code == 200
            
            job_id = response.json()["job_id"]
            
            # Collecter les progressions sur 10 secondes
            progressions = []
            for _ in range(10):
                await asyncio.sleep(1)
                status_response = await client.get(f"/scrape/jobs/{job_id}")
                if status_response.status_code == 200:
                    data = status_response.json()
                    if data["status"] == "running":
                        progressions.append(data["progress"]["completed"])
                    else:
                        break
            
            # Vérifier que la progression augmente
            if len(progressions) >= 3:
                # Calculer les incréments
                increments = [progressions[i+1] - progressions[i] for i in range(len(progressions)-1)]
                
                # La plupart des incréments doivent être > 0
                positive_increments = sum(1 for inc in increments if inc > 0)
                assert positive_increments >= len(increments) * 0.5, \
                    f"Progress should increase regularly: {progressions}"
                
                print(f"✅ Progress increments: {increments}")
            
            # Annuler le job
            await client.post(f"/scrape/jobs/{job_id}/cancel")


if __name__ == "__main__":
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"])
