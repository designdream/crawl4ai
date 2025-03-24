#!/usr/bin/env python3
"""
Test script for the Hybrid Crawler integration in Crawl4AI.

This script verifies that both ScrapingBee and Serper integrations
are working properly in the hybrid crawler.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_hybrid_crawler():
    """Test the hybrid crawler with both ScrapingBee and Serper"""
    # First, load environment variables
    load_dotenv('.env', override=True)
    
    try:
        # Print environment variable status for debugging
        logger.info(f"Environment variables loaded. SCRAPINGBEE_KEY: {'✓' if 'SCRAPINGBEE_KEY' in os.environ else '✗'}, "  
                  f"SCRAPINGBEE_API_KEY: {'✓' if 'SCRAPINGBEE_API_KEY' in os.environ else '✗'}, "
                  f"SERPER_API_KEY: {'✓' if 'SERPER_API_KEY' in os.environ else '✗'}")
        
        # Make sure we're using a consistent API key format for ScrapingBee
        # as documented in our memory about ScrapingBee integration
        if 'SCRAPINGBEE_KEY' in os.environ and 'SCRAPINGBEE_API_KEY' not in os.environ:
            os.environ['SCRAPINGBEE_API_KEY'] = os.environ['SCRAPINGBEE_KEY']
            logger.info(f"Set SCRAPINGBEE_API_KEY from SCRAPINGBEE_KEY")
        elif 'SCRAPINGBEE_KEY' in os.environ and 'SCRAPINGBEE_API_KEY' in os.environ:
            # If both exist, use SCRAPINGBEE_KEY as the authoritative source
            if os.environ['SCRAPINGBEE_KEY'] != os.environ['SCRAPINGBEE_API_KEY']:
                logger.warning(f"⚠️ SCRAPINGBEE_KEY and SCRAPINGBEE_API_KEY have different values!")
                logger.info(f"Using SCRAPINGBEE_KEY value for consistency")
                os.environ['SCRAPINGBEE_API_KEY'] = os.environ['SCRAPINGBEE_KEY']
            
        # Import our hybrid crawler
        from crawl4ai.search.hybrid_crawler import initialize_hybrid_crawler
        
        # Check if we have the necessary API keys
        scrapingbee_key = os.environ.get('SCRAPINGBEE_API_KEY')
        serper_key = os.environ.get('SERPER_API_KEY')
        
        # Log the keys (partially hidden for security)
        if scrapingbee_key:
            visible_part = scrapingbee_key[:5] + '...' + scrapingbee_key[-5:] if len(scrapingbee_key) > 10 else '***'
            logger.info(f"ScrapingBee API Key: {visible_part}")
        if serper_key:
            visible_part = serper_key[:5] + '...' + serper_key[-5:] if len(serper_key) > 10 else '***'
            logger.info(f"Serper API Key: {visible_part}")
        
        if not scrapingbee_key:
            logger.error("❌ SCRAPINGBEE_API_KEY not set in environment")
            logger.info("Please set SCRAPINGBEE_API_KEY or SCRAPINGBEE_KEY in your .env.local file")
            return False
            
        if not serper_key:
            logger.warning("⚠️ SERPER_API_KEY not set in environment")
            logger.info("Search functionality will not work, but direct crawling will be tested")
        
        # Initialize the hybrid crawler
        logger.info("Initializing hybrid crawler...")
        crawler = initialize_hybrid_crawler()
        
        # Test direct crawling with ScrapingBee
        test_url = "https://example.com"
        logger.info(f"Testing direct crawling with ScrapingBee: {test_url}")
        
        crawl_result = crawler.crawl_url(test_url)
        
        if "error" in crawl_result:
            logger.error(f"❌ ScrapingBee crawling failed: {crawl_result['error']}")
            return False
            
        html_content = crawl_result.get("html", "")
        if "Example Domain" in html_content:
            logger.info("✅ SUCCESS: ScrapingBee crawling is working correctly")
            direct_crawl_success = True
        else:
            logger.error("❌ ScrapingBee crawling didn't return expected content")
            direct_crawl_success = False
        
        # Test Serper search if API key is available
        search_success = False
        if serper_key:
            test_query = "environment regulations"
            logger.info(f"Testing search with Serper: {test_query}")
            
            search_result = crawler.search(test_query, num_results=3)
            
            if "error" in search_result:
                logger.error(f"❌ Serper search failed: {search_result['error']}")
            else:
                organic_results = search_result.get("organic", [])
                if organic_results:
                    logger.info(f"✅ SUCCESS: Serper search returned {len(organic_results)} results")
                    search_success = True
                else:
                    logger.error("❌ Serper search didn't return any results")
        else:
            logger.warning("⚠️ Skipping Serper search test (no API key)")
        
        # Test the discover_and_crawl method if both APIs are available
        if serper_key and direct_crawl_success:
            test_topic = "healthcare regulations"
            logger.info(f"Testing discover_and_crawl with topic: {test_topic}")
            
            discover_results = crawler.discover_and_crawl(test_topic, max_urls=2)
            
            if discover_results:
                logger.info(f"✅ SUCCESS: discover_and_crawl returned {len(discover_results)} results")
                logger.info("🎉 Hybrid crawler is fully functional!")
                return True
            else:
                logger.error("❌ discover_and_crawl didn't return any results")
                return direct_crawl_success and search_success
        
        # Return overall success
        return direct_crawl_success and search_success
        
    except Exception as e:
        logger.error(f"❌ Exception during test: {str(e)}")
        return False

def main():
    """Main function"""
    success = test_hybrid_crawler()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
