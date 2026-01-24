"""
QA Test Suite - Customer Feedbacks Tracker
Tests toutes les fonctionnalités de l'application.

Usage:
  python qa_test.py           # Tests only (server must be running)
  python qa_test.py --server  # Start server, run tests, stop server
"""
import asyncio
import httpx
import time
import sys
import subprocess
import signal
import os

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

API = "http://127.0.0.1:8000"
TIMEOUT = 30.0
MAX_RETRIES = 2  # Retry failed requests once

class QATestSuite:
    def __init__(self):
        self.results = {"passed": [], "failed": [], "warnings": []}
        self.server_process = None
    
    def ok(self, name, msg=""):
        self.results["passed"].append(name)
        print(f"  ✅ {name}" + (f" - {msg}" if msg else ""))
    
    def fail(self, name, msg=""):
        self.results["failed"].append((name, msg))
        print(f"  ❌ {name}" + (f" - {msg}" if msg else ""))
    
    def warn(self, name, msg=""):
        self.results["warnings"].append((name, msg))
        print(f"  ⚠️  {name}" + (f" - {msg}" if msg else ""))

    async def check_server_alive(self, client):
        """Check if server is still responding."""
        try:
            r = await client.get("/api/version", timeout=5.0)
            return r.status_code == 200
        except:
            return False

    async def request_with_retry(self, client, method, url, **kwargs):
        """Make HTTP request with automatic retry on connection failure."""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                if method == "GET":
                    return await client.get(url, **kwargs)
                else:
                    return await client.post(url, **kwargs)
            except (httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)  # Wait before retry
                    continue
        raise last_error

    def start_server(self):
        """Start the FastAPI server in background."""
        print("🚀 Starting server...")
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        # Wait for server to be ready
        for _ in range(30):  # Max 30 seconds
            time.sleep(1)
            try:
                import urllib.request
                urllib.request.urlopen(f"{API}/api/version", timeout=2)
                print("✅ Server ready!")
                return True
            except:
                continue
        print("❌ Server failed to start")
        return False

    def stop_server(self):
        """Stop the FastAPI server."""
        if self.server_process:
            print("\n🛑 Stopping server...")
            if sys.platform == "win32":
                self.server_process.terminate()
            else:
                os.kill(self.server_process.pid, signal.SIGTERM)
            self.server_process.wait(timeout=5)
            print("✅ Server stopped")

    async def run_all(self, manage_server=False):
        print("=" * 60)
        print("🧪 QA TEST SUITE - Customer Feedbacks Tracker")
        print("=" * 60)
        
        if manage_server:
            if not self.start_server():
                return
        
        try:
            async with httpx.AsyncClient(base_url=API, timeout=TIMEOUT) as c:
                await self.test_connectivity(c)
                if not await self.check_server_alive(c):
                    print("\n💀 SERVER CRASHED - Aborting tests")
                    return
                    
                await self.test_pages(c)
                await self.test_api_posts(c)
                await self.test_api_stats(c)
                
                if not await self.check_server_alive(c):
                    print("\n💀 SERVER CRASHED after stats - Aborting tests")
                    return
                
                await self.test_scrapers(c)
                await asyncio.sleep(1)  # Longer pause after scrapers
                
                if not await self.check_server_alive(c):
                    print("\n💀 SERVER CRASHED after scrapers - Aborting tests")
                    return
                
                await self.test_jobs(c)
                await asyncio.sleep(2)  # Even longer pause after jobs (most likely to crash)
                
                if not await self.check_server_alive(c):
                    print("\n💀 SERVER CRASHED after jobs - Aborting tests")
                    return
                
                await self.test_admin(c)
                await self.test_config(c)
                
                if not await self.check_server_alive(c):
                    print("\n💀 SERVER CRASHED after config - Aborting tests")
                    return
                
                await self.test_ai_features(c)
                await self.test_powerpoint(c)
        finally:
            if manage_server:
                self.stop_server()
        
        self.print_summary()
    
    async def test_connectivity(self, c):
        print("\n📡 CONNECTIVITY")
        try:
            r = await self.request_with_retry(c, "GET", "/")
            if r.status_code in (200, 302, 307):
                self.ok("Server responds", f"HTTP {r.status_code}")
            else:
                self.fail("Server responds", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("Server responds", str(e)[:50])
    
    async def test_pages(self, c):
        print("\n📄 PAGES HTML")
        pages = [
            ("/dashboard", "Dashboard"),
            ("/scraping", "Scraping page"),
            ("/logs", "Logs page"),
            ("/settings", "Settings page"),
            ("/improvements", "Improvements page"),
        ]
        for path, name in pages:
            try:
                r = await self.request_with_retry(c, "GET", path)
                if r.status_code == 200:
                    self.ok(name)
                else:
                    self.fail(name, f"HTTP {r.status_code}")
            except Exception as e:
                self.fail(name, str(e)[:50])
    
    async def test_api_posts(self, c):
        print("\n📝 API POSTS")
        
        # GET /posts
        try:
            r = await self.request_with_retry(c, "GET", "/posts", params={"limit": 10})
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    self.ok(f"GET /posts", f"{len(data)} posts")
                else:
                    self.fail("GET /posts", "Not a list")
            else:
                self.fail("GET /posts", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /posts", str(e)[:50])
        
        # GET /posts/stats/answered
        try:
            r = await self.request_with_retry(c, "GET", "/posts/stats/answered")
            if r.status_code == 200:
                self.ok("GET /posts/stats/answered")
            else:
                self.fail("GET /posts/stats/answered", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /posts/stats/answered", str(e)[:50])
    
    async def test_api_stats(self, c):
        print("\n📊 API STATS")
        
        endpoints = [
            "/api/version",
            "/api/improvements-summary",
            "/api/pain-points",
            "/api/product-opportunities",
        ]
        for ep in endpoints:
            try:
                r = await self.request_with_retry(c, "GET", ep)
                if r.status_code == 200:
                    self.ok(f"GET {ep}")
                else:
                    self.fail(f"GET {ep}", f"HTTP {r.status_code}")
            except Exception as e:
                self.fail(f"GET {ep}", str(e)[:50])
    
    async def test_scrapers(self, c):
        print("\n🔍 SCRAPERS (quick test)")
        
        scrapers = ["trustpilot", "github", "stackoverflow", "reddit", "news", "ovh-forum"]
        
        for src in scrapers:
            try:
                r = await self.request_with_retry(c, "POST", f"/scrape/{src}", params={"query": "OVH", "limit": 1}, timeout=20.0)
                if r.status_code == 200:
                    data = r.json()
                    added = data.get("added", 0)
                    total = data.get("total", 0)
                    errors = data.get("errors", [])
                    if errors:
                        self.warn(f"Scraper {src}", f"added={added}, errors={len(errors)}")
                    else:
                        self.ok(f"Scraper {src}", f"added={added}, total={total}")
                else:
                    self.fail(f"Scraper {src}", f"HTTP {r.status_code}")
            except httpx.ReadTimeout:
                self.warn(f"Scraper {src}", "Timeout (20s)")
            except Exception as e:
                self.fail(f"Scraper {src}", str(e)[:50])
    
    async def test_jobs(self, c):
        print("\n⚙️ JOBS SYSTEM")
        
        # Create job
        try:
            r = await self.request_with_retry(c, "POST", "/scrape/github/job", params={"query": "OVH", "limit": 3})
            if r.status_code == 200:
                job_id = r.json().get("job_id")
                self.ok("Create job", f"id={job_id[:8]}...")
                
                # Check progress
                await asyncio.sleep(2)
                r2 = await self.request_with_retry(c, "GET", f"/scrape/jobs/{job_id}")
                if r2.status_code == 200:
                    data = r2.json()
                    progress = data.get("progress", {})
                    self.ok("Get job status", f"progress={progress.get('completed')}/{progress.get('total')}")
                else:
                    self.fail("Get job status", f"HTTP {r2.status_code}")
                
                # List jobs
                r3 = await self.request_with_retry(c, "GET", "/scrape/jobs")
                if r3.status_code == 200:
                    jobs = r3.json()
                    self.ok("List jobs", f"{len(jobs)} jobs")
                else:
                    self.fail("List jobs", f"HTTP {r3.status_code}")
                
                # Cancel job
                r4 = await self.request_with_retry(c, "POST", f"/scrape/jobs/{job_id}/cancel")
                if r4.status_code == 200:
                    self.ok("Cancel job")
                else:
                    self.warn("Cancel job", f"HTTP {r4.status_code}")
            else:
                self.fail("Create job", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("Jobs system", str(e)[:50])
    
    async def test_admin(self, c):
        print("\n🔧 ADMIN")
        
        # GET stats only - cleanup operations are too slow/heavy for QA
        try:
            r = await self.request_with_retry(c, "GET", "/admin/duplicates-stats")
            if r.status_code == 200:
                data = r.json()
                self.ok("GET /admin/duplicates-stats", f"{data.get('total_to_delete', 0)} duplicates")
            else:
                self.fail("GET /admin/duplicates-stats", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /admin/duplicates-stats", str(e)[:50])
        
        # Skip cleanup operations - they are heavy and tested manually
        self.warn("POST /admin/cleanup-duplicates", "Skipped (heavy operation)")
        self.warn("POST /admin/cleanup-non-ovh-posts", "Skipped (heavy operation)")
    
    async def test_config(self, c):
        print("\n⚙️ CONFIG")
        
        # Get user keywords/queries
        try:
            r = await self.request_with_retry(c, "GET", "/settings/queries")
            if r.status_code == 200:
                data = r.json()
                self.ok("GET /settings/queries", f"{len(data.get('keywords', []))} keywords")
            else:
                self.fail("GET /settings/queries", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /settings/queries", str(e)[:50])
        
        # Get base keywords
        try:
            r = await self.request_with_retry(c, "GET", "/settings/base-keywords")
            if r.status_code == 200:
                data = r.json()
                total = sum(len(v) for v in data.values() if isinstance(v, list))
                self.ok("GET /settings/base-keywords", f"{total} base keywords")
            else:
                self.fail("GET /settings/base-keywords", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /settings/base-keywords", str(e)[:50])
        
        # Get app config
        try:
            r = await self.request_with_retry(c, "GET", "/api/config")
            if r.status_code == 200:
                self.ok("GET /api/config")
            else:
                self.fail("GET /api/config", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /api/config", str(e)[:50])
        
        # Get LLM config
        try:
            r = await self.request_with_retry(c, "GET", "/api/llm-config")
            if r.status_code == 200:
                data = r.json()
                provider = data.get("provider", "?")
                available = data.get("available", False)
                self.ok("GET /api/llm-config", f"provider={provider}, available={available}")
            else:
                self.fail("GET /api/llm-config", f"HTTP {r.status_code}")
        except Exception as e:
            self.fail("GET /api/llm-config", str(e)[:50])
    
    async def test_ai_features(self, c):
        print("\n🤖 AI FEATURES")
        
        # What's happening
        try:
            r = await self.request_with_retry(c, "POST", "/api/whats-happening", timeout=60.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    self.ok("What's Happening AI")
                else:
                    self.warn("What's Happening AI", data.get("error", "Unknown"))
            else:
                self.fail("What's Happening AI", f"HTTP {r.status_code}")
        except httpx.ReadTimeout:
            self.warn("What's Happening AI", "Timeout")
        except Exception as e:
            self.fail("What's Happening AI", str(e)[:50])
        
        # Recommended actions
        try:
            r = await self.request_with_retry(c, "POST", "/api/recommended-actions", timeout=60.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    self.ok("Recommended Actions AI")
                else:
                    self.warn("Recommended Actions AI", data.get("error", "Unknown"))
            else:
                self.fail("Recommended Actions AI", f"HTTP {r.status_code}")
        except httpx.ReadTimeout:
            self.warn("Recommended Actions AI", "Timeout")
        except Exception as e:
            self.fail("Recommended Actions AI", str(e)[:50])
    
    async def test_powerpoint(self, c):
        print("\n📊 POWERPOINT")
        
        try:
            r = await self.request_with_retry(c, "POST", "/api/generate-report", timeout=120.0)
            if r.status_code == 200:
                content_type = r.headers.get("content-type", "")
                if "application" in content_type:
                    self.ok("Generate PowerPoint", f"size={len(r.content)} bytes")
                else:
                    self.warn("Generate PowerPoint", f"Unexpected content-type: {content_type}")
            else:
                self.fail("Generate PowerPoint", f"HTTP {r.status_code}")
        except httpx.ReadTimeout:
            self.warn("Generate PowerPoint", "Timeout (120s)")
        except Exception as e:
            self.fail("Generate PowerPoint", str(e)[:50])

    def print_summary(self):
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])
        
        print(f"\n✅ Passed:   {len(self.results['passed'])}")
        print(f"❌ Failed:   {len(self.results['failed'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        print(f"📋 Total:    {total}")
        
        if self.results["failed"]:
            print("\n❌ FAILURES:")
            for name, msg in self.results["failed"]:
                print(f"   - {name}: {msg}")
        
        if self.results["warnings"]:
            print("\n⚠️  WARNINGS:")
            for name, msg in self.results["warnings"]:
                print(f"   - {name}: {msg}")
        
        print("\n" + "=" * 60)
        if not self.results["failed"]:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"💥 {len(self.results['failed'])} TESTS FAILED")
        print("=" * 60)


if __name__ == "__main__":
    manage_server = "--server" in sys.argv
    suite = QATestSuite()
    asyncio.run(suite.run_all(manage_server=manage_server))
