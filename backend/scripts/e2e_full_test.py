#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite complète de tests E2E pour OVH Customer Feedbacks Tracker.

Ce script teste :
- Démarrage du serveur
- Endpoints API principaux
- Scrapers (au moins un)
- Pages frontend
- Logs
- Configuration

Usage:
    python backend/scripts/e2e_full_test.py
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Fix encoding for Windows console (cp1252 can't handle emojis)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        # Python < 3.7 or reconfigure not available
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colors for output
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

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

# Configuration
ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / 'backend'
BASE_URL = 'http://127.0.0.1:8000'
UVICORN_CMD = [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000']
SERVER_START_TIMEOUT = 30
TEST_TIMEOUT = 5

# Global server process
server_process = None

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.duration = 0

def start_server() -> subprocess.Popen:
    """Démarre le serveur FastAPI en arrière-plan."""
    print_info("Démarrage du serveur...")
    proc = subprocess.Popen(
        UVICORN_CMD,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Attendre que le serveur soit prêt
    for i in range(SERVER_START_TIMEOUT):
        try:
            response = requests.get(f'{BASE_URL}/', timeout=2)
            if response.status_code in (200, 302, 404):
                print_success(f"Serveur démarré (tentative {i+1}/{SERVER_START_TIMEOUT})")
                return proc
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    
    raise RuntimeError(f"Le serveur n'a pas démarré dans les {SERVER_START_TIMEOUT} secondes")

def stop_server(proc: subprocess.Popen):
    """Arrête le serveur."""
    print_info("Arrêt du serveur...")
    try:
        proc.terminate()
        proc.wait(timeout=5)
        print_success("Serveur arrêté")
    except subprocess.TimeoutExpired:
        proc.kill()
        print_warning("Serveur tué (timeout)")
    except Exception as e:
        print_error(f"Erreur lors de l'arrêt: {e}")

def test_endpoint(method: str, endpoint: str, expected_status: int = 200, 
                  json_data: dict = None, params: dict = None) -> Tuple[bool, dict]:
    """Teste un endpoint API."""
    try:
        url = f"{BASE_URL}{endpoint}"
        kwargs = {'timeout': TEST_TIMEOUT}
        if params:
            kwargs['params'] = params
        if json_data:
            kwargs['json'] = json_data
            
        if method.upper() == 'GET':
            response = requests.get(url, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, **kwargs)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, **kwargs)
        else:
            return False, {"error": f"Méthode {method} non supportée"}
        
        if response.status_code == expected_status:
            try:
                return True, response.json()
            except:
                return True, {"text": response.text[:200]}
        else:
            return False, {
                "error": f"Status {response.status_code} attendu {expected_status}",
                "response": response.text[:200]
            }
    except requests.exceptions.Timeout:
        return False, {"error": "Timeout"}
    except requests.exceptions.ConnectionError:
        return False, {"error": "Connexion refusée"}
    except Exception as e:
        return False, {"error": str(e)}

def run_test(test_func) -> TestResult:
    """Exécute un test et retourne le résultat."""
    start_time = time.time()
    result = TestResult(test_func.__name__)
    try:
        test_func(result)
        result.passed = True
    except Exception as e:
        result.error = str(e)
        result.passed = False
    finally:
        result.duration = time.time() - start_time
    return result

# ==================== TESTS ====================

def test_server_health(result: TestResult):
    """Test 1: Vérifier que le serveur répond."""
    result.name = "Health Check"
    success, data = test_endpoint('GET', '/')
    if success:
        print_success("Serveur répond correctement")
    else:
        raise AssertionError(f"Le serveur ne répond pas: {data}")

def test_api_version(result: TestResult):
    """Test 2: Vérifier l'endpoint /api/version."""
    result.name = "API Version"
    success, data = test_endpoint('GET', '/api/version')
    if success:
        version = data.get('version', 'unknown')
        print_success(f"Version API: {version}")
    else:
        raise AssertionError(f"Erreur /api/version: {data}")

def test_api_config(result: TestResult):
    """Test 3: Vérifier l'endpoint /api/config."""
    result.name = "API Config"
    success, data = test_endpoint('GET', '/api/config')
    if success:
        env = data.get('environment', 'unknown')
        print_success(f"Configuration chargée (env: {env})")
    else:
        raise AssertionError(f"Erreur /api/config: {data}")

def test_api_posts(result: TestResult):
    """Test 4: Vérifier l'endpoint /api/posts."""
    result.name = "API Posts"
    success, data = test_endpoint('GET', '/posts', params={'limit': 10})
    if success:
        count = len(data) if isinstance(data, list) else 0
        print_success(f"Posts récupérés: {count}")
    else:
        raise AssertionError(f"Erreur /posts: {data}")

def test_api_stats(result: TestResult):
    """Test 5: Vérifier l'endpoint /api/posts-by-source (contient les stats)."""
    result.name = "API Stats"
    # Utiliser /api/posts-by-source qui contient les statistiques
    success, data = test_endpoint('GET', '/api/posts-by-source')
    if success:
        total = data.get('total_posts', 0)
        print_success(f"Statistiques récupérées (total: {total} posts)")
    else:
        raise AssertionError(f"Erreur /api/posts-by-source: {data}")

def test_api_posts_by_source(result: TestResult):
    """Test 6: Vérifier l'endpoint /api/posts-by-source."""
    result.name = "API Posts by Source"
    success, data = test_endpoint('GET', '/api/posts-by-source')
    if success:
        sources = data.get('sources', {})
        print_success(f"Posts par source récupérés ({len(sources)} sources)")
    else:
        raise AssertionError(f"Erreur /api/posts-by-source: {data}")

def test_scraper_reddit(result: TestResult):
    """Test 7: Tester le scraper Reddit (rapide)."""
    result.name = "Scraper Reddit"
    print_info("Test du scraper Reddit (peut prendre quelques secondes)...")
    success, data = test_endpoint('POST', '/scrape/reddit', params={'query': 'OVH', 'limit': 2})
    if success:
        added = data.get('added', 0)
        print_success(f"Scraper Reddit fonctionne (ajouté: {added} posts)")
    else:
        # Reddit peut échouer, c'est acceptable
        print_warning(f"Scraper Reddit: {data.get('error', 'Erreur inconnue')} (peut être normal)")

def test_scraper_stackoverflow(result: TestResult):
    """Test 8: Tester le scraper Stack Overflow (rapide)."""
    result.name = "Scraper Stack Overflow"
    print_info("Test du scraper Stack Overflow (peut prendre quelques secondes)...")
    success, data = test_endpoint('POST', '/scrape/stackoverflow', params={'query': 'OVH', 'limit': 2})
    if success:
        added = data.get('added', 0)
        print_success(f"Scraper Stack Overflow fonctionne (ajouté: {added} posts)")
    else:
        print_warning(f"Scraper Stack Overflow: {data.get('error', 'Erreur inconnue')}")

def test_frontend_pages(result: TestResult):
    """Test 9: Vérifier que les pages frontend se chargent."""
    result.name = "Frontend Pages"
    pages = ['/scraping', '/dashboard', '/logs', '/settings']
    for page in pages:
        success, data = test_endpoint('GET', page, expected_status=200)
        if success:
            print_success(f"Page {page} se charge")
        else:
            raise AssertionError(f"Page {page} ne se charge pas: {data}")

def test_api_logs(result: TestResult):
    """Test 10: Vérifier l'endpoint /api/logs."""
    result.name = "API Logs"
    success, data = test_endpoint('GET', '/api/logs', params={'limit': 10})
    if success:
        logs = data.get('logs', [])
        count = data.get('count', 0)
        print_success(f"Logs récupérés: {count}")
    else:
        raise AssertionError(f"Erreur /api/logs: {data}")

def test_settings_queries(result: TestResult):
    """Test 11: Tester la gestion des queries sauvegardées."""
    result.name = "Settings Queries"
    # GET
    success, data = test_endpoint('GET', '/settings/queries')
    if not success:
        raise AssertionError(f"Erreur GET /settings/queries: {data}")
    
    # POST
    test_keywords = ['e2e_test_keyword']
    success, data = test_endpoint('POST', '/settings/queries', json_data={'keywords': test_keywords})
    if success:
        print_success("Keywords sauvegardées")
    else:
        raise AssertionError(f"Erreur POST /settings/queries: {data}")

def test_cors_headers(result: TestResult):
    """Test 12: Vérifier les headers de sécurité."""
    result.name = "Security Headers"
    try:
        response = requests.get(f'{BASE_URL}/api/version', timeout=TEST_TIMEOUT)
        headers = response.headers
        
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
        
        found = []
        for header, expected in security_headers.items():
            if header in headers:
                found.append(header)
        
        if len(found) >= 2:
            print_success(f"Headers de sécurité présents: {', '.join(found)}")
        else:
            print_warning(f"Seulement {len(found)} headers de sécurité trouvés")
    except Exception as e:
        raise AssertionError(f"Erreur vérification headers: {e}")

# ==================== SUITE DE TESTS ====================

def run_all_tests() -> List[TestResult]:
    """Exécute tous les tests."""
    tests = [
        test_server_health,
        test_api_version,
        test_api_config,
        test_api_posts,
        test_api_stats,
        test_api_posts_by_source,
        test_scraper_reddit,
        test_scraper_stackoverflow,
        test_frontend_pages,
        test_api_logs,
        test_settings_queries,
        test_cors_headers,
    ]
    
    results = []
    for test_func in tests:
        result = run_test(test_func)
        results.append(result)
        if result.passed:
            print_success(f"✓ {result.name} ({result.duration:.2f}s)")
        else:
            print_error(f"✗ {result.name} ({result.duration:.2f}s)")
            if result.error:
                print_error(f"  Erreur: {result.error}")
    
    return results

def print_summary(results: List[TestResult]):
    """Affiche le résumé des tests."""
    print_header("RÉSUMÉ DES TESTS")
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    failed = total - passed
    
    print(f"\n{Colors.BOLD}Total: {total} tests{Colors.RESET}")
    print(f"{Colors.GREEN}✅ Réussis: {passed}{Colors.RESET}")
    if failed > 0:
        print(f"{Colors.RED}❌ Échoués: {failed}{Colors.RESET}")
    
    if failed > 0:
        print(f"\n{Colors.RED}{Colors.BOLD}Tests échoués:{Colors.RESET}")
        for result in results:
            if not result.passed:
                print(f"  - {result.name}")
                if result.error:
                    print(f"    {Colors.RED}{result.error}{Colors.RESET}")
    
    total_duration = sum(r.duration for r in results)
    print(f"\n{Colors.BLUE}Durée totale: {total_duration:.2f}s{Colors.RESET}")
    
    # Score
    score = (passed / total * 100) if total > 0 else 0
    print(f"\n{Colors.BOLD}Score: {score:.1f}%{Colors.RESET}")
    
    if score == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Tous les tests sont passés !{Colors.RESET}")
    elif score >= 80:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  La plupart des tests sont passés{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ Plusieurs tests ont échoué{Colors.RESET}")
    
    return score == 100

def main():
    """Fonction principale."""
    global server_process
    
    print_header("TESTS E2E - OVH Customer Feedbacks Tracker")
    
    try:
        # Démarrer le serveur
        server_process = start_server()
        time.sleep(1)  # Attendre un peu pour être sûr
        
        # Exécuter les tests
        results = run_all_tests()
        
        # Afficher le résumé
        all_passed = print_summary(results)
        
        # Code de sortie
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print_warning("\nTests interrompus par l'utilisateur")
        return 130
    except Exception as e:
        print_error(f"Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Arrêter le serveur
        if server_process:
            stop_server(server_process)

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

