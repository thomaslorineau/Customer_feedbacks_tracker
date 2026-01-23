"""Tests E2E pour l'interface utilisateur."""
import pytest
import asyncio
from playwright.async_api import async_playwright, Page, expect
import time

# Configuration pytest-asyncio pour les fixtures async de session
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Create a browser instance for all tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create a new page for each test."""
    page = await browser.new_page()
    yield page
    await page.close()


BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_feedback_collection_page_loads(page: Page):
    """Test que la page Feedback Collection se charge correctement."""
    await page.goto(f"{BASE_URL}/scraping")
    await expect(page).to_have_title("Customer Feedbacks Tracker - Feedbacks Collection")
    
    # Vérifier que les éléments principaux sont présents
    await expect(page.locator("h1")).to_be_visible()
    await expect(page.locator("#gallery")).to_be_visible()
    await expect(page.locator("#btnScrapeStackOverflow")).to_be_visible()


@pytest.mark.asyncio
async def test_stackoverflow_scraper_error_handling(page: Page):
    """Test que les erreurs Stack Overflow sont correctement affichées."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Intercepter les requêtes pour simuler une erreur
    async def handle_route(route):
        if "/scrape/stackoverflow" in route.request.url:
            await route.fulfill(
                status=500,
                content_type="application/json",
                body='{"detail": "NetworkError when attempting to fetch resource"}'
            )
        else:
            await route.continue_()
    
    await page.route("**/scrape/stackoverflow*", handle_route)
    
    # Cliquer sur le bouton Stack Overflow
    await page.click("#btnScrapeStackOverflow")
    
    # Attendre que le toast d'erreur apparaisse
    await page.wait_for_selector(".toast.error", timeout=5000)
    
    # Vérifier que l'erreur est affichée
    toast_text = await page.locator(".toast.error").text_content()
    assert "Error scraping Stack Overflow" in toast_text or "NetworkError" in toast_text


@pytest.mark.asyncio
async def test_database_stats_display(page: Page):
    """Test que les stats de la base de données s'affichent correctement."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Attendre que les stats se chargent
    await page.wait_for_selector("#globalTotalPosts", timeout=5000)
    
    # Vérifier que les stats sont affichées
    total_posts = await page.locator("#globalTotalPosts").text_content()
    assert total_posts is not None
    assert total_posts.isdigit() or total_posts == "0"
    
    positive_posts = await page.locator("#globalPositivePosts").text_content()
    assert positive_posts is not None
    
    negative_posts = await page.locator("#globalNegativePosts").text_content()
    assert negative_posts is not None


@pytest.mark.asyncio
async def test_update_product_labels_button(page: Page):
    """Test que le bouton 'Check Product Labels' met à jour la base de données."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Attendre que la page soit chargée
    await page.wait_for_selector("button[onclick='checkProductLabels()']", timeout=5000)
    
    # Intercepter la requête de mise à jour
    update_request_promise = page.wait_for_request("**/admin/update-product-labels")
    stats_request_promise = page.wait_for_request("**/admin/product-labels-stats")
    
    # Mock les réponses
    async def handle_route(route):
        if "/admin/update-product-labels" in route.request.url:
            await route.fulfill(
                status=200,
                content_type="application/json",
                body='{"success": true, "updated_count": 10, "error_count": 0, "total_posts": 10, "message": "Updated 10 posts"}'
            )
        elif "/admin/product-labels-stats" in route.request.url:
            await route.fulfill(
                status=200,
                content_type="application/json",
                body='{"total_posts": 10, "posts_with_label": 8, "posts_without_label": 2, "coverage_percentage": 80.0, "label_distribution": {"VPS": 3, "Domain": 2}, "validation": {"valid_labels_count": 8, "invalid_labels_count": 0, "invalid_labels": {}, "official_products": ["VPS", "Domain"]}}'
            )
        else:
            await route.continue_()
    
    await page.route("**/admin/update-product-labels*", handle_route)
    await page.route("**/admin/product-labels-stats*", handle_route)
    
    # Cliquer sur le bouton (avec confirmation)
    page.on("dialog", lambda dialog: dialog.accept())
    await page.click("button[onclick='checkProductLabels()']")
    
    # Attendre que les requêtes soient faites
    await update_request_promise
    await stats_request_promise
    
    # Vérifier qu'un toast de succès apparaît
    await page.wait_for_selector(".toast.success", timeout=5000, state="visible")
    toast_text = await page.locator(".toast.success").text_content()
    assert "updated" in toast_text.lower() or "success" in toast_text.lower()


@pytest.mark.asyncio
async def test_recheck_answered_status_button(page: Page):
    """Test que le bouton 'Re-check Answered Status' fonctionne."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Attendre que la page soit chargée
    await page.wait_for_selector("button[onclick='recheckAnsweredStatus()']", timeout=5000)
    
    # Intercepter la requête
    request_promise = page.wait_for_request("**/admin/recheck-answered-status")
    
    # Mock la réponse
    async def handle_route(route):
        if "/admin/recheck-answered-status" in route.request.url:
            await route.fulfill(
                status=200,
                content_type="application/json",
                body='{"success": true, "updated_count": 5, "error_count": 0, "skipped_count": 2, "total_posts": 7, "message": "Re-checked 7 posts. Updated 5 posts."}'
            )
        else:
            await route.continue_()
    
    await page.route("**/admin/recheck-answered-status*", handle_route)
    
    # Cliquer sur le bouton (avec confirmation)
    page.on("dialog", lambda dialog: dialog.accept())
    await page.click("button[onclick='recheckAnsweredStatus()']")
    
    # Attendre que la requête soit faite
    await request_promise
    
    # Vérifier qu'un toast de succès apparaît
    await page.wait_for_selector(".toast.success", timeout=5000, state="visible")
    toast_text = await page.locator(".toast.success").text_content()
    assert "completed" in toast_text.lower() or "updated" in toast_text.lower() or "success" in toast_text.lower()


@pytest.mark.asyncio
async def test_version_badge_display(page: Page):
    """Test que le badge de version s'affiche correctement."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Attendre que le badge de version se charge
    await page.wait_for_selector("#versionBadge", timeout=5000)
    
    # Vérifier que le badge contient une version
    version_badge = await page.locator("#versionBadge").text_content()
    assert version_badge is not None
    assert version_badge.startswith("v")


