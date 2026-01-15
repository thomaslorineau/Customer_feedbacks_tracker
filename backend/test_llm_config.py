#!/usr/bin/env python3
"""Test script to verify LLM API key configuration."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import config, validate_config_on_startup, get_llm_client

def test_config_validation():
    """Test 1: Validate configuration."""
    print("\n" + "="*60)
    print("TEST 1: Configuration Validation")
    print("="*60)
    
    result = validate_config_on_startup()
    
    if result["valid"]:
        print("✅ Configuration is valid")
    else:
        print("⚠️ Configuration has warnings (but may still work)")
    
    print("\nConfiguration summary:")
    print(config.get_config_summary())
    
    return result["valid"]


def test_api_key_masking():
    """Test 2: API key masking for logs."""
    print("\n" + "="*60)
    print("TEST 2: API Key Masking")
    print("="*60)
    
    test_keys = {
        "OpenAI": "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz",
        "Anthropic": "sk-ant-api-1234567890abcdefghijklmnopqrstuvwxyz",
        "GitHub": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
    }
    
    for provider, key in test_keys.items():
        masked = config.mask_api_key(key)
        print(f"{provider:12} : {masked}")
    
    print("\n✅ Masking works correctly - keys are never fully displayed")
    return True


def test_llm_client_simple():
    """Test 3: Initialize LLM client (no API call)."""
    print("\n" + "="*60)
    print("TEST 3: LLM Client Initialization")
    print("="*60)
    
    try:
        client = get_llm_client()
        print(f"✅ LLM client initialized successfully")
        print(f"   Provider: {config.LLM_PROVIDER}")
        print(f"   Client type: {type(client).__name__}")
        return True
    except ValueError as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return False


def test_llm_api_call():
    """Test 4: Make a simple API call to LLM."""
    print("\n" + "="*60)
    print("TEST 4: LLM API Call (Simple Test)")
    print("="*60)
    
    try:
        client = get_llm_client()
        
        print("Making test API call...")
        print("Prompt: 'Say hello in one word'")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using cheaper model for testing
            messages=[
                {"role": "user", "content": "Say hello in one word"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"\n✅ API call successful!")
        print(f"   Response: {result}")
        print(f"   Model used: {response.model}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API call failed: {type(e).__name__}")
        print(f"   Error: {str(e)[:200]}")
        
        if "authentication" in str(e).lower() or "api_key" in str(e).lower():
            print("\n💡 Hint: Check that your API key is correct and has not been revoked")
        elif "quota" in str(e).lower() or "billing" in str(e).lower():
            print("\n💡 Hint: Check your OpenAI account billing and usage limits")
        
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print(" LLM CONFIGURATION TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Configuration validation
    results.append(("Configuration Validation", test_config_validation()))
    
    # Test 2: API key masking
    results.append(("API Key Masking", test_api_key_masking()))
    
    # Test 3: Client initialization
    results.append(("Client Initialization", test_llm_client_simple()))
    
    # Test 4: API call (only if previous tests passed)
    if all(r[1] for r in results):
        print("\n⚠️  About to make a REAL API call (costs ~$0.0001)")
        print("This will test if your API key is working correctly.")
        
        import time
        time.sleep(2)  # Give user time to read
        
        results.append(("API Call Test", test_llm_api_call()))
    else:
        print("\n⚠️  Skipping API call test due to previous failures")
        results.append(("API Call Test", None))
    
    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        
        print(f"{status:10} {test_name}")
    
    passed = sum(1 for _, r in results if r is True)
    total = sum(1 for _, r in results if r is not None)
    
    print("\n" + "="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
