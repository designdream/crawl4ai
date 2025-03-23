#!/usr/bin/env python3
"""
Standalone ScrapingBee Integration Test

This script tests ScrapingBee integration without depending on the full Crawl4AI codebase.
It verifies that ScrapingBee works correctly with the proper configuration.
"""

import os
import sys
import json
import logging
import argparse
import requests
import urllib3
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable SSL warnings for ScrapingBee requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_scrapingbee_proxy(api_key, render_js=True, premium=True, **kwargs):
    """
    Get ScrapingBee proxy configuration with the proper parameters
    
    Args:
        api_key: ScrapingBee API key
        render_js: Enable JavaScript rendering
        premium: Use premium proxies
        **kwargs: Additional parameters for ScrapingBee
    
    Returns:
        dict: Proxy configuration for requests
    """
    # Build password parameters
    params = []
    if render_js:
        params.append("render_js=true")
    if premium:
        params.append("premium=true")
    
    # Add any additional parameters
    for key, value in kwargs.items():
        params.append(f"{key}={value}")
    
    # Join parameters
    password = "&".join(params)
    
    # Format 1: Dictionary configuration (for browser configs)
    proxy_config = {
        "server": "http://proxy.scrapingbee.com:8886",
        "username": api_key,
        "password": password
    }
    
    # Format 2: URL format (for standard requests)
    proxy_url = f"http://{api_key}:{password}@proxy.scrapingbee.com:8886"
    
    return {
        "config": proxy_config,
        "url": proxy_url,
        "proxies": {
            "http": proxy_url,
            "https": proxy_url
        }
    }


