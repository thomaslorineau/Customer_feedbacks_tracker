"""Fixtures et utilitaires pour les tests de robustesse."""
import pytest
import asyncio
import httpx
import time
from typing import Optional, Dict, List


def wait_for_job_status(
    client: httpx.AsyncClient,
    job_id: str,
    expected_statuses: List[str],
    max_wait: int = 60,
    check_interval: int = 2
) -> Optional[Dict]:
    """
    Attend qu'un job atteigne un des statuts attendus.
    
    Returns:
        Les données du job si trouvé, None sinon
    """
    elapsed = 0
    while elapsed < max_wait:
        try:
            response = await client.get(f"/scrape/jobs/{job_id}")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in expected_statuses:
                    return data
            elif response.status_code in [404, 410]:
                # Job n'existe plus
                return None
        except Exception:
            pass
        
        await asyncio.sleep(check_interval)
        elapsed += check_interval
    
    return None


def assert_progress_valid(progress: Dict, job_id: str = ""):
    """Assertion helper pour valider la progression."""
    assert "total" in progress, f"Progress should have 'total' (job: {job_id[:8]})"
    assert "completed" in progress, f"Progress should have 'completed' (job: {job_id[:8]})"
    
    total = progress.get("total", 0)
    completed = progress.get("completed", 0)
    
    assert isinstance(total, int), f"Progress.total should be int, got {type(total)}"
    assert isinstance(completed, int), f"Progress.completed should be int, got {type(completed)}"
    assert total >= 0, f"Progress.total should be >= 0, got {total}"
    assert completed >= 0, f"Progress.completed should be >= 0, got {completed}"
    assert completed <= total or total == 0, \
        f"Progress.completed ({completed}) should not exceed total ({total})"


def assert_job_status_valid(status: str, job_id: str = ""):
    """Assertion helper pour valider le statut d'un job."""
    valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]
    assert status in valid_statuses, \
        f"Invalid job status: {status} (valid: {valid_statuses}) (job: {job_id[:8]})"


def detect_stuck_job(
    progress_history: List[tuple],
    stuck_threshold: int = 5
) -> bool:
    """
    Détecte si un job est bloqué basé sur l'historique de progression.
    
    Args:
        progress_history: Liste de tuples (completed, total, status)
        stuck_threshold: Nombre de checks consécutifs sans changement pour considérer comme bloqué
    
    Returns:
        True si le job semble bloqué
    """
    if len(progress_history) < stuck_threshold:
        return False
    
    # Vérifier les derniers N checks
    recent = progress_history[-stuck_threshold:]
    
    # Si tous les checks récents ont la même progression, le job est bloqué
    first_completed, first_total = recent[0][0], recent[0][1]
    all_same = all(
        p[0] == first_completed and p[1] == first_total 
        for p in recent
    )
    
    # Mais seulement si le total > 0 (sinon c'est normal)
    return all_same and first_total > 0

