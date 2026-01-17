"""Script de test et génération de rapport synthétique."""
import asyncio
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
import traceback

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Ajouter le chemin du backend
sys.path.insert(0, '.')

from app.scraper import trustpilot, github, stackoverflow, reddit, news, mastodon, linkedin
from app.scraper.circuit_breaker import get_all_circuit_breakers
from app.scraper.http_client import get_http_client, close_http_client


class ScraperTestResult:
    """Résultat d'un test de scraper."""
    def __init__(self, name: str):
        self.name = name
        self.status = "PENDING"
        self.items_count = 0
        self.duration = 0.0
        self.error = None
        self.metrics = {}


async def test_scraper(scraper_func, name: str, query: str = "OVH", limit: int = 5) -> ScraperTestResult:
    """Test un scraper et retourne le résultat."""
    result = ScraperTestResult(name)
    start_time = time.time()
    
    try:
        items = await scraper_func(query, limit=limit)
        result.status = "SUCCESS"
        result.items_count = len(items)
        result.duration = time.time() - start_time
        
        # Vérifications de qualité
        if items:
            result.metrics['has_items'] = True
            result.metrics['avg_content_length'] = sum(len(item.get('content', '')) for item in items) / len(items)
            result.metrics['has_urls'] = sum(1 for item in items if item.get('url'))
            result.metrics['has_authors'] = sum(1 for item in items if item.get('author'))
        else:
            result.metrics['has_items'] = False
        
    except Exception as e:
        result.status = "ERROR"
        result.error = str(e)
        result.duration = time.time() - start_time
        result.metrics['error_type'] = type(e).__name__
    
    return result


