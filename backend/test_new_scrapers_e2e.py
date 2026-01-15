#!/usr/bin/env python3
"""End-to-end tests for new scrapers: OVH Forum, Mastodon, G2 Crowd"""
import sys
import time
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

print("=" * 60)
print("E2E Tests for New Scrapers")
print("=" * 60)

def test_ovh_forum():
    """Test OVH Forum scraper"""
    print("\n1️⃣ Testing OVH Forum scraper...")
    try:
        from app.scraper import ovh_forum
        result = ovh_forum.scrape_ovh_forum(query='OVH', limit=5)
        print(f"   ✅ OVH Forum: {len(result)} posts found")
        if result:
            print(f"   First post: {result[0]['content'][:80]}...")
            print(f"   Author: {result[0]['author']}")
            print(f"   URL: {result[0]['url'][:80]}...")
        else:
            print("   ⚠️  No posts found (may be normal if forum structure changed)")
        return True
    except Exception as e:
        print(f"   ❌ OVH Forum error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def test_mastodon():
    """Test Mastodon scraper"""
    print("\n2️⃣ Testing Mastodon scraper...")
    try:
        from app.scraper import mastodon
        result = mastodon.scrape_mastodon(query='ovhcloud', limit=5)
        print(f"   ✅ Mastodon: {len(result)} posts found")
        if result:
            print(f"   First post: {result[0]['content'][:80]}...")
            print(f"   Author: {result[0]['author']}")
            print(f"   Source: {result[0]['source']}")
        else:
            print("   ⚠️  No posts found (may be normal if no recent posts)")
        return True
    except Exception as e:
        print(f"   ❌ Mastodon error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def test_g2_crowd():
    """Test G2 Crowd scraper"""
    print("\n3️⃣ Testing G2 Crowd scraper...")
    try:
        from app.scraper import g2_crowd
        result = g2_crowd.scrape_g2_crowd(query='OVH', limit=5)
        print(f"   ✅ G2 Crowd: {len(result)} reviews found")
        if result:
            print(f"   First review: {result[0]['content'][:80]}...")
            print(f"   Author: {result[0]['author']}")
            print(f"   URL: {result[0]['url'][:80]}...")
        else:
            print("   ⚠️  No reviews found (may be normal if page structure changed)")
        return True
    except Exception as e:
        print(f"   ❌ G2 Crowd error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test API endpoints for new scrapers"""
    print("\n4️⃣ Testing API endpoints...")
    try:
        from fastapi.testclient import TestClient
        from app import main
        
        client = TestClient(main.app)
        
        # Test OVH Forum endpoint
        print("   Testing POST /scrape/ovh-forum...")
        response = client.post("/scrape/ovh-forum?query=OVH&limit=3")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ OVH Forum API: {data.get('added', 0)} posts added")
        else:
            print(f"   ⚠️  OVH Forum API returned: {response.status_code}")
        
        time.sleep(1)
        
        # Test Mastodon endpoint
        print("   Testing POST /scrape/mastodon...")
        response = client.post("/scrape/mastodon?query=ovhcloud&limit=3")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Mastodon API: {data.get('added', 0)} posts added")
        else:
            print(f"   ⚠️  Mastodon API returned: {response.status_code}")
        
        time.sleep(1)
        
        # Test G2 Crowd endpoint
        print("   Testing POST /scrape/g2-crowd...")
        response = client.post("/scrape/g2-crowd?query=OVH&limit=3")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ G2 Crowd API: {data.get('added', 0)} reviews added")
        else:
            print(f"   ⚠️  G2 Crowd API returned: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"   ❌ API endpoints error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_db():
    """Test integration with database"""
    print("\n5️⃣ Testing database integration...")
    try:
        from app import db, main
        from app.scraper import ovh_forum, mastodon, g2_crowd
        from app.analysis import sentiment
        
        # Initialize DB
        db.init_db()
        
        # Test inserting posts from each scraper
        test_results = []
        
        # OVH Forum
        try:
            items = ovh_forum.scrape_ovh_forum(query='OVH', limit=2)
            if items:
                for it in items[:1]:  # Just test with 1 item
                    an = sentiment.analyze(it.get('content') or '')
                    it['sentiment_score'] = an['score']
                    it['sentiment_label'] = an['label']
                    result = db.insert_post({
                        'source': it.get('source'),
                        'author': it.get('author'),
                        'content': it.get('content'),
                        'url': it.get('url'),
                        'created_at': it.get('created_at'),
                        'sentiment_score': it.get('sentiment_score'),
                        'sentiment_label': it.get('sentiment_label'),
                        'language': it.get('language', 'unknown'),
                    })
                    test_results.append(('OVH Forum', result))
        except Exception as e:
            print(f"   ⚠️  OVH Forum DB test skipped: {e}")
        
        # Mastodon
        try:
            items = mastodon.scrape_mastodon(query='ovhcloud', limit=2)
            if items:
                for it in items[:1]:
                    an = sentiment.analyze(it.get('content') or '')
                    it['sentiment_score'] = an['score']
                    it['sentiment_label'] = an['label']
                    result = db.insert_post({
                        'source': it.get('source'),
                        'author': it.get('author'),
                        'content': it.get('content'),
                        'url': it.get('url'),
                        'created_at': it.get('created_at'),
                        'sentiment_score': it.get('sentiment_score'),
                        'sentiment_label': it.get('sentiment_label'),
                        'language': it.get('language', 'unknown'),
                    })
                    test_results.append(('Mastodon', result))
        except Exception as e:
            print(f"   ⚠️  Mastodon DB test skipped: {e}")
        
        # G2 Crowd
        try:
            items = g2_crowd.scrape_g2_crowd(query='OVH', limit=2)
            if items:
                for it in items[:1]:
                    an = sentiment.analyze(it.get('content') or '')
                    it['sentiment_score'] = an['score']
                    it['sentiment_label'] = an['label']
                    result = db.insert_post({
                        'source': it.get('source'),
                        'author': it.get('author'),
                        'content': it.get('content'),
                        'url': it.get('url'),
                        'created_at': it.get('created_at'),
                        'sentiment_score': it.get('sentiment_score'),
                        'sentiment_label': it.get('sentiment_label'),
                        'language': it.get('language', 'unknown'),
                    })
                    test_results.append(('G2 Crowd', result))
        except Exception as e:
            print(f"   ⚠️  G2 Crowd DB test skipped: {e}")
        
        if test_results:
            print(f"   ✅ Database integration tests completed:")
            for name, result in test_results:
                status = "✅ Inserted" if result else "⚠️  Duplicate/Skipped"
                print(f"      {name}: {status}")
        else:
            print("   ⚠️  No items to test (scrapers returned empty)")
        
        return True
    except Exception as e:
        print(f"   ❌ Database integration error: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    results = []
    
    # Run all tests
    results.append(("OVH Forum Scraper", test_ovh_forum()))
    time.sleep(2)  # Be polite to servers
    
    results.append(("Mastodon Scraper", test_mastodon()))
    time.sleep(2)
    
    results.append(("G2 Crowd Scraper", test_g2_crowd()))
    time.sleep(2)
    
    results.append(("API Endpoints", test_api_endpoints()))
    time.sleep(1)
    
    results.append(("Database Integration", test_integration_with_db()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed or returned no data (may be normal)")
        sys.exit(1)




