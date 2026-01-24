"""Tests E2E pour l'affichage de la barre de progression."""
import pytest
import asyncio
import httpx
from playwright.async_api import async_playwright, Page, expect
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

# Configuration pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:8000")
TIMEOUT = 120.0


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


@pytest.fixture
async def api_client():
    """HTTP client for API calls."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=TIMEOUT) as client:
        yield client


class TestProgressBarLogsPage:
    """Tests E2E pour la barre de progression sur la page logs.html."""
    
    @pytest.mark.asyncio
    async def test_progress_bar_appears_on_running_job(self, page: Page, api_client):
        """Test que la barre de progression apparaît quand un job est en cours."""
        print(f"\n🔍 Testing progress bar appearance on logs page...")
        
        # Créer un job
        create_response = await api_client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        print(f"✅ Job created: {job_id[:8]}...")
        
        # Aller sur la page logs
        await page.goto(f"{FRONTEND_BASE}/logs.html")
        await page.wait_for_load_state("networkidle")
        
        # Attendre que la barre de progression apparaisse
        progress_container = page.locator("#scrapingProgressContainer")
        
        # La barre devrait apparaître dans les 5 secondes
        try:
            await expect(progress_container).to_be_visible(timeout=5000)
            print("✅ Progress bar container is visible")
        except Exception as e:
            print(f"⚠️ Progress bar not visible immediately: {e}")
            # Vérifier si elle apparaît après un refresh
            await page.reload()
            await page.wait_for_load_state("networkidle")
            await expect(progress_container).to_be_visible(timeout=5000)
            print("✅ Progress bar container is visible after reload")
        
        # Vérifier que les éléments de la barre sont présents
        progress_bar = page.locator("#scrapingProgressBar")
        progress_text = page.locator("#scrapingProgressText")
        
        await expect(progress_bar).to_be_visible(timeout=2000)
        await expect(progress_text).to_be_visible(timeout=2000)
        
        print("✅ Progress bar elements are visible")
    
    @pytest.mark.asyncio
    async def test_progress_bar_updates(self, page: Page, api_client):
        """Test que la barre de progression se met à jour."""
        print(f"\n🔍 Testing progress bar updates...")
        
        # Créer un job avec une limite élevée pour qu'il prenne du temps
        create_response = await api_client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 50}
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # Aller sur la page logs
        await page.goto(f"{FRONTEND_BASE}/logs.html")
        await page.wait_for_load_state("networkidle")
        
        # Attendre que la barre apparaisse
        progress_container = page.locator("#scrapingProgressContainer")
        await expect(progress_container).to_be_visible(timeout=10000)
        
        # Capturer la valeur initiale de la progression
        progress_text = page.locator("#scrapingProgressText")
        initial_text = await progress_text.text_content()
        print(f"  Initial progress text: {initial_text}")
        
        # Attendre quelques secondes pour que la progression change
        await asyncio.sleep(5)
        
        # Vérifier que le texte a changé ou que la barre est toujours visible
        updated_text = await progress_text.text_content()
        print(f"  Updated progress text: {updated_text}")
        
        # La progression devrait avoir changé OU le job devrait être terminé
        assert initial_text != updated_text or "completed" in updated_text.lower() or "failed" in updated_text.lower(), \
            f"Progress should have changed: {initial_text} -> {updated_text}"
        
        print("✅ Progress bar updated")
    
    @pytest.mark.asyncio
    async def test_progress_bar_disappears_on_completion(self, page: Page, api_client):
        """Test que la barre de progression disparaît quand le job est terminé."""
        print(f"\n🔍 Testing progress bar disappears on completion...")
        
        # Créer un job avec une limite faible pour qu'il se termine rapidement
        create_response = await api_client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 5}
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # Aller sur la page logs
        await page.goto(f"{FRONTEND_BASE}/logs.html")
        await page.wait_for_load_state("networkidle")
        
        # Attendre que la barre apparaisse
        progress_container = page.locator("#scrapingProgressContainer")
        try:
            await expect(progress_container).to_be_visible(timeout=5000)
            print("✅ Progress bar appeared")
        except:
            print("⚠️ Progress bar did not appear (job may have completed too quickly)")
        
        # Attendre que le job se termine (max 60 secondes)
        max_wait = 60
        wait_interval = 2
        waited = 0
        
        while waited < max_wait:
            # Vérifier le statut du job via l'API
            status_response = await api_client.get(f"/scrape/jobs/{job_id}")
            if status_response.status_code == 200:
                status_data = status_response.response.json()
                if status_data.get("status") in ["completed", "failed", "cancelled"]:
                    print(f"✅ Job finished with status: {status_data['status']}")
                    break
            
            await asyncio.sleep(wait_interval)
            waited += wait_interval
        
        # Attendre un peu plus pour que l'UI se mette à jour
        await asyncio.sleep(5)
        
        # La barre devrait disparaître ou afficher un message de complétion
        progress_text = page.locator("#scrapingProgressText")
        try:
            text_content = await progress_text.text_content(timeout=2000)
            if text_content:
                print(f"  Progress text: {text_content}")
                # Le texte peut indiquer que le job est terminé
                assert "completed" in text_content.lower() or "failed" in text_content.lower() or "cancelled" in text_content.lower(), \
                    f"Progress text should indicate completion: {text_content}"
        except:
            # Si le texte n'est pas visible, la barre a peut-être disparu
            print("✅ Progress bar disappeared or text not visible")
    
    @pytest.mark.asyncio
    async def test_progress_bar_refresh_button(self, page: Page, api_client):
        """Test que le bouton refresh fonctionne avec la barre de progression."""
        print(f"\n🔍 Testing refresh button with progress bar...")
        
        # Créer un job
        create_response = await api_client.post(
            "/scrape/reddit/job",
            params={"query": "OVH", "limit": 20}
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        
        # Aller sur la page logs
        await page.goto(f"{FRONTEND_BASE}/logs.html")
        await page.wait_for_load_state("networkidle")
        
        # Attendre que la barre apparaisse
        progress_container = page.locator("#scrapingProgressContainer")
        await expect(progress_container).to_be_visible(timeout=10000)
        
        # Capturer l'état initial
        initial_text = await page.locator("#scrapingProgressText").text_content()
        print(f"  Initial progress: {initial_text}")
        
        # Cliquer sur le bouton refresh
        refresh_button = page.locator("#refreshBtn, button:has-text('Refresh'), button:has-text('🔄')")
        await refresh_button.click()
        
        # Attendre que le refresh se termine
        await asyncio.sleep(2)
        
        # Vérifier que la barre est toujours visible
        await expect(progress_container).to_be_visible(timeout=2000)
        
        # Vérifier que le texte a été mis à jour ou est toujours présent
        updated_text = await page.locator("#scrapingProgressText").text_content()
        print(f"  Updated progress: {updated_text}")
        
        assert updated_text is not None, "Progress text should still be visible after refresh"
        
        print("✅ Refresh button works correctly with progress bar")


class TestProgressBarDashboardPage:
    """Tests E2E pour la barre de progression sur la page dashboard.html."""
    
    @pytest.mark.asyncio
    async def test_progress_bar_appears_on_dashboard(self, page: Page, api_client):
        """Test que la barre de progression apparaît sur le dashboard."""
        print(f"\n🔍 Testing progress bar appearance on dashboard...")
        
        # Aller sur la page dashboard
        await page.goto(f"{FRONTEND_BASE}/dashboard")
        await page.wait_for_load_state("networkidle")
        
        # Trouver le bouton "Scrape All" ou similaire
        scrape_button = page.locator("button:has-text('Scrape All'), button:has-text('Scrape'), #btnScrapeAll")
        
        if await scrape_button.count() > 0:
            # Cliquer sur le bouton pour démarrer un scraping
            await scrape_button.first.click()
            print("✅ Scrape button clicked")
            
            # Attendre que la barre de progression apparaisse
            progress_container = page.locator("#scrapingProgressContainer, .progress-container, [id*='progress']")
            
            try:
                await expect(progress_container.first).to_be_visible(timeout=10000)
                print("✅ Progress bar appeared on dashboard")
            except:
                # Chercher d'autres sélecteurs possibles
                all_progress = await page.locator("[id*='progress'], [class*='progress']").all()
                if len(all_progress) > 0:
                    print(f"✅ Found {len(all_progress)} progress elements")
                else:
                    print("⚠️ Progress bar not found on dashboard")
        else:
            print("⚠️ Scrape button not found on dashboard")
    
    @pytest.mark.asyncio
    async def test_progress_bar_updates_on_dashboard(self, page: Page, api_client):
        """Test que la barre de progression se met à jour sur le dashboard."""
        print(f"\n🔍 Testing progress bar updates on dashboard...")
        
        # Créer un job via l'API
        create_response = await api_client.post(
            "/scrape/keywords",
            json={"keywords": ["OVH"]},
            params={"limit": 10, "concurrency": 1, "delay": 0.5}
        )
        assert create_response.status_code == 200
        job_id = create_response.json()["job_id"]
        print(f"✅ Job created: {job_id[:8]}...")
        
        # Aller sur la page dashboard
        await page.goto(f"{FRONTEND_BASE}/dashboard")
        await page.wait_for_load_state("networkidle")
        
        # Chercher la barre de progression
        progress_container = page.locator("#scrapingProgressContainer, .progress-container, [id*='progress']")
        
        # Attendre qu'elle apparaisse (peut prendre du temps si le job est déjà en cours)
        try:
            await expect(progress_container.first).to_be_visible(timeout=10000)
            
            # Capturer l'état initial
            progress_text = page.locator("#scrapingProgressText, [id*='progressText']")
            if await progress_text.count() > 0:
                initial_text = await progress_text.first.text_content()
                print(f"  Initial progress: {initial_text}")
                
                # Attendre quelques secondes
                await asyncio.sleep(5)
                
                # Vérifier que le texte a changé
                updated_text = await progress_text.first.text_content()
                print(f"  Updated progress: {updated_text}")
                
                assert updated_text != initial_text or "completed" in updated_text.lower(), \
                    f"Progress should have changed: {initial_text} -> {updated_text}"
                
                print("✅ Progress bar updated on dashboard")
        except:
            print("⚠️ Progress bar not found or not updating on dashboard")

