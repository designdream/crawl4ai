#!/usr/bin/env python3
"""
ScrapingBee Verification Script

This script verifies that ScrapingBee is working correctly with your Crawl4AI application.
It tests both formats of proxy configuration to determine which one works correctly.
"""

import os
import json
import asyncio
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai.async_webcrawler import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, ProxyConfig


async def test_scrapingbee(api_key, test_url="https://httpbin.org/ip"):
    """Test ScrapingBee with different proxy configurations"""
    
    results = {}
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("SCRAPINGBEE_KEY")
        if not api_key:
            print("❌ No ScrapingBee API key provided. Please provide it as an argument or set SCRAPINGBEE_KEY environment variable.")
            return False
    
    print(f"🔑 ScrapingBee API Key: {api_key[:5]}...{api_key[-5:]}")
    print(f"🌐 Testing URL: {test_url}")
    
    # Test 1: Direct connection (no proxy)
    print("\n🔍 Test 1: Direct connection (no proxy)")
    browser_config = BrowserConfig(headless=True, verbose=True)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url)
            print(f"✅ Direct connection successful")
            print(f"📄 Content: {result.extracted_content[:200]}...")
            results["direct"] = result.extracted_content
    except Exception as e:
        print(f"❌ Direct connection failed: {str(e)}")
        results["direct"] = str(e)
    
    # Test 2: ScrapingBee with Format 1 (object format)
    print("\n🔍 Test 2: ScrapingBee with Format 1 (object format)")
    proxy_config = {
        "server": "http://proxy.scrapingbee.com:8886",
        "username": api_key,
        "password": "render_js=true&premium=true"
    }
    
    browser_config = BrowserConfig(headless=True, verbose=True)
    crawler_config = CrawlerRunConfig(proxy_config=proxy_config)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=crawler_config)
            print(f"✅ ScrapingBee Format 1 successful")
            print(f"📄 Content: {result.extracted_content[:200]}...")
            results["format1"] = result.extracted_content
    except Exception as e:
        print(f"❌ ScrapingBee Format 1 failed: {str(e)}")
        results["format1"] = str(e)
    
    # Test 3: ScrapingBee with Format 2 (URL format)
    print("\n🔍 Test 3: ScrapingBee with Format 2 (URL format)")
    proxy_url = f"http://{api_key}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
    
    browser_config = BrowserConfig(headless=True, verbose=True, proxy=proxy_url)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url)
            print(f"✅ ScrapingBee Format 2 successful")
            print(f"📄 Content: {result.extracted_content[:200]}...")
            results["format2"] = result.extracted_content
    except Exception as e:
        print(f"❌ ScrapingBee Format 2 failed: {str(e)}")
        results["format2"] = str(e)
    
    # Test 4: ScrapingBee with ProxyConfig object
    print("\n🔍 Test 4: ScrapingBee with ProxyConfig object")
    proxy_config = ProxyConfig(
        server="http://proxy.scrapingbee.com:8886",
        username=api_key,
        password="render_js=true&premium=true"
    )
    
    browser_config = BrowserConfig(headless=True, verbose=True)
    crawler_config = CrawlerRunConfig(proxy_config=proxy_config)
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=test_url, config=crawler_config)
            print(f"✅ ScrapingBee ProxyConfig successful")
            print(f"📄 Content: {result.extracted_content[:200]}...")
            results["proxy_config"] = result.extracted_content
    except Exception as e:
        print(f"❌ ScrapingBee ProxyConfig failed: {str(e)}")
        results["proxy_config"] = str(e)
    
    # Compare results to determine if ScrapingBee is working
    print("\n📊 Results Summary:")
    
    # Check if the direct connection response differs from ScrapingBee responses
    # This indicates ScrapingBee is being used (different IP addresses)
    proxy_working = False
    for test_name, content in results.items():
        if test_name != "direct" and content != results["direct"]:
            print(f"✅ {test_name} produced different results than direct connection (ScrapingBee appears to be working)")
            proxy_working = True
        elif test_name != "direct":
            print(f"❌ {test_name} produced the same results as direct connection (ScrapingBee may not be working)")
    
    # Save the results to a JSON file for detailed analysis
    with open("scrapingbee_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n🔍 Detailed results saved to scrapingbee_test_results.json")
    
    return proxy_working

def main():
    parser = argparse.ArgumentParser(description='Verify ScrapingBee integration with Crawl4AI')
    parser.add_argument('--api-key', type=str, help='ScrapingBee API key (or set SCRAPINGBEE_KEY env var)')
    parser.add_argument('--url', type=str, default="https://httpbin.org/ip", 
                       help='URL to test (default: https://httpbin.org/ip)')
    
    args = parser.parse_args()
    
    # Run the test
    asyncio.run(test_scrapingbee(args.api_key, args.url))

if __name__ == "__main__":
    main()