async def run_all_tests():
    """Exécute tous les tests et génère le rapport."""
    print("=" * 100)
    print("TESTS FONCTIONNELS ET TECHNIQUES - SCRAPERS ASYNC")
    print("=" * 100)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Liste des scrapers à tester
    scrapers = [
        (trustpilot.scrape_trustpilot_reviews_async, "Trustpilot"),
        (github.scrape_github_issues_async, "GitHub"),
        (stackoverflow.scrape_stackoverflow_async, "StackOverflow"),
        (reddit.scrape_reddit_async, "Reddit"),
        (news.scrape_google_news_async, "Google News"),
        (mastodon.scrape_mastodon_async, "Mastodon"),
        (linkedin.scrape_linkedin_async, "LinkedIn"),
    ]
    
    results: List[ScraperTestResult] = []
    
    # Test séquentiel pour avoir des résultats détaillés
    print("Exécution des tests...")
    for scraper_func, name in scrapers:
        print(f"  Testing {name}...", end=" ", flush=True)
        result = await test_scraper(scraper_func, name)
        results.append(result)
        
        if result.status == "SUCCESS":
            print(f"OK ({result.items_count} items, {result.duration:.2f}s)")
        else:
            print(f"FAILED ({result.error})")
        
        # Petit délai entre les tests
        await asyncio.sleep(0.5)
    
    # Test concurrent
    print("\nTest de concurrence...")
    start_time = time.time()
    concurrent_tasks = [
        test_scraper(scraper_func, name) 
        for scraper_func, name in scrapers
    ]
    concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    concurrent_duration = time.time() - start_time
    
    # Récupération des métriques du circuit breaker
    circuit_breakers = get_all_circuit_breakers()
    
    # Génération du rapport
    print("\n" + "=" * 100)
    print("RAPPORT SYNTHÉTIQUE")
    print("=" * 100)
    
    # Tableau des résultats
    print("\n[RAPPORT] RESULTATS PAR SCRAPER")
    print("-" * 100)
    print(f"{'Scraper':<20} {'Status':<12} {'Items':<8} {'Durée':<10} {'Erreur':<30}")
    print("-" * 100)
    
    for result in results:
        status_icon = "[OK]" if result.status == "SUCCESS" else "[FAIL]"
        error_msg = result.error[:27] + "..." if result.error and len(result.error) > 30 else (result.error or "")
        print(f"{result.name:<20} {status_icon} {result.status:<10} {result.items_count:<8} {result.duration:>8.2f}s  {error_msg:<30}")
    
    # Métriques globales
    print("\n[METRIQUES] METRIQUES GLOBALES")
    print("-" * 100)
    total_success = sum(1 for r in results if r.status == "SUCCESS")
    total_items = sum(r.items_count for r in results)
    total_duration = sum(r.duration for r in results)
    avg_duration = total_duration / len(results) if results else 0
    
    print(f"Taux de succès:        {total_success}/{len(results)} ({total_success/len(results)*100:.1f}%)")
    print(f"Total items récupérés: {total_items}")
    print(f"Durée totale:          {total_duration:.2f}s")
    print(f"Durée moyenne:         {avg_duration:.2f}s")
    print(f"Durée concurrente:     {concurrent_duration:.2f}s")
    print(f"Gain de performance:   {total_duration/concurrent_duration:.2f}x" if concurrent_duration > 0 else "N/A")
    
    # Circuit breakers
    print("\n[CIRCUIT BREAKERS] CIRCUIT BREAKERS")
    print("-" * 100)
    if circuit_breakers:
        print(f"{'Source':<20} {'État':<15} {'Échecs':<10}")
        print("-" * 100)
        for source, cb in circuit_breakers.items():
            state_icon = "[OK]" if cb.get_state().value == "CLOSED" else "[OPEN]" if cb.get_state().value == "OPEN" else "[HALF]"
            print(f"{source:<20} {state_icon} {cb.get_state().value:<13} {cb.failure_count:<10}")
    else:
        print("Aucun circuit breaker actif")
    
    # Qualité des données
    print("\n[QUALITE] QUALITE DES DONNEES")
    print("-" * 100)
    successful_results = [r for r in results if r.status == "SUCCESS" and r.items_count > 0]
    if successful_results:
        print(f"{'Scraper':<20} {'Items':<8} {'URLs':<8} {'Auteurs':<10} {'Contenu moy':<12}")
        print("-" * 100)
        for result in successful_results:
            metrics = result.metrics
            urls_pct = (metrics.get('has_urls', 0) / result.items_count * 100) if result.items_count > 0 else 0
            authors_pct = (metrics.get('has_authors', 0) / result.items_count * 100) if result.items_count > 0 else 0
            avg_content = metrics.get('avg_content_length', 0)
            print(f"{result.name:<20} {result.items_count:<8} {urls_pct:>6.1f}%  {authors_pct:>8.1f}%  {avg_content:>10.1f}")
    
    # Recommandations
    print("\n[RECOMMANDATIONS] RECOMMANDATIONS")
    print("-" * 100)
    recommendations = []
    
    if total_success < len(results):
        failed = [r.name for r in results if r.status != "SUCCESS"]
        recommendations.append(f"Scrapers en échec: {', '.join(failed)} - Vérifier la connectivité réseau")
    
    if avg_duration > 5.0:
        recommendations.append(f"Durée moyenne élevée ({avg_duration:.2f}s) - Optimiser les timeouts")
    
    slow_scrapers = [r.name for r in results if r.duration > 10.0]
    if slow_scrapers:
        recommendations.append(f"Scrapers lents: {', '.join(slow_scrapers)} - Considérer l'optimisation")
    
    if not recommendations:
        recommendations.append("[OK] Tous les scrapers fonctionnent correctement")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    # Résumé final
    print("\n" + "=" * 100)
    print("RÉSUMÉ FINAL")
    print("=" * 100)
    print(f"[OK] Scrapers operationnels: {total_success}/{len(results)}")
    print(f"[ITEMS] Items recuperes: {total_items}")
    print(f"[PERF] Performance: {concurrent_duration:.2f}s (concurrent)")
    print(f"[CB] Circuit breakers: {len(circuit_breakers)} actifs")
    
    # Nettoyage
    await close_http_client()
    
    return results


if __name__ == "__main__":
    try:
        results = asyncio.run(run_all_tests())
        sys.exit(0 if all(r.status == "SUCCESS" for r in results) else 1)
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Erreur lors des tests: {e}")
        traceback.print_exc()
        sys.exit(1)

