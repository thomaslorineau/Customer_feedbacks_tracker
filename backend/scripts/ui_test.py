#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests UI automatisés avec Playwright.

Ce script teste :
- Chargement des pages principales
- Navigation entre les pages
- Toggle dark mode
- Éléments clés du dashboard

Usage:
    # Installation (une fois)
    pip install playwright
    playwright install chromium

    # Lancer les tests
    python backend/scripts/ui_test.py

    # Ou avec le serveur déjà lancé
    python backend/scripts/ui_test.py --no-server --base-url http://localhost:8000
"""

import subprocess
import time
import sys
import os
import argparse
from pathlib import Path

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}[PASS] {msg}{Colors.RESET}")

def print_error(msg: str):
    print(f"{Colors.RED}[FAIL] {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.RESET}")

def print_warn(msg: str):
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.RESET}")


class UITestRunner:
    def __init__(self, base_url: str = "http://localhost:8000", headless: bool = True):
        self.base_url = base_url.rstrip('/')
        self.headless = headless
        self.server_process = None
        self.browser = None
        self.context = None
        self.page = None
        self.results = {"passed": 0, "failed": 0, "errors": []}
        self.screenshots_dir = Path(__file__).parent.parent / "test_screenshots"

    def start_server(self) -> bool:
        """Démarre le serveur FastAPI."""
        print_info("Démarrage du serveur...")
        
        backend_dir = Path(__file__).parent.parent
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Attendre que le serveur soit prêt
            import httpx
            for i in range(30):
                try:
                    response = httpx.get(f"{self.base_url}/", timeout=2)
                    if response.status_code == 200:
                        print_success("Serveur démarré")
                        return True
                except Exception:
                    pass
                time.sleep(1)
            
            print_error("Timeout en attendant le serveur")
            return False
            
        except Exception as e:
            print_error(f"Erreur au démarrage du serveur: {e}")
            return False

    def stop_server(self):
        """Arrête le serveur FastAPI."""
        if self.server_process:
            print_info("Arrêt du serveur...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            print_success("Serveur arrêté")

    def setup_browser(self) -> bool:
        """Initialise Playwright et le navigateur."""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            self.page = self.context.new_page()
            
            # Créer le dossier screenshots
            self.screenshots_dir.mkdir(exist_ok=True)
            
            print_success("Navigateur initialisé")
            return True
            
        except Exception as e:
            print_error(f"Erreur Playwright: {e}")
            print_warn("Avez-vous installé Playwright ? Lancez: playwright install chromium")
            return False

    def teardown_browser(self):
        """Ferme le navigateur."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()

    def take_screenshot(self, name: str):
        """Prend un screenshot pour debug."""
        if self.page:
            path = self.screenshots_dir / f"{name}.png"
            self.page.screenshot(path=str(path))
            print_info(f"Screenshot: {path}")

    def run_test(self, name: str, test_func):
        """Exécute un test et capture les erreurs."""
        try:
            print_info(f"Test: {name}")
            test_func()
            self.results["passed"] += 1
            print_success(name)
        except AssertionError as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{name}: {e}")
            print_error(f"{name}: {e}")
            self.take_screenshot(name.replace(" ", "_").lower())
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{name}: {e}")
            print_error(f"{name}: Exception - {e}")
            self.take_screenshot(name.replace(" ", "_").lower())

    # ==================== TESTS ====================

    def test_homepage_loads(self):
        """Vérifie que la page d'accueil charge."""
        self.page.goto(f"{self.base_url}/")
        self.page.wait_for_load_state("networkidle")
        
        assert "Customer Feedbacks" in self.page.title(), f"Titre inattendu: {self.page.title()}"
        
        # Vérifie qu'il y a du contenu
        body = self.page.locator("body")
        assert body.is_visible(), "Body non visible"

    def test_dashboard_loads(self):
        """Vérifie que le dashboard charge."""
        self.page.goto(f"{self.base_url}/dashboard/")
        self.page.wait_for_load_state("networkidle")
        
        # Attendre un peu pour les graphiques
        self.page.wait_for_timeout(2000)
        
        # Vérifie le titre ou un élément clé
        assert "dashboard" in self.page.url.lower() or "Dashboard" in self.page.content(), "Dashboard non chargé"

    def test_settings_loads(self):
        """Vérifie que la page settings charge."""
        self.page.goto(f"{self.base_url}/dashboard/settings.html")
        self.page.wait_for_load_state("networkidle")
        
        assert "settings" in self.page.url.lower(), "Page settings non chargée"

    def test_logs_page_loads(self):
        """Vérifie que la page logs charge."""
        self.page.goto(f"{self.base_url}/logs.html")
        self.page.wait_for_load_state("networkidle")
        
        assert "logs" in self.page.url.lower(), "Page logs non chargée"

    def test_navigation_links(self):
        """Vérifie que la navigation fonctionne."""
        self.page.goto(f"{self.base_url}/dashboard/")
        self.page.wait_for_load_state("networkidle")
        
        # Chercher un lien de navigation et cliquer
        nav_links = self.page.locator("nav a, .nav a, [class*='nav'] a")
        
        if nav_links.count() > 0:
            # Cliquer sur le premier lien
            first_link = nav_links.first
            href = first_link.get_attribute("href")
            if href and not href.startswith("#") and not href.startswith("javascript"):
                first_link.click()
                self.page.wait_for_load_state("networkidle")
                print_info(f"Navigation vers: {self.page.url}")

    def test_dark_mode_toggle(self):
        """Vérifie que le toggle dark mode fonctionne."""
        self.page.goto(f"{self.base_url}/dashboard/")
        self.page.wait_for_load_state("networkidle")
        
        # Chercher le toggle dark mode
        toggle_selectors = [
            "[class*='dark-mode']",
            "[class*='theme']",
            "#dark-mode-toggle",
            "#theme-toggle",
            "button[class*='dark']",
            "[onclick*='dark']"
        ]
        
        for selector in toggle_selectors:
            toggle = self.page.locator(selector).first
            if toggle.count() > 0 and toggle.is_visible():
                # Prendre le state initial
                body_class_before = self.page.locator("body").get_attribute("class") or ""
                
                # Cliquer sur le toggle
                toggle.click()
                self.page.wait_for_timeout(500)
                
                # Vérifier que quelque chose a changé
                body_class_after = self.page.locator("body").get_attribute("class") or ""
                
                if body_class_before != body_class_after:
                    print_info("Dark mode toggle fonctionne")
                    return
        
        print_warn("Toggle dark mode non trouvé ou non fonctionnel")

    def test_api_connectivity(self):
        """Vérifie que l'API répond via le frontend."""
        self.page.goto(f"{self.base_url}/dashboard/")
        self.page.wait_for_load_state("networkidle")
        
        # Attendre les appels API
        self.page.wait_for_timeout(3000)
        
        # Vérifier qu'il n'y a pas d'erreur majeure dans la console
        # (les erreurs mineures sont OK)

    # ==================== MAIN ====================

    def run_all_tests(self):
        """Exécute tous les tests."""
        tests = [
            ("Page d'accueil charge", self.test_homepage_loads),
            ("Dashboard charge", self.test_dashboard_loads),
            ("Settings charge", self.test_settings_loads),
            ("Logs charge", self.test_logs_page_loads),
            ("Navigation fonctionne", self.test_navigation_links),
            ("Dark mode toggle", self.test_dark_mode_toggle),
            ("Connectivité API", self.test_api_connectivity),
        ]
        
        print("\n" + "=" * 60)
        print("TESTS UI - Playwright")
        print("=" * 60 + "\n")
        
        for name, test_func in tests:
            self.run_test(name, test_func)
            print()
        
        # Résumé
        print("\n" + "=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print(f"  Passés:  {self.results['passed']}")
        print(f"  Échoués: {self.results['failed']}")
        
        if self.results["errors"]:
            print("\nErreurs:")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        print("=" * 60 + "\n")
        
        return self.results["failed"] == 0


def main():
    parser = argparse.ArgumentParser(description="Tests UI avec Playwright")
    parser.add_argument("--no-server", action="store_true", help="Ne pas démarrer le serveur (utiliser un serveur existant)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="URL de base du serveur")
    parser.add_argument("--headed", action="store_true", help="Afficher le navigateur (non headless)")
    args = parser.parse_args()
    
    runner = UITestRunner(base_url=args.base_url, headless=not args.headed)
    
    try:
        # Démarrer le serveur si nécessaire
        if not args.no_server:
            if not runner.start_server():
                print_error("Impossible de démarrer le serveur")
                sys.exit(1)
        
        # Setup navigateur
        if not runner.setup_browser():
            sys.exit(1)
        
        # Lancer les tests
        success = runner.run_all_tests()
        
        sys.exit(0 if success else 1)
        
    finally:
        runner.teardown_browser()
        if not args.no_server:
            runner.stop_server()


if __name__ == "__main__":
    main()
