#!/usr/bin/env python3
"""
Simple ScrapingBee Test 

This script tests ScrapingBee directly using the recommended format from the documentation:
{"proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"}
"""
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_scrapingbee(api_key=None, test_url="https://httpbin.org/ip"):
    """
    Test ScrapingBee with the correct proxy format
    """
    # Get the API key
    if not api_key:
        api_key = os.getenv("SCRAPINGBEE_KEY")
        if not api_key:
            print("❌ No ScrapingBee API key found. Please provide as argument or set SCRAPINGBEE_KEY env var.")
            return False
    
    print(f"🔑 Using ScrapingBee API key: {api_key[:5]}...{api_key[-5:]}")
    print(f"🌐 Testing URL: {test_url}")
    
    # First, make a request without a proxy to compare
    print("\n1️⃣ Making a direct request (no proxy):")
    try:
        direct_response = requests.get(test_url, timeout=10)
        print(f"✅ Status code: {direct_response.status_code}")
        print(f"📄 Response: {direct_response.text[:200]}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Now, test with ScrapingBee using the correct format (#2 according to memory)
    print("\n2️⃣ Testing with ScrapingBee proxy format #2:")
    proxy_url = f"http://{api_key}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    print(f"🔄 Using proxy: {proxy_url.replace(api_key, api_key[:5] + '...' + api_key[-5:])}")
    
    try:
        proxy_response = requests.get(
            test_url, 
            proxies=proxies,
            timeout=30  # Longer timeout for proxy
        )
        print(f"✅ Status code: {proxy_response.status_code}")
        print(f"📄 Response: {proxy_response.text[:200]}")
        
        # Compare the results
        if direct_response.text != proxy_response.text:
            print("\n✅ SUCCESS: The responses are different, indicating ScrapingBee is working!")
            print(f"Direct IP: {direct_response.json().get('origin', 'unknown')}")
            try:
                print(f"Proxy IP: {proxy_response.json().get('origin', 'unknown')}")
            except:
                print(f"Proxy response couldn't be parsed as JSON")
            return True
        else:
            print("\n❌ The responses are identical, indicating ScrapingBee may not be working correctly.")
            return False
    except Exception as e:
        print(f"❌ Error with ScrapingBee: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ScrapingBee integration")
    parser.add_argument("--api-key", type=str, 
                        help="ScrapingBee API key (or set SCRAPINGBEE_KEY env var)")
    parser.add_argument("--url", type=str, default="https://httpbin.org/ip",
                        help="URL to test (default: https://httpbin.org/ip)")
    
    args = parser.parse_args()
    
    test_scrapingbee(args.api_key, args.url)
