"""Tests de robustesse pour les jobs de scraping - détecte les problèmes avant qu'ils ne se produisent."""
import pytest
import asyncio
import httpx
import time
import os
import sys
from typing import Dict, Optional

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


class TestJobStability:
    """Tests de stabilité pour détecter les jobs bloqués."""
    
    @pytest.mark.asyncio
    async def test_job_should_not_stay_pending_too_long(self, client):
        """Test qu'un job ne reste pas bloqué en 'pending' trop longtemps."""
        print(f"\n🔍 Testing job doesn't stay pending too long...")
        
        # Créer un job
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 10}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller le statut pendant 30 secondes maximum
        max_pending_time = 30  # secondes
        check_interval = 2  # secondes
        elapsed = 0
        
        while elapsed < max_pending_time:
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status != "pending":
                print(f"✅ Job moved from pending to {status} after {elapsed}s")
                assert status in ["running", "completed", "failed", "cancelled"], \
                    f"Job should not be stuck in pending, got {status}"
                return
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # Si on arrive ici, le job est resté en pending trop longtemps
        pytest.fail(f"Job {job_id[:8]}... stayed in 'pending' status for {elapsed}s (max allowed: {max_pending_time}s)")
    
    @pytest.mark.asyncio
    async def test_job_progress_should_increase(self, client):
        """Test que la progression d'un job augmente régulièrement."""
        print(f"\n🔍 Testing job progress increases...")
        
        # Créer un job avec une limite élevée pour qu'il prenne du temps
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 50}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre que le job démarre
        await asyncio.sleep(3)
        
        # Vérifier la progression plusieurs fois
        progress_values = []
        max_checks = 10
        check_interval = 3  # secondes
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            progress_values.append((completed, total, status))
            
            # Si le job est terminé, arrêter
            if status in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        # Vérifier que la progression a changé
        assert len(progress_values) >= 2, "Should have at least 2 progress checks"
        
        first_progress = progress_values[0]
        last_progress = progress_values[-1]
        
        # La progression devrait avoir augmenté OU le job devrait être terminé
        if last_progress[2] in ["completed", "failed", "cancelled"]:
            print(f"✅ Job finished with status: {last_progress[2]}")
        elif last_progress[0] > first_progress[0]:
            print(f"✅ Progress increased: {first_progress[0]}/{first_progress[1]} -> {last_progress[0]}/{last_progress[1]}")
        elif last_progress[1] != first_progress[1]:
            print(f"✅ Total changed: {first_progress[1]} -> {last_progress[1]}")
        else:
            # Vérifier si le job est vraiment bloqué ou s'il progresse lentement
            # Si le total est > 0 et qu'on a plusieurs checks, vérifier qu'au moins un a changé
            if len(progress_values) >= 3:
                # Vérifier qu'au moins une valeur a changé entre les checks
                has_progress = any(
                    progress_values[i][0] != progress_values[i-1][0] or 
                    progress_values[i][1] != progress_values[i-1][1]
                    for i in range(1, len(progress_values))
                )
                if not has_progress and last_progress[1] > 0:
                    pytest.fail(
                        f"Job {job_id[:8]}... progress appears stuck: "
                        f"{first_progress[0]}/{first_progress[1]} -> {last_progress[0]}/{last_progress[1]} "
                        f"(checked {len(progress_values)} times over {len(progress_values) * check_interval}s)"
                    )
    
    @pytest.mark.asyncio
    async def test_job_should_complete_or_fail_within_reasonable_time(self, client):
        """Test qu'un job se termine dans un délai raisonnable."""
        print(f"\n🔍 Testing job completes within reasonable time...")
        
        # Créer un job avec une limite raisonnable
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Attendre que le job se termine (max 2 minutes pour 20 posts)
        max_wait_time = 120  # secondes
        check_interval = 5  # secondes
        elapsed = 0
        
        while elapsed < max_wait_time:
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status in ["completed", "failed", "cancelled"]:
                print(f"✅ Job finished with status: {status} after {elapsed}s")
                return
            
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # Si on arrive ici, le job n'a pas terminé dans le délai raisonnable
        pytest.fail(
            f"Job {job_id[:8]}... did not complete within {max_wait_time}s. "
            f"Last status: {status_data.get('status')}, "
            f"progress: {status_data.get('progress', {})}"
        )


