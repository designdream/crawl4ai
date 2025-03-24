"""
Hybrid Crawler for Crawl4AI

This module integrates both ScrapingBee direct crawling and Serper search capabilities,
allowing the system to:
1. Crawl specific URLs using ScrapingBee for precise extraction
2. Discover new content via Serper search when specific URLs aren't known
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union

# Import ScrapingBee clients - use proxy-based client first, fallback to direct if needed
from crawl4ai.scrapingbee_proxy_direct import ProxyScrapingBeeClient
try:
    from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient
    direct_client_available = True
except ImportError:
    direct_client_available = False

# Import Serper search client
from crawl4ai.search.serper_client import SerperSearchClient, initialize_serper_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HybridCrawler:
    """
    Hybrid crawler that combines ScrapingBee for direct URL crawling
    and Serper for search-based content discovery.
    """
    
    def __init__(
        self, 
        scrapingbee_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        use_cache: bool = True
    ):
        """
        Initialize the hybrid crawler with both ScrapingBee and Serper capabilities.
        
        Args:
            scrapingbee_api_key: ScrapingBee API key
            serper_api_key: Serper API key
            use_cache: Whether to use caching for both crawling and searching
        """
        # Initialize ScrapingBee client using proxy approach (proven to work)
        self.scrapingbee_client = ProxyScrapingBeeClient(
            api_key=scrapingbee_api_key, 
            use_cache=use_cache
        )
        
        # Also initialize the direct client as fallback if available
        self.direct_client = None
        if direct_client_available:
            try:
                self.direct_client = DirectScrapingBeeClient(
                    api_key=scrapingbee_api_key, 
                    use_cache=use_cache
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize direct ScrapingBee client: {e}")
        
        # Initialize Serper client
        self.serper_client = initialize_serper_client(api_key=serper_api_key)
        
        # Track initialization
        logger.info("✅ HybridCrawler initialized")
        logger.info(f"   - ScrapingBee client: {'✅ Ready' if self.scrapingbee_client.api_key else '❌ No API key'}")
        logger.info(f"   - Serper client: {'✅ Ready' if self.serper_client.api_key else '❌ No API key'}")
    
    def crawl_url(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Crawl a specific URL using ScrapingBee.
        
        Args:
            url: URL to crawl
            params: Additional parameters for ScrapingBee
            
        Returns:
            Dict with HTML content and metadata
        """
        logger.info(f"🕸️ Crawling URL with ScrapingBee: {url}")
        
        # Try with proxy client first (known to work)
        result = self.scrapingbee_client.crawl_url(url, params)
        
        # If proxy client fails and direct client is available, try as fallback
        if "error" in result and self.direct_client is not None:
            logger.warning(f"⚠️ Proxy client failed, trying direct client as fallback")
            result = self.direct_client.crawl_url(url, params)
            
        return result
    
    def search(self, query: str, num_results: int = 10) -> Dict:
        """
        Search for content using Serper.
        
        Args:
            query: Search query
            num_results: Number of search results to return
            
        Returns:
            Dict with search results
        """
        logger.info(f"🔍 Searching with Serper: {query}")
        return self.serper_client.search(query, num_results=num_results)
    
    def discover_and_crawl(
        self, 
        topic: str, 
        max_urls: int = 3,
        crawl_params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Discover URLs related to a topic and crawl them.
        
        This powerful method combines search and crawling to automatically:
        1. Search for URLs related to a specific topic
        2. Crawl each discovered URL to extract its content
        
        Args:
            topic: Topic to search for
            max_urls: Maximum number of URLs to crawl
            crawl_params: Parameters for the crawling process
            
        Returns:
            List of crawling results for each discovered URL
        """
        logger.info(f"🔍🕸️ Discovering and crawling content for topic: {topic}")
        
        # First, search for relevant URLs
        urls = self.serper_client.get_urls_for_topic(topic, num_results=max_urls)
        
        if not urls:
            logger.warning(f"⚠️ No URLs found for topic: {topic}")
            return []
        
        logger.info(f"✅ Found {len(urls)} URLs for topic: {topic}")
        
        # Crawl each discovered URL
        results = []
        for url in urls:
            try:
                logger.info(f"🕸️ Crawling discovered URL: {url}")
                result = self.crawl_url(url, params=crawl_params)
                
                # Add source metadata
                result["_discovered"] = {
                    "topic": topic,
                    "method": "discover_and_crawl"
                }
                
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Error crawling discovered URL {url}: {str(e)}")
                results.append({
                    "url": url,
                    "error": str(e),
                    "_discovered": {
                        "topic": topic,
                        "method": "discover_and_crawl"
                    }
                })
        
        return results

# Convenience function to initialize the hybrid crawler
def initialize_hybrid_crawler(
    scrapingbee_api_key: Optional[str] = None,
    serper_api_key: Optional[str] = None,
    use_cache: bool = True
) -> HybridCrawler:
    """
    Initialize a hybrid crawler instance with both ScrapingBee and Serper capabilities.
    
    Args:
        scrapingbee_api_key: ScrapingBee API key (defaults to env var)
        serper_api_key: Serper API key (defaults to env var)
        use_cache: Whether to use caching
        
    Returns:
        Configured HybridCrawler instance
    """
    return HybridCrawler(
        scrapingbee_api_key=scrapingbee_api_key,
        serper_api_key=serper_api_key,
        use_cache=use_cache
    )
