#!/usr/bin/env python3
"""
Test script to verify the server-optimized ScrapingBee integration for DigitalOcean deployment.
"""
import os
import time
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after logger setup
from crawl4ai.scrapingbee_helper import get_optimized_scrapingbee_config, detect_site_type
from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient

# Test URLs - including mix of static and JS-heavy sites
TEST_URLS = [
    # Static site
    "https://www.rn.ca.gov/",
    # JS-heavy site 
    "https://www.ncsbn.org/"
]

def test_scrapingbee_helper():
    """Test server-optimized ScrapingBee helper functions."""
    # Ensure environment variables are loaded
    load_dotenv(override=True)
    
    # Check for ScrapingBee API key
    sb_key = os.getenv("SCRAPINGBEE_API_KEY")
    if not sb_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable not found!")
        logger.error("   Please set this variable before running this test.")
        return False
    
    logger.info(f"✅ SCRAPINGBEE_API_KEY found (starts with: {sb_key[:5]}...)")
    
    # Test site type detection
    for url in TEST_URLS:
        site_type = detect_site_type(url)
        logger.info(f"✅ Site type detection for {url}: {site_type}")
    
    # Test config generation
    config = get_optimized_scrapingbee_config(
        api_key=sb_key,
        render_js=True,
        extract_remotely=True
    )
    
    if config and isinstance(config, dict) and len(config) > 0:
        logger.info(f"✅ Successfully generated ScrapingBee config with {len(config)} parameters")
        return True
    else:
        logger.error("❌ Failed to generate ScrapingBee config")
        return False

def test_direct_client():
    """Test the DirectScrapingBeeClient."""
    # Create client
    client = DirectScrapingBeeClient()
    
    if not client.api_key:
        logger.error("❌ ScrapingBee client initialization failed - no API key")
        return False
    
    logger.info("✅ DirectScrapingBeeClient initialized successfully")
    
    # Test crawling
    results = []
    
    for url in TEST_URLS:
        logger.info(f"Testing DirectScrapingBeeClient with URL: {url}")
        start_time = time.time()
        
        try:
            # Crawl with default parameters
            response = client.crawl_url(url)
            
            # Record timing
            duration = time.time() - start_time
            
            # Check response
            success = isinstance(response, dict) and "html" in response
            
            # Log results
            if success:
                html_length = len(response.get("html", ""))
                links_count = len(response.get("links", []))
                logger.info(f"✅ Successfully crawled {url} in {duration:.2f} seconds")
                logger.info(f"   HTML size: {html_length} bytes, Links extracted: {links_count}")
            else:
                logger.error(f"❌ Failed to crawl {url}")
                if isinstance(response, dict) and "error" in response:
                    logger.error(f"   Error: {response['error']}")
            
            # Store result
            results.append({
                "url": url,
                "success": success,
                "duration_seconds": round(duration, 2),
                "response_keys": list(response.keys()) if isinstance(response, dict) else "Not a dictionary"
            })
        
        except Exception as e:
            logger.error(f"❌ Error testing {url}: {str(e)}")
            results.append({
                "url": url,
                "success": False,
                "error": str(e)
            })
    
    # Check if any test succeeded
    success_count = sum(1 for result in results if result.get("success"))
    if success_count > 0:
        logger.info(f"✅ DirectScrapingBeeClient tests successful: {success_count}/{len(results)} URLs")
        return True
    else:
        logger.error("❌ All DirectScrapingBeeClient tests failed")
        return False

def run_tests():
    """Run all server-optimized ScrapingBee integration tests."""
    logger.info("==== TESTING SERVER-OPTIMIZED SCRAPINGBEE INTEGRATION ====")
    
    # Step 1: Test helper functions
    helper_success = test_scrapingbee_helper()
    
    # Step 2: Test direct client
    if helper_success:
        logger.info("\n==== TESTING DIRECT SCRAPINGBEE CLIENT ====")
        client_success = test_direct_client()
    else:
        logger.error("❌ Helper tests failed, skipping client tests")
        client_success = False
    
    # Summarize results
    logger.info("\n==== TEST SUMMARY ====")
    if helper_success and client_success:
        logger.info("✅ All server-optimized ScrapingBee tests PASSED!")
        logger.info("✅ Server-optimized ScrapingBee integration is ready for DigitalOcean deployment")
    else:
        logger.warning("⚠️ Some server-optimized ScrapingBee tests FAILED")
    
    logger.info("Test complete!")

if __name__ == "__main__":
    run_tests()