class TestJobProgressConsistency:
    """Tests de cohérence de la progression."""
    
    @pytest.mark.asyncio
    async def test_progress_should_not_decrease(self, client):
        """Test que la progression ne diminue jamais."""
        print(f"\n🔍 Testing progress never decreases...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 30}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Surveiller la progression
        last_completed = -1
        max_checks = 15
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            
            # Vérifier que completed ne diminue jamais
            if last_completed >= 0:
                assert completed >= last_completed, \
                    f"Progress decreased: {last_completed} -> {completed} (check {i+1})"
            
            last_completed = completed
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Progress never decreased (checked {max_checks} times)")
    
    @pytest.mark.asyncio
    async def test_progress_should_not_exceed_total(self, client):
        """Test que completed ne dépasse jamais total."""
        print(f"\n🔍 Testing progress never exceeds total...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        max_checks = 20
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            # Vérifier que completed <= total (sauf si total est 0)
            if total > 0:
                assert completed <= total, \
                    f"Progress exceeds total: {completed} > {total} (check {i+1})"
            
            if status in ["completed", "failed", "cancelled"]:
                # À la fin, completed devrait être <= total
                if status == "completed" and total > 0:
                    assert completed <= total, \
                        f"Completed job has progress exceeding total: {completed} > {total}"
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Progress never exceeded total (checked {max_checks} times)")
    
    @pytest.mark.asyncio
    async def test_progress_percentage_should_be_valid(self, client):
        """Test que le pourcentage de progression est valide."""
        print(f"\n🔍 Testing progress percentage is valid...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        max_checks = 15
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            # Calculer le pourcentage
            if total > 0:
                percentage = (completed / total) * 100
                assert 0 <= percentage <= 100, \
                    f"Invalid percentage: {percentage}% (completed={completed}, total={total})"
            
            if status_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Progress percentage always valid (checked {max_checks} times)")


class TestJobErrorHandling:
    """Tests de gestion des erreurs."""
    
    @pytest.mark.asyncio
    async def test_job_should_handle_invalid_job_id_gracefully(self, client):
        """Test que les job IDs invalides sont gérés correctement."""
        print(f"\n🔍 Testing invalid job ID handling...")
        
        invalid_ids = [
            "invalid-id",
            "12345",
            "",
            "not-a-uuid",
            "00000000-0000-0000-0000-000000000000"
        ]
        
        for invalid_id in invalid_ids:
            response = await client.get(f"/scrape/jobs/{invalid_id}")
            # Devrait retourner 404 ou 410, pas 500
            assert response.status_code in [404, 410], \
                f"Invalid job ID '{invalid_id}' should return 404/410, got {response.status_code}"
        
        print(f"✅ All invalid job IDs handled gracefully")
    
    @pytest.mark.asyncio
    async def test_job_should_handle_cancellation_gracefully(self, client):
        """Test que l'annulation d'un job fonctionne même s'il est déjà terminé."""
        print(f"\n🔍 Testing job cancellation handling...")
        
        # Créer un job avec une limite faible pour qu'il se termine rapidement
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
            status_data = status_response.json()
            if status_data.get("status") in ["completed", "failed"]:
                break
            await asyncio.sleep(2)
            elapsed += 2
        
        # Essayer d'annuler le job même s'il est terminé
        cancel_response = await client.post(f"/scrape/jobs/{job_id}/cancel")
        # Devrait retourner 200 même si le job est terminé (idempotent)
        assert cancel_response.status_code == 200, \
            f"Cancelling completed job should return 200, got {cancel_response.status_code}"
        
        print(f"✅ Job cancellation handled gracefully even when completed")
    
    @pytest.mark.asyncio
    async def test_multiple_jobs_should_not_interfere(self, client):
        """Test que plusieurs jobs peuvent tourner en parallèle sans interférence."""
        print(f"\n🔍 Testing multiple jobs don't interfere...")
        
        # Créer plusieurs jobs
        job_ids = []
        for i in range(3):
            response = await client.post(
                "/scrape/reddit/job",
                params={"query": f"OVH{i}", "limit": 10}
            )
            assert response.status_code == 200
            job_ids.append(response.json()["job_id"])
        
        # Vérifier que tous les jobs sont accessibles et ont des statuts valides
        await asyncio.sleep(2)
        
        for job_id in job_ids:
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200, \
                f"Job {job_id[:8]}... should be accessible"
            
            status_data = status_response.json()
            status = status_data.get("status")
            assert status in ["pending", "running", "completed", "failed", "cancelled"], \
                f"Job {job_id[:8]}... has invalid status: {status}"
            
            # Vérifier que chaque job a sa propre progression
            progress = status_data.get("progress", {})
            assert "total" in progress, f"Job {job_id[:8]}... should have progress.total"
            assert "completed" in progress, f"Job {job_id[:8]}... should have progress.completed"
        
        print(f"✅ Multiple jobs run independently without interference")


class TestJobStateTransitions:
    """Tests des transitions d'état des jobs."""
    
    @pytest.mark.asyncio
    async def test_job_state_transitions_are_valid(self, client):
        """Test que les transitions d'état sont valides."""
        print(f"\n🔍 Testing job state transitions...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 15}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Suivre les transitions d'état
        states_seen = []
        max_checks = 20
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            # Ajouter l'état s'il a changé
            if not states_seen or states_seen[-1] != status:
                states_seen.append(status)
                print(f"  State transition: {states_seen[-2] if len(states_seen) > 1 else 'initial'} -> {status}")
            
            # Vérifier que les transitions sont valides
            valid_transitions = {
                "pending": ["running", "cancelled"],
                "running": ["completed", "failed", "cancelled"],
                "completed": [],  # État final
                "failed": [],  # État final
                "cancelled": []  # État final
            }
            
            if len(states_seen) > 1:
                prev_state = states_seen[-2]
                curr_state = states_seen[-1]
                
                if prev_state in valid_transitions:
                    assert curr_state in valid_transitions[prev_state] or curr_state == prev_state, \
                        f"Invalid state transition: {prev_state} -> {curr_state}"
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        # Vérifier qu'on a vu au moins une transition
        assert len(states_seen) >= 1, "Should have seen at least one state"
        
        # Vérifier qu'on a terminé dans un état final
        final_state = states_seen[-1]
        assert final_state in ["completed", "failed", "cancelled"], \
            f"Job should end in a final state, got {final_state}"
        
        print(f"✅ Valid state transitions: {' -> '.join(states_seen)}")


class TestJobDataIntegrity:
    """Tests d'intégrité des données des jobs."""
    
    @pytest.mark.asyncio
    async def test_job_data_structure_is_consistent(self, client):
        """Test que la structure des données d'un job est cohérente."""
        print(f"\n🔍 Testing job data structure consistency...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 10}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        max_checks = 10
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            
            # Vérifier les champs requis
            assert "id" in status_data, "Job should have 'id' field"
            assert "status" in status_data, "Job should have 'status' field"
            assert "progress" in status_data, "Job should have 'progress' field"
            
            # Vérifier que l'ID correspond
            assert status_data["id"] == job_id, \
                f"Job ID mismatch: expected {job_id}, got {status_data['id']}"
            
            # Vérifier le statut
            assert status_data["status"] in ["pending", "running", "completed", "failed", "cancelled"], \
                f"Invalid status: {status_data['status']}"
            
            # Vérifier la structure de progress
            progress = status_data["progress"]
            assert isinstance(progress, dict), "Progress should be a dictionary"
            assert "total" in progress, "Progress should have 'total' field"
            assert "completed" in progress, "Progress should have 'completed' field"
            assert isinstance(progress["total"], int), "Progress.total should be int"
            assert isinstance(progress["completed"], int), "Progress.completed should be int"
            
            if status_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Job data structure consistent across {max_checks} checks")
    
    @pytest.mark.asyncio
    async def test_job_progress_values_are_sane(self, client):
        """Test que les valeurs de progression sont raisonnables."""
        print(f"\n🔍 Testing job progress values are sane...")
        
        response = await client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        max_checks = 15
        check_interval = 2
        
        for i in range(max_checks):
            status_response = await client.get(f"/scrape/jobs/{job_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            # Vérifier que les valeurs sont raisonnables
            assert completed >= 0, f"Completed should be >= 0, got {completed}"
            assert total >= 0, f"Total should be >= 0, got {total}"
            
            # Si total > 0, completed devrait être <= total
            if total > 0:
                assert completed <= total, \
                    f"Completed ({completed}) should not exceed total ({total})"
            
            # Vérifier que total n'est pas absurde (max 10000 pour un job normal)
            if total > 10000:
                pytest.fail(f"Total seems too high: {total} (might indicate a bug)")
            
            if status_data.get("status") in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(check_interval)
        
        print(f"✅ Progress values are sane (checked {max_checks} times)")

