"""
Test script to demonstrate ScrapingBee speed optimizations.

This script performs two concurrent requests to the same URL using:
1. Standard configuration
2. Speed-optimized configuration

Then it compares the results and timing to show the improvement.
"""
import os
import sys
import time
import asyncio
import requests
from typing import Dict, Tuple
import logging

# Add the parent directory to the path so we can import crawl4ai
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import from crawl4ai
from crawl4ai.scrapingbee_helper import (
    get_scrapingbee_proxy_config,
    get_optimized_scrapingbee_config,
    get_optimized_proxies_dict,
    verify_scrapingbee_integration
)

async def test_standard_request(url: str) -> Tuple[float, int, str]:
    """Make a request with standard config and time it"""
    start_time = time.time()
    
    # Get standard proxy config
    proxies = {
        "http": f"http://{os.getenv('SCRAPINGBEE_KEY')}:render_js=true&premium_proxy=true@proxy.scrapingbee.com:8886",
        "https": f"https://{os.getenv('SCRAPINGBEE_KEY')}:render_js=true&premium_proxy=true@proxy.scrapingbee.com:8887"
    }
    
    try:
        response = requests.get(
            url,
            proxies=proxies,
            verify=False,  # Required for ScrapingBee
            timeout=60  # Long timeout
        )
        
        duration = time.time() - start_time
        return duration, response.status_code, f"Content length: {len(response.text)} bytes"
    except Exception as e:
        duration = time.time() - start_time
        return duration, 0, f"Error: {str(e)}"

async def test_optimized_request(url: str) -> Tuple[float, int, str]:
    """Make a request with optimized config and time it"""
    start_time = time.time()
    
    # Get optimized proxy config with speed enhancements
    proxies = get_optimized_proxies_dict(
        render_js=False,       # Disable JS rendering for speed
        premium_proxy=True,    # Use premium proxies for reliability
        timeout_ms=15000,      # 15 seconds timeout
        block_resources=True,  # Block images, CSS, fonts, etc.
        block_ads=True,        # Block ads to speed up loading
        wait_browser=False     # Don't wait for onload event
    )
    
    try:
        response = requests.get(
            url,
            proxies=proxies,
            verify=False,  # Required for ScrapingBee
            timeout=30  # Shorter timeout
        )
        
        duration = time.time() - start_time
        return duration, response.status_code, f"Content length: {len(response.text)} bytes"
    except Exception as e:
        duration = time.time() - start_time
        return duration, 0, f"Error: {str(e)}"

async def run_comparison_tests():
    """Run both tests concurrently and compare results"""
    # Verify ScrapingBee integration first
    success, message = verify_scrapingbee_integration()
    if not success:
        logger.error(f"ScrapingBee integration is not working: {message}")
        return
    
    logger.info("ScrapingBee integration verified. Running speed comparison tests...")
    
    # Test URLs - add more as needed
    test_urls = [
        "https://news.ycombinator.com/",
        "https://www.wikipedia.org/",
    ]
    
    for url in test_urls:
        logger.info(f"\n\n--- Testing URL: {url} ---")
        
        # Run both tests concurrently
        standard_result, optimized_result = await asyncio.gather(
            test_standard_request(url),
            test_optimized_request(url)
        )
        
        # Unpack results
        standard_time, standard_status, standard_info = standard_result
        optimized_time, optimized_status, optimized_info = optimized_result
        
        # Calculate speedup
        if standard_time > 0:
            speedup = ((standard_time - optimized_time) / standard_time) * 100
        else:
            speedup = 0
        
        # Display results
        logger.info(f"\nStandard config:")
        logger.info(f"  Time: {standard_time:.2f} seconds")
        logger.info(f"  Status: {standard_status}")
        logger.info(f"  {standard_info}")
        
        logger.info(f"\nOptimized config:")
        logger.info(f"  Time: {optimized_time:.2f} seconds")
        logger.info(f"  Status: {optimized_status}")
        logger.info(f"  {optimized_info}")
        
        logger.info(f"\nSpeed improvement: {speedup:.1f}% faster")
        
        # Add a little delay between tests
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Run the comparison tests
    asyncio.run(run_comparison_tests())
