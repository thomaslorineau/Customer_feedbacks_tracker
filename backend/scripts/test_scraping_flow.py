#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test complet pour valider le flux scraping → affichage.

Ce script teste :
1. Création d'un job de scraping
2. Suivi de la progression du job
3. Vérification de l'affichage dans l'API
4. Vérification que le job se termine correctement
"""
import requests
import time
import sys
import os
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

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 30


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def check_server_health() -> bool:
    """Vérifie que le serveur est accessible."""
    try:
        response = requests.get(f"{API_BASE}/api/version", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print_error(f"Server not accessible: {e}")
        return False


def create_job(source: str, query: str = "OVH", limit: int = 10) -> Optional[str]:
    """Crée un job de scraping et retourne son ID."""
    try:
        print_info(f"Creating {source} job with query='{query}', limit={limit}...")
        response = requests.post(
            f"{API_BASE}/scrape/{source}/job",
            params={"query": query, "limit": limit},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Failed to create job: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        job_id = data.get("job_id")
        
        if not job_id:
            print_error(f"No job_id in response: {data}")
            return None
        
        print_success(f"Job created: {job_id[:8]}...")
        return job_id
    
    except Exception as e:
        print_error(f"Error creating job: {e}")
        return None


def get_job_status(job_id: str) -> Optional[Dict]:
    """Récupère le statut d'un job."""
    try:
        response = requests.get(f"{API_BASE}/scrape/jobs/{job_id}", timeout=TIMEOUT)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            print_error(f"Failed to get job status: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    
    except Exception as e:
        print_error(f"Error getting job status: {e}")
        return None


def get_running_jobs() -> list:
    """Récupère la liste des jobs en cours."""
    try:
        response = requests.get(
            f"{API_BASE}/scrape/jobs",
            params={"status": "running", "limit": 10},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Failed to get running jobs: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        return data.get("jobs", [])
    
    except Exception as e:
        print_error(f"Error getting running jobs: {e}")
        return []


def monitor_job_progress(job_id: str, max_wait: int = 120) -> bool:
    """Surveille la progression d'un job jusqu'à sa complétion."""
    print_info(f"Monitoring job {job_id[:8]}...")
    
    start_time = time.time()
    last_progress = None
    stuck_count = 0
    max_stuck_count = 10  # Si la progression ne change pas pendant 10 polls, considérer comme bloqué
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while time.time() - start_time < max_wait:
        try:
            status_data = get_job_status(job_id)
            
            if status_data is None:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print_warning(f"Job {job_id[:8]}... not found after {max_consecutive_errors} attempts (may have been cleaned up)")
                    return False
                time.sleep(2)
                continue
            
            consecutive_errors = 0  # Reset error count on success
            
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", {})
            completed = progress.get("completed", 0)
            total = progress.get("total", 0)
            
            current_progress = (completed, total, status)
            
            # Vérifier si la progression a changé
            if last_progress == current_progress:
                stuck_count += 1
            else:
                stuck_count = 0
            
            if total > 0:
                percentage = (completed / total) * 100
                print_info(f"  Status: {status}, Progress: {completed}/{total} ({percentage:.1f}%)")
            else:
                print_info(f"  Status: {status}, Progress: {completed}/{total}")
            
            # Vérifier si le job est terminé
            if status in ["completed", "failed", "cancelled"]:
                print_success(f"Job finished with status: {status}")
                return status == "completed"
            
            # Vérifier si le job est bloqué (mais seulement si on a un total > 0)
            if stuck_count >= max_stuck_count and total > 0:
                print_warning(f"Job appears stuck: progress hasn't changed in {max_stuck_count} polls")
                # Ne pas retourner False immédiatement, continuer à surveiller
                if stuck_count >= max_stuck_count * 2:
                    print_error(f"Job confirmed stuck after {max_stuck_count * 2} polls")
                    return False
            
            last_progress = current_progress
            time.sleep(2)  # Poll toutes les 2 secondes
        
        except Exception as e:
            consecutive_errors += 1
            print_warning(f"Error monitoring job: {e} (attempt {consecutive_errors}/{max_consecutive_errors})")
            if consecutive_errors >= max_consecutive_errors:
                print_error(f"Too many consecutive errors, stopping monitoring")
                return False
            time.sleep(2)
    
    print_error(f"Job did not complete within {max_wait} seconds")
    return False


def test_single_source_job(source: str) -> bool:
    """Test complet pour un job de source unique."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Testing {source} scraper{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    # Créer le job
    job_id = create_job(source, query="OVH", limit=10)
    if not job_id:
        return False
    
    # Attendre un peu pour que le job démarre
    time.sleep(2)
    
    # Vérifier que le job apparaît dans la liste des jobs en cours
    running_jobs = get_running_jobs()
    job_found = any(job.get("id") == job_id for job in running_jobs)
    
    if job_found:
        print_success(f"Job {job_id[:8]}... found in running jobs list")
    else:
        print_warning(f"Job {job_id[:8]}... not found in running jobs (may have completed quickly)")
    
    # Surveiller la progression
    success = monitor_job_progress(job_id, max_wait=60)
    
    return success


def test_keyword_job() -> bool:
    """Test complet pour un job avec keywords."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Testing keyword job{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    
    try:
        print_info("Creating keyword job with keywords=['OVH']...")
        response = requests.post(
            f"{API_BASE}/scrape/keywords",
            json={"keywords": ["OVH"]},
            params={"limit": 5, "concurrency": 1, "delay": 0.5},
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Failed to create keyword job: {response.status_code} - {response.text}")
            return False
        
        data = response.json()
        job_id = data.get("job_id")
        
        if not job_id:
            print_error(f"No job_id in response: {data}")
            return False
        
        print_success(f"Keyword job created: {job_id[:8]}...")
        
        # Surveiller la progression avec un timeout plus long pour les keyword jobs
        # qui peuvent prendre beaucoup de temps (360 tâches)
        success = monitor_job_progress(job_id, max_wait=300)  # 5 minutes pour keyword jobs
        
        return success
    
    except Exception as e:
        print_error(f"Error creating keyword job: {e}")
        return False


def main():
    """Fonction principale."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}🧪 SCRAPING FLOW TEST{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    # Vérifier que le serveur est accessible
    if not check_server_health():
        print_error("Server is not accessible. Please start the server first.")
        sys.exit(1)
    
    print_success("Server is accessible")
    
    # Tests pour différentes sources
    sources_to_test = ["reddit", "stackoverflow"]
    results = []
    
    for source in sources_to_test:
        result = test_single_source_job(source)
        results.append((f"{source} job", result))
    
    # Test pour keyword job
    result = test_keyword_job()
    results.append(("keyword job", result))
    
    # Résumé
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}📊 TEST RESULTS{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
            passed += 1
        else:
            print_error(f"{test_name}: FAILED")
            failed += 1
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Total: {total}")
    print(f"  Passed: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"  Failed: {Colors.RED}{failed}{Colors.RESET}")
    print(f"  Success rate: {success_rate:.1f}%")
    
    if failed == 0:
        print_success("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print_error(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

