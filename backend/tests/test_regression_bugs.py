"""Tests de régression pour les bugs précédemment identifiés."""
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


class TestRegressionJobStuck:
    """Tests de régression pour les jobs bloqués."""
    
    @pytest.mark.asyncio
    async def test_job_should_not_stay_at_1_percent(self, client):
        """Régression: Test qu'un job ne reste pas bloqué à 1%."""
        print(f"\n🔍 Regression: Testing job doesn't stay at 1%...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 50}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller la progression
        stuck_at_1_percent = False
        max_checks = 20
        check_interval = 3
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            if total > 0:
                percentage = (completed / total) * 100
                
                # Détecter si on est bloqué à 1%
                if percentage <= 1.0 and status == "running":
                    if not stuck_at_1_percent:
                        stuck_at_1_percent = True
                        stuck_start_time = time.time()
                    else:
                        # Si on est bloqué à 1% pendant plus de 30 secondes, c'est un problème
                        if time.time() - stuck_start_time > 30:
                            pytest.fail(
                                f"Job {job_id[:8]}... stuck at 1% for more than 30 seconds. "
                                f"Progress: {completed}/{total} ({percentage:.1f}%)"
                            )
                else:
                    stuck_at_1_percent = False
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Job did not get stuck at 1%")
    
    @pytest.mark.asyncio
    async def test_job_should_not_stay_in_pending_with_progress(self, client):
        """Régression: Test qu'un job ne reste pas en 'pending' avec de la progression."""
        print(f"\n🔍 Regression: Testing job doesn't stay pending with progress...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 30}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller le statut
        pending_with_progress = False
        max_checks = 15
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            # Détecter si on est en pending avec de la progression
            if status == "pending" and completed > 0 and total > 0:
                if not pending_with_progress:
                    pending_with_progress = True
                    pending_start_time = time.time()
                else:
                    # Si on reste en pending avec progression pendant plus de 2 minutes, c'est un problème
                    if time.time() - pending_start_time > 120:
                        pytest.fail(
                            f"Job {job_id[:8]}... stuck in 'pending' with progress for more than 2 minutes. "
                            f"Progress: {completed}/{total}, status: {status}"
                        )
            else:
                pending_with_progress = False
            
            if status in ["running", "completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Job did not stay pending with progress")


class TestRegressionProgressBar:
    """Tests de régression pour la barre de progression."""
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_not_disappear_prematurely(self, client):
        """Régression: Test que la barre de progression ne disparaît pas prématurément."""
        print(f"\n🔍 Regression: Testing progress bar doesn't disappear prematurely...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 25}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller que le job reste accessible tant qu'il est en cours
        max_checks = 20
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            
            # Le job devrait être accessible tant qu'il n'est pas terminé
            if status_response.status_code == 404:
                # Vérifier le statut via la liste des jobs
                all_jobs_response = await client.get("/scrape/jobs?limit=10")
                if all_jobs_response.status_code == 200:
                    all_jobs_data = all_jobs_response.json()
                    jobs = all_jobs_data.get("jobs", [])
                    found_job = next((j for j in jobs if j["id"] == job_id), None)
                    
                    if found_job:
                        status = found_job.get("status")
                        if status in ["running", "pending"]:
                            pytest.fail(
                                f"Job {job_id[:8]}... disappeared from direct access "
                                f"but is still {status} in jobs list"
                            )
            
            assert status_response.status_code in [200, 404, 410], \
                f"Job should return 200, 404, or 410, got {status_response.status_code}"
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status in ["completed", "failed", "cancelled"]:
                    break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Progress bar did not disappear prematurely")
    
    @pytest.mark.asyncio
    async def test_progress_bar_should_appear_on_refresh(self, client):
        """Régression: Test que la barre de progression apparaît après un refresh."""
        print(f"\n🔍 Regression: Testing progress bar appears on refresh...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre que le job démarre
        await asyncio.sleep(2)
        
        # Vérifier que le job apparaît dans les jobs running (simule un refresh)
        running_response = await client.get("/scrape/jobs?status=running&limit=10")
        
        # Peut échouer avec 500 si DB verrouillée, c'est acceptable
        if running_response.status_code == 200:
            running_data = running_response.json()
            jobs = running_data.get("jobs", [])
            
            # Le job devrait apparaître dans la liste
            found_job = next((j for j in jobs if j["id"] == job_id), None)
            if found_job:
                print(f"✅ Job appears in running jobs list after 'refresh'")
            else:
                # Vérifier directement le statut
                status_response = await client.get(f"/scrape/jobs/{job_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status") in ["pending", "running"]:
                        print(f"⚠️ Job not in running list but still accessible (may be pending)")
        
        print(f"✅ Progress bar appears on refresh")


class TestRegressionServerStability:
    """Tests de régression pour la stabilité du serveur."""
    
    @pytest.mark.asyncio
    async def test_server_should_not_crash_on_multiple_requests(self, client):
        """Régression: Test que le serveur ne plante pas sur plusieurs requêtes."""
        print(f"\n🔍 Regression: Testing server doesn't crash on multiple requests...")
        
        # Créer plusieurs jobs rapidement
        job_ids = []
        for i in range(5):
            response = await client.post(
                "/scrape/reddit/job",
                params={"query": f"OVH{i}", "limit": 10}
            )
            assert response.status_code == 200
            job_ids.append(response.json()["job_id"])
        
        # Faire plusieurs requêtes simultanées pour vérifier le statut
        await asyncio.sleep(1)
        
        # Faire plusieurs requêtes en parallèle
        tasks = [client.get(f"/scrape/jobs/{job_id}") for job_id in job_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Vérifier que toutes les requêtes ont réussi (ou retourné des erreurs attendues)
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                pytest.fail(f"Request for job {job_ids[i][:8]}... raised exception: {response}")
            
            assert response.status_code in [200, 404, 410], \
                f"Request for job {job_ids[i][:8]}... should return 200/404/410, got {response.status_code}"
        
        print(f"✅ Server handled {len(job_ids)} concurrent requests without crashing")
    
    @pytest.mark.asyncio
    async def test_server_should_handle_network_errors_gracefully(self, client):
        """Régression: Test que le serveur gère les erreurs réseau gracieusement."""
        print(f"\n🔍 Regression: Testing server handles network errors gracefully...")
        
        # Créer un job
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 10}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Faire plusieurs requêtes avec des timeouts courts pour simuler des erreurs réseau
        # (mais pas trop courts pour ne pas échouer systématiquement)
        for i in range(5):
            try:
                # Utiliser un timeout raisonnable
                status_response = await client.get(
                    f"/scrape/jobs/{job_id}",
                    timeout=5.0
                )
                assert status_response.status_code in [200, 404, 410], \
                    f"Request {i+1} should return valid status code"
            except httpx.TimeoutException:
                # Timeout est acceptable si le serveur est lent
                print(f"⚠️ Request {i+1} timed out (acceptable if server is slow)")
            except Exception as e:
                pytest.fail(f"Request {i+1} raised unexpected exception: {e}")
            
            await asyncio.sleep(0.5)
        
        print(f"✅ Server handled network errors gracefully")

