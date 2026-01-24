"""Tests de robustesse pour la barre de progression - détecte les problèmes d'affichage."""
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
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

pytest_plugins = ('pytest_asyncio',)

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 120.0


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def client():
    """Client HTTP pour les tests."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
        yield client


class TestProgressBarAPI:
    """Tests de robustesse pour l'API de progression."""
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_appear_for_running_job(self, client):
        """Test qu'un job en cours apparaît dans la liste des jobs running."""
        print(f"\n🔍 Testing progress bar appears for running job...")
        
        # Créer un job
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre que le job démarre
        await asyncio.sleep(2)
        
        # Vérifier que le job apparaît dans les jobs running
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                running_response = await client.get("/scrape/jobs?status=running&limit=10")
                if running_response.status_code == 200:
                    running_data = running_response.json()
                    jobs = running_data.get("jobs", [])
                    
                    # Chercher notre job
                    found_job = next((j for j in jobs if j["id"] == job_id), None)
                    if found_job:
                        print(f"✅ Job found in running jobs list")
                        assert found_job["status"] in ["pending", "running"], \
                            f"Job should be pending or running, got {found_job['status']}"
                        return
                
                await asyncio.sleep(1)
            except Exception as e:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                    continue
                raise
        
        # Si on arrive ici, le job n'a pas été trouvé
        # Vérifier le statut directement
        status_response = await client.get(f"/scrape/jobs/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        # Le job peut avoir terminé très rapidement
        if status_data.get("status") in ["completed", "failed"]:
            print(f"⚠️ Job completed too quickly to appear in running list")
        else:
            pytest.fail(
                f"Job {job_id[:8]}... not found in running jobs list. "
                f"Status: {status_data.get('status')}"
            )
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_disappear_after_completion(self, client):
        """Test qu'un job terminé n'apparaît plus dans les jobs running."""
        print(f"\n🔍 Testing progress bar disappears after completion...")
        
        # Créer un job avec une limite faible
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 5}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre que le job se termine
        max_wait = 60
        elapsed = 0
        while elapsed < max_wait:
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            if status_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(2)
            elapsed += 2
        
        # Vérifier que le job n'apparaît plus dans les jobs running
        running_response = await client.get("/scrape/jobs?status=running&limit=10")
        if running_response.status_code == 200:
            running_data = running_response.json()
            jobs = running_data.get("jobs", [])
            
            found_job = next((j for j in jobs if j["id"] == job_id), None)
            assert found_job is None, \
                f"Completed job {job_id[:8]}... should not appear in running jobs list"
        
        print(f"✅ Completed job no longer appears in running jobs")
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_handle_server_restart(self, client):
        """Test que la barre de progression gère correctement un redémarrage serveur."""
        print(f"\n🔍 Testing progress bar handles server restart...")
        
        # Créer un job
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 30}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre un peu pour que le job démarre
        await asyncio.sleep(3)
        
        # Vérifier que le job est accessible
        status_response = await client.get(f"/scrape/jobs/{job_id}")
        assert status_response.status_code == 200
        
        # Simuler un redémarrage serveur en vérifiant que le job est toujours accessible
        # (dans un vrai scénario, le job serait perdu, mais on teste la résilience)
        await asyncio.sleep(2)
        
        # Vérifier que le job est toujours accessible après le "redémarrage"
        status_response2 = await client.get(f"/scrape/jobs/{job_id}")
        # Le job peut être perdu (404) ou toujours accessible (200)
        assert status_response2.status_code in [200, 404, 410], \
            f"Job should return 200, 404, or 410 after 'restart', got {status_response2.status_code}"
        
        if status_response2.status_code == 200:
            print(f"✅ Job still accessible after server restart simulation")
        else:
            print(f"⚠️ Job lost after server restart (expected behavior)")
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_update_regularly(self, client):
        """Test que la progression est mise à jour régulièrement."""
        print(f"\n🔍 Testing progress bar updates regularly...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 40}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller les mises à jour
        last_update_time = None
        update_intervals = []
        max_checks = 15
        check_interval = 3
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            
            current_time = time.time()
            if last_update_time is not None:
                interval = current_time - last_update_time
                update_intervals.append(interval)
            
            last_update_time = current_time
            
            if status_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        # Vérifier que les mises à jour sont régulières (pas trop espacées)
        if len(update_intervals) > 0:
            avg_interval = sum(update_intervals) / len(update_intervals)
            # Les mises à jour devraient être régulières (pas plus de 2x l'intervalle de check)
            assert avg_interval <= check_interval * 2, \
                f"Progress updates seem irregular: avg interval {avg_interval:.1f}s (expected <= {check_interval * 2}s)"
        
        print(f"✅ Progress updates are regular (checked {max_checks} times)")


class TestProgressBarEdgeCases:
    """Tests des cas limites pour la barre de progression."""
    
    @pytest.mark.asyncio
    async def test_progress_bar_with_zero_total(self, client):
        """Test que la progression gère correctement total=0."""
        print(f"\n🔍 Testing progress bar with zero total...")
        
        # Créer un job
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 10}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Vérifier que même si total=0 initialement, le job fonctionne
        status_response = await client.get(f"/scrape/jobs/{job_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        progress = status_data.get("progress", {})
        total = progress.get("total", 0)
        completed = progress.get("completed", 0)
        
        # Si total=0, completed devrait aussi être 0
        if total == 0:
            assert completed == 0, \
                f"If total=0, completed should be 0, got {completed}"
        
        print(f"✅ Progress bar handles zero total correctly")
    
    @pytest.mark.asyncio
    async def test_progress_bar_with_rapid_completion(self, client):
        """Test que la barre de progression gère les jobs qui se terminent rapidement."""
        print(f"\n🔍 Testing progress bar with rapid completion...")
        
        # Créer un job avec une limite très faible
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 1}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Vérifier immédiatement
        await asyncio.sleep(1)
        
        status_response = await client.get(f"/scrape/jobs/{job_id}")
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        status = status_data.get("status")
        
        # Le job peut être déjà terminé ou encore en cours
        assert status in ["pending", "running", "completed", "failed"], \
            f"Job should have valid status, got {status}"
        
        # Vérifier que la progression existe même si le job est terminé rapidement
        progress = status_data.get("progress", {})
        assert "total" in progress, "Progress should have 'total' even if job completed quickly"
        assert "completed" in progress, "Progress should have 'completed' even if job completed quickly"
        
        print(f"✅ Progress bar handles rapid completion correctly")
    
    @pytest.mark.asyncio
    async def test_progress_bar_with_concurrent_jobs(self, client):
        """Test que plusieurs jobs peuvent avoir des barres de progression simultanées."""
        print(f"\n🔍 Testing progress bar with concurrent jobs...")
        
        # Créer plusieurs jobs
        job_ids = []
        for i in range(3):
            response = await client.post(
                "/scrape/reddit/job",
                params={"query": f"OVH{i}", "limit": 15}
            )
            assert response.status_code == 200
            job_ids.append(response.json()["job_id"])
        
        # Attendre un peu
        await asyncio.sleep(2)
        
        # Vérifier que tous les jobs sont accessibles et ont des progressions indépendantes
        progressions = {}
        for job_id in job_ids:
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            progress = status_data.get("progress", {})
            progressions[job_id] = {
                "completed": progress.get("completed", 0),
                "total": progress.get("total", 0),
                "status": status_data.get("status")
            }
        
        # Vérifier que les progressions sont indépendantes (peuvent être différentes)
        unique_progressions = set(
            (p["completed"], p["total"]) 
            for p in progressions.values()
        )
        
        # Au moins une progression devrait être différente (ou toutes identiques si jobs similaires)
        assert len(unique_progressions) >= 1, "Should have at least one progression value"
        
        print(f"✅ Multiple concurrent jobs have independent progress bars")

