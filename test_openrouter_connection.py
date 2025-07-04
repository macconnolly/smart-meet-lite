#!/usr/bin/env python3
"""
Test OpenRouter connectivity with various configurations.
This helps diagnose connection issues in corporate environments.
"""

import os
import sys
import httpx
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_direct_connection():
    """Test direct connection without any proxy."""
    print("\n=== Testing Direct Connection ===")
    try:
        response = httpx.get("https://openrouter.ai", timeout=10.0)
        print(f"✓ Direct connection successful: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Direct connection failed: {e}")
        return False

def test_with_ssl_disabled():
    """Test connection with SSL verification disabled."""
    print("\n=== Testing with SSL Verification Disabled ===")
    try:
        client = httpx.Client(verify=False)
        response = client.get("https://openrouter.ai", timeout=10.0)
        print(f"✓ Connection with SSL disabled successful: Status {response.status_code}")
        client.close()
        return True
    except Exception as e:
        print(f"✗ Connection with SSL disabled failed: {e}")
        return False

def test_with_proxy():
    """Test connection with proxy from environment variables."""
    print("\n=== Testing with Proxy Configuration ===")
    
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    
    if not (http_proxy or https_proxy):
        print("No proxy configuration found in environment variables")
        return False
    
    proxies = {}
    if http_proxy:
        proxies["http://"] = http_proxy
        print(f"Using HTTP proxy: {http_proxy}")
    if https_proxy:
        proxies["https://"] = https_proxy
        print(f"Using HTTPS proxy: {https_proxy}")
    
    try:
        client = httpx.Client(proxies=proxies, verify=False, timeout=10.0)
        response = client.get("https://openrouter.ai", timeout=10.0)
        print(f"✓ Connection with proxy successful: Status {response.status_code}")
        client.close()
        return True
    except Exception as e:
        print(f"✗ Connection with proxy failed: {e}")
        return False

def test_openrouter_api():
    """Test actual OpenRouter API call."""
    print("\n=== Testing OpenRouter API ===")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("✗ No OPENROUTER_API_KEY found in environment")
        return False
    
    # Get proxy configuration
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    ssl_verify = os.getenv("SSL_VERIFY", "true").lower() == "true"
    
    proxies = None
    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy
        print(f"Using proxy configuration: {proxies}")
    
    try:
        client = httpx.Client(proxies=proxies, verify=ssl_verify, timeout=30.0)
        
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openrouter/cypher-alpha:free",
                "messages": [{"role": "user", "content": "Say 'test' and nothing else"}],
                "max_tokens": 10
            }
        )
        
        if response.status_code == 200:
            print(f"✓ API call successful: {response.json()}")
            client.close()
            return True
        else:
            print(f"✗ API call failed with status {response.status_code}: {response.text}")
            client.close()
            return False
            
    except Exception as e:
        print(f"✗ API call failed with exception: {e}")
        return False

def print_environment_info():
    """Print relevant environment information."""
    print("\n=== Environment Information ===")
    print(f"HTTP_PROXY: {os.getenv('HTTP_PROXY', 'Not set')}")
    print(f"HTTPS_PROXY: {os.getenv('HTTPS_PROXY', 'Not set')}")
    print(f"http_proxy: {os.getenv('http_proxy', 'Not set')}")
    print(f"https_proxy: {os.getenv('https_proxy', 'Not set')}")
    print(f"NO_PROXY: {os.getenv('NO_PROXY', 'Not set')}")
    print(f"SSL_VERIFY: {os.getenv('SSL_VERIFY', 'Not set (defaults to true)')}")
    print(f"OPENROUTER_API_KEY: {'Set' if os.getenv('OPENROUTER_API_KEY') else 'Not set'}")

def main():
    """Run all connectivity tests."""
    print("OpenRouter Connectivity Test")
    print("============================")
    
    print_environment_info()
    
    # Run tests
    results = {
        "Direct Connection": test_direct_connection(),
        "SSL Disabled": test_with_ssl_disabled(),
        "With Proxy": test_with_proxy(),
        "API Call": test_openrouter_api()
    }
    
    # Summary
    print("\n=== Test Summary ===")
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    # Recommendations
    print("\n=== Recommendations ===")
    if not results["Direct Connection"] and not results["With Proxy"]:
        print("1. You appear to be behind a firewall. Configure proxy settings:")
        print("   export HTTPS_PROXY=http://your-proxy-server:port")
        print("   export HTTP_PROXY=http://your-proxy-server:port")
        
    if not results["SSL Disabled"] and results["Direct Connection"]:
        print("1. SSL verification might be the issue. Try setting:")
        print("   export SSL_VERIFY=false")
        
    if results["With Proxy"] and not results["API Call"]:
        print("1. Proxy works but API fails. Check your API key.")
        print("2. The proxy might be blocking API requests.")
        
    if all(not v for v in results.values()):
        print("1. All tests failed. This suggests a network-level block.")
        print("2. Contact your IT department for proxy configuration.")
        print("3. You may need to whitelist openrouter.ai")

if __name__ == "__main__":
    main()