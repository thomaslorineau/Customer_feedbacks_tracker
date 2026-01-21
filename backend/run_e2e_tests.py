#!/usr/bin/env python3
"""
Script pour exécuter les tests E2E des scrapers.
Usage: python run_e2e_tests.py [--port PORT] [--verbose]
"""
import sys
import os
import subprocess
import argparse

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Run E2E tests for scrapers")
    parser.add_argument("--port", type=int, default=8001, help="API server port (default: 8001)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--markers", "-m", type=str, help="Run tests with specific markers (e.g., 'not slow')")
    args = parser.parse_args()
    
    # Définir la variable d'environnement pour l'URL de l'API
    os.environ["API_BASE_URL"] = f"http://127.0.0.1:{args.port}"
    
    # Construire la commande pytest
    cmd = ["python", "-m", "pytest", "tests/test_e2e_scrapers.py"]
    
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Toujours verbose pour voir les résultats
    
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    # Ajouter des options utiles
    cmd.extend([
        "--tb=short",  # Traceback court
        "--color=yes",  # Couleurs
        "-s",  # Afficher les print statements
    ])
    
    print(f"🚀 Running E2E tests against API at {os.environ['API_BASE_URL']}")
    print(f"📋 Command: {' '.join(cmd)}\n")
    
    # Exécuter les tests
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()


