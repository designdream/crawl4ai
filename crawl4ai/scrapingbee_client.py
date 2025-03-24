#!/usr/bin/env python3
"""
ScrapingBee Client for Crawl4AI
Enhanced client implementation that handles special cases and error conditions.
"""
import os
import time
import json
import logging
import urllib.parse
from typing import Dict, Any, List, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the DirectScrapingBeeClient
from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient

class ScrapingBeeClientError(Exception):
    """Base exception for ScrapingBee client errors"""
    pass

class SiteNotSupportedError(ScrapingBeeClientError):
    """Raised when a site requires special handling that is not configured"""
    pass

class EnhancedScrapingBeeClient:
    """
    Enhanced ScrapingBee client that adds additional features:
    1. Special handling for Google domains
    2. Improved error reporting
    3. Automatic retries with backoff
    4. Domain-specific parameter adjustment
    """
    
    # List of domains that require special handling
    SPECIAL_DOMAINS = {
        "google.com": {"custom_google": True, "premium": True},
        "google.co.uk": {"custom_google": True, "premium": True},
        "google.ca": {"custom_google": True, "premium": True},
        "google.fr": {"custom_google": True, "premium": True},
        "google.de": {"custom_google": True, "premium": True},
        "google.es": {"custom_google": True, "premium": True},
        "google.it": {"custom_google": True, "premium": True},
        "google.com.au": {"custom_google": True, "premium": True},
        "youtube.com": {"premium": True, "render_js": True},
        "linkedin.com": {"premium": True, "render_js": True},
        "facebook.com": {"premium": True, "block_resources": True},
        "twitter.com": {"premium": True, "render_js": True},
        "x.com": {"premium": True, "render_js": True}
    }
    
    # High-bandwidth sites that benefit from additional parameters
    HIGH_BANDWIDTH_DOMAINS = [
        "amazon.com", "walmart.com", "target.com", "ebay.com",
        "bestbuy.com", "homedepot.com", "lowes.com"
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl_hours: int = 24,
        max_retries: int = 3,
        timeout: int = 60,
        handle_special_domains: bool = True,
        warn_on_special_domains: bool = True
    ):
        """
        Initialize the enhanced ScrapingBee client.
        
        Args:
            api_key: ScrapingBee API key (defaults to env var)
            use_cache: Enable caching (recommended)
            cache_ttl_hours: Cache TTL in hours
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
            handle_special_domains: Auto-apply parameters for special domains
            warn_on_special_domains: Show warnings when special domains are detected
        """
        self.direct_client = DirectScrapingBeeClient(
            api_key=api_key,
            use_cache=use_cache
        )
        
        self.max_retries = max_retries
        self.timeout = timeout
        self.handle_special_domains = handle_special_domains
        self.warn_on_special_domains = warn_on_special_domains
        
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY", "")
        
        if not self.api_key:
            logger.warning("⚠️ No ScrapingBee API key provided. Client will not work.")
        else:
            logger.info("✅ Enhanced ScrapingBee client initialized")
            logger.info(f"   - API Key: {self.api_key[:5]}..." if self.api_key else "Not set")
            logger.info(f"   - Caching: {'Enabled' if use_cache else 'Disabled'}")
            logger.info(f"   - Special domains handling: {'Enabled' if handle_special_domains else 'Disabled'}")
    
    def _get_domain(self, url: str) -> str:
        """Extract the domain from a URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except Exception:
            return ""
    
    def _check_special_domain(self, url: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if URL is for a domain requiring special handling."""
        domain = self._get_domain(url)
        
        # Exact domain match
        for special_domain, params in self.SPECIAL_DOMAINS.items():
            if domain == special_domain or domain.endswith(f".{special_domain}"):
                return True, params
        
        # High bandwidth domains
        for hb_domain in self.HIGH_BANDWIDTH_DOMAINS:
            if domain == hb_domain or domain.endswith(f".{hb_domain}"):
                return True, {"block_resources": "font,image", "premium": True}
        
        return False, {}
    
    def crawl(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        force_special_handling: bool = False
    ) -> Dict[str, Any]:
        """
        Crawl a URL with ScrapingBee with enhanced error handling.
        
        Args:
            url: The URL to crawl
            params: Additional parameters to pass to ScrapingBee
            force_special_handling: Force special domain handling even if disabled globally
            
        Returns:
            Dict with HTML content and metadata
        """
        if not self.api_key:
            return {"error": "No ScrapingBee API key provided", "status": "error"}
        
        # Start with user-provided or empty params
        final_params = params.copy() if params else {}
        
        # Check for special domains
        is_special, special_params = self._check_special_domain(url)
        domain = self._get_domain(url)
        
        if is_special:
            # Special domain handling
            if self.handle_special_domains or force_special_handling:
                if self.warn_on_special_domains:
                    logger.warning(f"⚠️ Special domain detected: {domain}")
                    for key, value in special_params.items():
                        logger.info(f"   - Adding parameter: {key}={value}")
                
                # Merge special params with user params (user params take precedence)
                for key, value in special_params.items():
                    if key not in final_params:
                        final_params[key] = value
            else:
                if "google" in domain and self.warn_on_special_domains:
                    logger.warning(f"⚠️ Google domain detected but special handling is disabled: {url}")
                    logger.warning("   This may lead to blocked requests.")
        
        # Make the request with the direct client
        try:
            result = self.direct_client.crawl_url(url, final_params, self.max_retries)
            
            # Check for specific error conditions
            if result.get("error"):
                error_msg = result.get("error", "Unknown error")
                
                if "Google" in error_msg and "custom_google" not in final_params:
                    # Provide guidance for Google domains
                    logger.error(f"❌ Google domain access failed: {error_msg}")
                    logger.info("ℹ️ Google domains require 'custom_google=True' parameter")
                    logger.info("   This costs 20 credits per request with ScrapingBee")
                    result["google_domain_hint"] = True
                
                elif "404" in error_msg or result.get("status_code") == 404:
                    # 404 errors can be legitimate
                    logger.warning(f"⚠️ URL returned 404 Not Found: {url}")
                    result["status"] = "not_found"
                
                # Mark as error for consistent status field
                result["status"] = "error"
            else:
                # Mark as success for consistent status field
                result["status"] = "success"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error during ScrapingBee request: {e}")
            return {
                "error": str(e),
                "status": "error",
                "url": url,
                "timestamp": time.time()
            }
    
    def batch_crawl(
        self, 
        urls: List[str], 
        params: Optional[Dict[str, Any]] = None,
        concurrency_limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs with controlled concurrency.
        
        Args:
            urls: List of URLs to crawl
            params: Additional parameters for all requests
            concurrency_limit: Maximum concurrent requests
            
        Returns:
            List of results for each URL
        """
        import asyncio
        
        # Define async crawl function
        async def crawl_one(url):
            # Use synchronous method for simplicity
            return self.crawl(url, params)
        
        # Create task batches to control concurrency
        async def batch_process():
            results = []
            for i in range(0, len(urls), concurrency_limit):
                batch = urls[i:i+concurrency_limit]
                batch_tasks = [crawl_one(url) for url in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Handle exceptions
                processed_results = []
                for url, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        processed_results.append({
                            "url": url,
                            "error": str(result),
                            "status": "error",
                            "timestamp": time.time()
                        })
                    else:
                        processed_results.append(result)
                
                results.extend(processed_results)
                
                # Short delay between batches
                await asyncio.sleep(0.5)
                
            return results
        
        # Run async tasks
        try:
            return asyncio.run(batch_process())
        except Exception as e:
            logger.error(f"❌ Batch crawl error: {e}")
            # Return empty results with errors for all URLs
            return [{
                "url": url,
                "error": str(e),
                "status": "error",
                "timestamp": time.time()
            } for url in urls]

# Example usage
def test_enhanced_client():
    """Test the enhanced ScrapingBee client."""
    # Create client
    client = EnhancedScrapingBeeClient()
    
    # Test URLs
    test_urls = [
        # Regular site
        "https://www.rn.ca.gov/",
        # JS-heavy site
        "https://www.ncsbn.org/",
        # Google domain (requires special handling)
        "https://www.google.com/search?q=nursing+boards",
        # Non-existent URL
        "https://s.dy.me/nonexistent"
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        result = client.crawl(url)
        
        if result.get("status") == "success":
            print(f"✅ Success: Got {len(result.get('html', ''))} bytes of HTML")
            print(f"  Links found: {len(result.get('links', []))}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    # Test batch crawling
    print("\nTesting batch crawl...")
    batch_results = client.batch_crawl(test_urls[:2])  # Just the first two URLs
    print(f"Batch results: {len(batch_results)} URLs processed")

if __name__ == "__main__":
    test_enhanced_client()
