#!/usr/bin/env python3
"""
ScrapingBee Integration Test for Crawl4AI

This script tests the integration between ScrapingBee proxy services and your
authenticated Crawl4AI deployment.
"""

import argparse
import json
import requests
import sys

def test_scrapingbee_integration(crawl4ai_token, scrapingbee_api_key, test_url="https://httpbin.org/ip"):
    """
    Test the integration between ScrapingBee and Crawl4AI
    
    Args:
        crawl4ai_token: Your Crawl4AI JWT authentication token
        scrapingbee_api_key: Your ScrapingBee API key
        test_url: URL to test scraping (default: httpbin.org/ip which shows the IP)
    """
    print(f"Testing ScrapingBee integration with Crawl4AI...")
    print(f"Target URL: {test_url}")
    
    # Crawl4AI endpoint
    crawl4ai_url = "https://s.dy.me/crawl"
    
    # Headers with Crawl4AI authentication
    headers = {
        "Authorization": f"Bearer {crawl4ai_token}",
        "Content-Type": "application/json"
    }
    
    # First test without ScrapingBee (direct connection)
    print("\n1. Testing direct connection (without ScrapingBee):")
    direct_data = {
        "urls": [test_url],
        "browser_config": {
            "headless": True
        }
    }
    
    try:
        direct_response = requests.post(
            crawl4ai_url, 
            headers=headers, 
            json=direct_data,
            timeout=30
        )
        direct_result = direct_response.json()
        print(f"Status: {direct_response.status_code}")
        print(f"Response: {json.dumps(direct_result, indent=2)}")
    except Exception as e:
        print(f"Error with direct connection: {str(e)}")
    
    # Now test with ScrapingBee proxy
    print("\n2. Testing with ScrapingBee proxy:")
    scrapingbee_data = {
        "urls": [test_url],
        "browser_config": {
            "headless": True,
            "proxy": {
                "server": "http://proxy.scrapingbee.com:8886",
                "username": scrapingbee_api_key,
                "password": "render_js=true"
            }
        }
    }
    
    try:
        proxy_response = requests.post(
            crawl4ai_url, 
            headers=headers, 
            json=scrapingbee_data,
            timeout=60  # Longer timeout for proxy requests
        )
        proxy_result = proxy_response.json()
        print(f"Status: {proxy_response.status_code}")
        print(f"Response: {json.dumps(proxy_result, indent=2)}")
    except Exception as e:
        print(f"Error with ScrapingBee proxy: {str(e)}")
    
    print("\nComparison:")
    print("If the IP addresses are different between the two requests, ScrapingBee is working correctly!")
    print("If you see JavaScript-rendered content in the ScrapingBee response, the render_js option is working!")

def main():
    parser = argparse.ArgumentParser(description='Test ScrapingBee integration with Crawl4AI')
    parser.add_argument('--crawl4ai-token', type=str, required=True, help='Crawl4AI JWT token')
    parser.add_argument('--scrapingbee-key', type=str, required=True, help='ScrapingBee API key')
    parser.add_argument('--url', type=str, default="https://httpbin.org/ip", 
                      help='URL to test (default: https://httpbin.org/ip)')
    
    args = parser.parse_args()
    
    test_scrapingbee_integration(
        args.crawl4ai_token,
        args.scrapingbee_key,
        args.url
    )

if __name__ == "__main__":
    main()