def test_direct_connection(url):
    """Test direct connection without ScrapingBee"""
    logging.info(f"🔍 Testing direct connection to {url}")
    
    try:
        response = requests.get(url, timeout=10)
        logging.info(f"✅ Direct connection successful: Status {response.status_code}")
        
        if "httpbin.org/ip" in url:
            ip = response.json().get("origin", "unknown")
            logging.info(f"📌 Your direct IP: {ip}")
        
        return {
            "success": True,
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers)
        }
    except Exception as e:
        logging.error(f"❌ Direct connection failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def test_scrapingbee(api_key, url, render_js=True, premium=True, **kwargs):
    """
    Test ScrapingBee integration with proper configuration
    
    Args:
        api_key: ScrapingBee API key
        url: URL to test
        render_js: Enable JavaScript rendering
        premium: Use premium proxies
        **kwargs: Additional parameters for ScrapingBee
    
    Returns:
        dict: Test results
    """
    logging.info(f"🔍 Testing ScrapingBee connection to {url}")
    logging.info(f"🔑 Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Get proxy configuration
    proxy = get_scrapingbee_proxy(api_key, render_js, premium, **kwargs)
    logging.info(f"🔄 Using proxy: {proxy['url'].replace(api_key, api_key[:5] + '...' + api_key[-5:])}")
    
    try:
        # Make request through ScrapingBee proxy with SSL verification disabled
        response = requests.get(
            url, 
            proxies=proxy["proxies"],
            verify=False,  # Critical: Disable SSL verification
            timeout=30
        )
        logging.info(f"✅ ScrapingBee connection successful: Status {response.status_code}")
        
        if "httpbin.org/ip" in url:
            try:
                ip = response.json().get("origin", "unknown")
                logging.info(f"📌 ScrapingBee IP: {ip}")
            except:
                logging.warning("⚠️ Could not parse IP from response")
        
        return {
            "success": True,
            "status_code": response.status_code,
            "content": response.text,
            "headers": dict(response.headers)
        }
    except Exception as e:
        logging.error(f"❌ ScrapingBee connection failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def verify_scrapingbee_integration(api_key, test_url="https://httpbin.org/ip"):
    """
    Verify ScrapingBee integration by comparing direct and proxy requests
    
    Args:
        api_key: ScrapingBee API key
        test_url: URL to test
    
    Returns:
        tuple: (success, message)
    """
    # Test direct connection
    direct_result = test_direct_connection(test_url)
    
    if not direct_result["success"]:
        return False, f"❌ Direct connection failed: {direct_result.get('error')}"
    
    # Test ScrapingBee connection
    sb_result = test_scrapingbee(api_key, test_url)
    
    if not sb_result["success"]:
        return False, f"❌ ScrapingBee connection failed: {sb_result.get('error')}"
    
    # For IP endpoint, compare the IPs
    if "httpbin.org/ip" in test_url:
        try:
            direct_ip = json.loads(direct_result["content"])["origin"]
            sb_ip = json.loads(sb_result["content"])["origin"]
            
            if direct_ip != sb_ip:
                return True, f"✅ ScrapingBee is working! Direct IP: {direct_ip}, Proxy IP: {sb_ip}"
            else:
                return False, f"❌ ScrapingBee may not be working. Same IP for direct and proxy: {direct_ip}"
        except:
            return False, "❌ Could not compare IPs from responses"
    
    # For other URLs, just check if content differs
    if direct_result["content"] != sb_result["content"]:
        return True, "✅ ScrapingBee is working! Content differs between direct and proxy requests."
    else:
        return False, "❌ ScrapingBee may not be working. Same content for direct and proxy requests."


def test_all_formats(api_key, test_url="https://httpbin.org/ip"):
    """
    Test different ScrapingBee configuration formats
    
    Args:
        api_key: ScrapingBee API key
        test_url: URL to test
    """
    logging.info("\n====== Testing Different ScrapingBee Configurations ======")
    
    # Format 1: Basic
    logging.info("\n🔄 Format 1: Basic Configuration")
    basic_result = test_scrapingbee(api_key, test_url)
    
    # Format 2: With render_js and premium
    logging.info("\n🔄 Format 2: With render_js and premium")
    adv_result = test_scrapingbee(api_key, test_url, render_js=True, premium=True)
    
    # Format 3: With additional params
    logging.info("\n🔄 Format 3: With additional parameters")
    params_result = test_scrapingbee(
        api_key, test_url, 
        render_js=True, premium=True,
        country_code="us", 
        block_ads=True
    )
    
    # Compare with direct connection
    direct_result = test_direct_connection(test_url)
    
    # Save results to file for analysis
    results = {
        "direct": direct_result,
        "basic": basic_result,
        "advanced": adv_result,
        "with_params": params_result
    }
    
    # Save only headers and the first 1000 chars of content to keep file size reasonable
    for key in results:
        if "content" in results[key] and results[key]["content"]:
            results[key]["content"] = results[key]["content"][:1000] + "..." if len(results[key]["content"]) > 1000 else results[key]["content"]
    
    with open("scrapingbee_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"\n📊 Test results saved to scrapingbee_test_results.json")
    
    # Verify if at least one format worked
    success = False
    for result in [basic_result, adv_result, params_result]:
        if result["success"]:
            success = True
            break
    
    if success:
        logging.info("\n✅ At least one ScrapingBee configuration format worked!")
    else:
        logging.error("\n❌ All ScrapingBee configurations failed.")
    
    return success


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test ScrapingBee integration")
    parser.add_argument("--api-key", type=str, help="ScrapingBee API key")
    parser.add_argument("--url", type=str, default="https://httpbin.org/ip", help="URL to test")
    parser.add_argument("--test-all", action="store_true", help="Test all configuration formats")
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("SCRAPINGBEE_KEY")
    
    if not api_key:
        logging.error("❌ No ScrapingBee API key provided. Use --api-key or set SCRAPINGBEE_KEY env var.")
        sys.exit(1)
    
    if args.test_all:
        success = test_all_formats(api_key, args.url)
    else:
        success, message = verify_scrapingbee_integration(api_key, args.url)
        logging.info(f"\n{message}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
