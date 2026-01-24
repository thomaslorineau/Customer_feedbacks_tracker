#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour lancer tous les tests de manière systématique.

Ce script :
1. Vérifie que le serveur est accessible (pour les tests E2E)
2. Lance les tests unitaires
3. Lance les tests E2E si le serveur est disponible
4. Génère un rapport détaillé
"""
import subprocess
import sys
import os
import time
import requests
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_section(title: str):
    """Affiche un titre de section."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")


def check_server_health(api_base: str = "http://127.0.0.1:8000", timeout: int = 5) -> bool:
    """Vérifie que le serveur est accessible."""
    try:
        response = requests.get(f"{api_base}/api/version", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def run_tests(test_path: str, description: str, require_server: bool = False) -> tuple[bool, str]:
    """
    Lance des tests et retourne (success, output).
    
    Args:
        test_path: Chemin vers les tests à lancer
        description: Description des tests
        require_server: Si True, vérifie que le serveur est accessible
    
    Returns:
        Tuple (success: bool, output: str)
    """
    print_info(f"Running {description}...")
    
    if require_server:
        if not check_server_health():
            return False, "Server not accessible - skipping E2E tests"
    
    try:
        # Lancer pytest avec capture de la sortie
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )
        
        output = result.stdout + result.stderr
        success = result.returncode == 0
        
        return success, output
    
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 10 minutes"
    except Exception as e:
        return False, f"Error running tests: {e}"


def main():
    """Fonction principale."""
    print_section("🧪 TEST SUITE - OVH Customer Feedbacks Tracker")
    
    # Déterminer le répertoire de base
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    project_root = backend_dir.parent
    
    os.chdir(project_root)
    
    results = []
    
    # 1. Tests unitaires (toujours exécutés)
    print_section("1. Tests Unitaires")
    success, output = run_tests(
        "backend/tests/unit/",
        "Unit tests",
        require_server=False
    )
    results.append(("Unit Tests", success, output))
    
    if success:
        print_success("Unit tests passed")
    else:
        print_error("Unit tests failed")
        print(output[-1000:])  # Afficher les dernières lignes
    
    # 2. Tests de robustesse (toujours exécutés)
    print_section("2. Tests de Robustesse")
    success, output = run_tests(
        "backend/tests/test_job_robustness.py",
        "Job robustness tests",
        require_server=True
    )
    results.append(("Robustness Tests", success, output))
    
    if success:
        print_success("Robustness tests passed")
    elif "Server not accessible" in output:
        print_warning("Robustness tests skipped (server not accessible)")
    else:
        print_error("Robustness tests failed")
        print(output[-1000:])
    
    # 3. Tests de régression (toujours exécutés)
    print_section("3. Tests de Régression")
    success, output = run_tests(
        "backend/tests/test_regression_bugs.py",
        "Regression tests",
        require_server=True
    )
    results.append(("Regression Tests", success, output))
    
    if success:
        print_success("Regression tests passed")
    elif "Server not accessible" in output:
        print_warning("Regression tests skipped (server not accessible)")
    else:
        print_error("Regression tests failed")
        print(output[-1000:])
    
    # 4. Tests E2E (nécessitent le serveur)
    print_section("4. Tests E2E")
    if check_server_health():
        print_success("Server is accessible - running E2E tests")
        
        # Tests E2E jobs
        success, output = run_tests(
            "backend/tests/test_e2e_jobs.py",
            "E2E job tests",
            require_server=True
        )
        results.append(("E2E Job Tests", success, output))
        
        if success:
            print_success("E2E job tests passed")
        else:
            print_error("E2E job tests failed")
            print(output[-1000:])
        
        # Tests E2E progress bar (nécessitent Playwright)
        print_info("Skipping E2E progress bar tests (require Playwright)")
        # success, output = run_tests(
        #     "backend/tests/test_e2e_progress_bar.py",
        #     "E2E progress bar tests",
        #     require_server=True
        # )
        # results.append(("E2E Progress Bar Tests", success, output))
    else:
        print_warning("Server not accessible - skipping E2E tests")
        print_info("Start the server with: cd backend && .\\start_server.ps1")
        results.append(("E2E Tests", None, "Skipped - server not accessible"))
    
    # Résumé
    print_section("📊 RÉSUMÉ DES TESTS")
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, success, output in results:
        if success is True:
            print_success(f"{name}: PASSED")
            passed += 1
        elif success is False:
            print_error(f"{name}: FAILED")
            failed += 1
        else:
            print_warning(f"{name}: SKIPPED")
            skipped += 1
    
    total = passed + failed + skipped
    success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
    
    print(f"\n{Colors.BOLD}Total:{Colors.RESET} {total}")
    print(f"{Colors.GREEN}Passed:{Colors.RESET} {passed}")
    print(f"{Colors.RED}Failed:{Colors.RESET} {failed}")
    print(f"{Colors.YELLOW}Skipped:{Colors.RESET} {skipped}")
    print(f"{Colors.BOLD}Success rate:{Colors.RESET} {success_rate:.1f}%")
    
    if failed == 0:
        print_success("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print_error(f"\n❌ {failed} test suite(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