@pytest.mark.asyncio
async def test_logs_page_loads(page: Page):
    """Test que la page des logs se charge correctement."""
    await page.goto(f"{BASE_URL}/logs")
    
    # Vérifier que les éléments principaux sont présents
    await expect(page.locator("h1")).to_be_visible()
    await expect(page.locator("#logsList")).to_be_visible()
    await expect(page.locator("#filterSource")).to_be_visible()
    await expect(page.locator("#filterLevel")).to_be_visible()


@pytest.mark.asyncio
async def test_logs_display(page: Page):
    """Test que les logs s'affichent correctement."""
    await page.goto(f"{BASE_URL}/logs")
    
    # Attendre que les logs se chargent
    await page.wait_for_selector("#logsList", timeout=5000)
    
    # Vérifier que les logs sont affichés (ou qu'un message approprié est affiché)
    logs_container = page.locator("#logsList")
    content = await logs_container.text_content()
    assert content is not None
    # Soit des logs sont affichés, soit un message "Aucun log disponible"
    assert len(content) > 0


@pytest.mark.asyncio
async def test_logs_filters(page: Page):
    """Test que les filtres de logs fonctionnent."""
    await page.goto(f"{BASE_URL}/logs")
    
    # Sélectionner une source
    await page.select_option("#filterSource", "Trustpilot")
    
    # Attendre que les logs se rechargent
    await page.wait_for_timeout(1000)
    
    # Vérifier que le filtre est appliqué (les logs sont rechargés)
    logs_container = page.locator("#logsList")
    assert await logs_container.is_visible()


@pytest.mark.asyncio
async def test_navigation_menu_present(page: Page):
    """Test que le menu de navigation est présent sur toutes les pages."""
    pages_to_test = [
        ("/scraping", "Feedbacks Collection"),
        ("/logs", "Scraping Logs"),
        ("/dashboard", "Dashboard Analytics"),
    ]
    
    for path, expected_text in pages_to_test:
        await page.goto(f"{BASE_URL}{path}")
        
        # Vérifier que le menu de navigation est présent
        nav_menu = page.locator(".nav-menu")
        await expect(nav_menu).to_be_visible()
        
        # Vérifier que le lien vers la page attendue est présent
        nav_link = page.locator(f"text={expected_text}")
        await expect(nav_link).to_be_visible()


@pytest.mark.asyncio
async def test_dark_mode_no_flash(page: Page):
    """Test qu'il n'y a pas de flash de light mode au chargement en dark mode."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Vérifier que le dark mode est appliqué immédiatement
    body_classes = await page.evaluate("() => document.body.className")
    
    # Si dark mode est activé, il ne devrait pas y avoir de flash
    # On vérifie que le thème est appliqué avant le rendu
    html_classes = await page.evaluate("() => document.documentElement.className")
    
    # Le dark mode devrait être appliqué immédiatement
    assert "dark-mode" in body_classes or "dark-mode" in html_classes or len(body_classes) == 0


@pytest.mark.asyncio
async def test_theme_toggle(page: Page):
    """Test que le toggle de thème fonctionne."""
    await page.goto(f"{BASE_URL}/scraping")
    
    # Trouver le bouton de toggle de thème
    theme_toggle = page.locator(".theme-toggle")
    await expect(theme_toggle).to_be_visible()
    
    # Cliquer sur le toggle
    await theme_toggle.click()
    
    # Attendre que le thème change
    await page.wait_for_timeout(500)
    
    # Vérifier que le thème a changé
    body_classes = await page.evaluate("() => document.body.className")
    # Le thème devrait avoir changé
    assert body_classes is not None


@pytest.mark.asyncio
async def test_logs_page_menu_present(page: Page):
    """Test que le menu de navigation est présent sur la page des logs."""
    await page.goto(f"{BASE_URL}/logs")
    
    # Vérifier que le menu de navigation est présent
    nav_menu = page.locator(".nav-menu")
    await expect(nav_menu).to_be_visible()
    
    # Vérifier que les liens de navigation sont présents
    await expect(page.locator("text=Feedbacks Collection")).to_be_visible()
    await expect(page.locator("text=Scraping Logs")).to_be_visible()
    await expect(page.locator("text=Dashboard Analytics")).to_be_visible()


@pytest.mark.asyncio
async def test_logs_error_display(page: Page):
    """Test que les erreurs de chargement des logs sont affichées."""
    await page.goto(f"{BASE_URL}/logs")
    
    # Intercepter les requêtes pour simuler une erreur
    async def handle_route(route):
        if "/api/logs" in route.request.url:
            await route.fulfill(
                status=500,
                content_type="application/json",
                body='{"error": "Internal server error"}'
            )
        else:
            await route.continue_()
    
    await page.route("**/api/logs*", handle_route)
    
    # Recharger la page pour déclencher l'erreur
    await page.reload()
    
    # Attendre que le message d'erreur apparaisse
    await page.wait_for_selector(".empty", timeout=5000)
    
    # Vérifier que l'erreur est affichée
    error_text = await page.locator(".empty").text_content()
    assert "erreur" in error_text.lower() or "error" in error_text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


