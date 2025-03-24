#!/usr/bin/env python3
"""
Direct ScrapingBee integration using the proxy format.

This module provides direct access to websites via ScrapingBee using the proxy format
that has been verified to work in previous implementations:
{"proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"}
"""
import os
import time
import json
import logging
import requests
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Create cache directory if it doesn't exist
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# Cache settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

# Performance tracking
PERFORMANCE_STATS = {
    "cache_hits": 0,
    "cache_misses": 0,
    "requests_success": 0,
    "requests_failure": 0
}

def get_cache_key(url: str, params: Dict) -> str:
    """Generate a unique cache key for a request based on URL and params."""
    # Extract domain for domain-specific caching
    domain = urlparse(url).netloc
    
    # Create a string with domain, URL and sorted params
    param_str = json.dumps(params, sort_keys=True)
    key_str = f"{domain}|{url}|{param_str}"
    
    # Hash the string to create a filename-safe key
    return hashlib.md5(key_str.encode()).hexdigest()

class ProxyScrapingBeeClient:
    """Client for accessing websites via ScrapingBee using the proxy format."""
    
    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True):
        """
        Initialize the ScrapingBee proxy client.
        
        Args:
            api_key: ScrapingBee API key (defaults to env var)
            use_cache: Whether to use caching
        """
        # Load environment variables
        load_dotenv(override=True)
        
        # Get API key, trying both environment variable names
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY") or os.getenv("SCRAPINGBEE_KEY", "")
        if not self.api_key:
            logger.warning("⚠️ No ScrapingBee API key provided. ProxyScrapingBeeClient will not work.")
            
        # Setup caching
        self.use_cache = use_cache and CACHE_ENABLED
        
        # Track initialization
        logger.info("✅ ProxyScrapingBeeClient initialized")
        logger.info(f"   - API Key: {'✅ Found' if self.api_key else '❌ Missing'}")
        logger.info(f"   - Caching enabled: {self.use_cache}")
        
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """
        Get a cached response if it exists and is not expired.
        
        Args:
            cache_key: The cache key to look up
            
        Returns:
            The cached response or None if no valid cache exists
        """
        if not self.use_cache:
            return None
            
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            # Read the cache file
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            timestamp = cache_data.get("timestamp", 0)
            expiry = timestamp + (CACHE_TTL_HOURS * 3600)
            
            if time.time() > expiry:
                # Cache expired
                return None
                
            # Cache hit
            PERFORMANCE_STATS["cache_hits"] += 1
            logger.info(f"✅ Cache hit for {cache_key} (hits: {PERFORMANCE_STATS['cache_hits']}, misses: {PERFORMANCE_STATS['cache_misses']})")
            return cache_data.get("data")
                
        except Exception as e:
            logger.warning(f"⚠️ Error reading cache: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """
        Save a response to the cache.
        
        Args:
            cache_key: The cache key to save under
            data: The data to cache
        """
        if not self.use_cache:
            return
            
        try:
            cache_file = CACHE_DIR / f"{cache_key}.json"
            
            # Prepare cache data with timestamp
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            
            # Write to cache file
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            logger.warning(f"⚠️ Error writing to cache: {e}")
    
    def create_proxy_config(self, params: Optional[Dict] = None) -> Dict:
        """
        Create a proxy configuration for ScrapingBee using the format that works.
        
        Args:
            params: Additional parameters to pass to ScrapingBee
            
        Returns:
            Dict with proxy configuration
        """
        if not self.api_key:
            raise ValueError("ScrapingBee API key is required")
            
        # Default parameters
        default_params = "render_js=true&premium=true"
        
        # Add additional parameters if provided
        if params:
            param_parts = []
            for key, value in params.items():
                if isinstance(value, bool):
                    value = str(value).lower()
                param_parts.append(f"{key}={value}")
            
            if param_parts:
                default_params = "&".join(param_parts)
        
        # Create the proxy configuration using the format that works
        return {
            "proxy": f"http://{self.api_key}:{default_params}@proxy.scrapingbee.com:8886"
        }
    
    def crawl_url(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        Crawl a URL using ScrapingBee via proxy.
        
        Args:
            url: The URL to crawl
            params: Additional parameters to pass to ScrapingBee
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with HTML content and metadata
        """
        if not self.api_key:
            return {"error": "No ScrapingBee API key provided"}
            
        # Log the request
        logger.info(f"🕸️ PROXY SCRAPINGBEE REQUEST: {url}")
        
        # Default parameters if none provided
        if params is None:
            params = {
                "render_js": True,
                "premium": True
            }
            
        # Generate cache key
        cache_key = get_cache_key(url, params)
        
        # Check cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            # Add metadata
            cached_response["_metadata"] = {
                "from_cache": True,
                "proxy_mode": True
            }
            return cached_response
            
        # Cache miss
        PERFORMANCE_STATS["cache_misses"] += 1
        logger.info(f"🔍 Cache miss for {url} (hits: {PERFORMANCE_STATS['cache_hits']}, misses: {PERFORMANCE_STATS['cache_misses']})")
        
        # Create proxy configuration
        try:
            proxy_config = self.create_proxy_config(params)
        except ValueError as e:
            return {"error": str(e)}
            
        # Handle retries
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Log the attempt
                retry_count += 1
                logger.info(f"🕸️ Proxy ScrapingBee request attempt {retry_count}/{max_retries}...")
                
                # Time the request
                start_time = time.time()
                
                # Send the request via proxy
                response = requests.get(
                    url,
                    proxies=proxy_config,
                    timeout=30
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                logger.info(f"⏱️ ScrapingBee response time: {response_time:.2f}s")
                
                # Check if response is successful
                if response.status_code == 200:
                    # Extract content
                    html_content = response.text
                    
                    # Process response
                    result = {
                        "url": url,
                        "html": html_content,
                        "_metadata": {
                            "duration": response_time,
                            "status_code": response.status_code,
                            "proxy_mode": True
                        }
                    }
                    
                    # Save to cache
                    self._save_to_cache(cache_key, result)
                    
                    # Log success
                    PERFORMANCE_STATS["requests_success"] += 1
                    logger.info(f"✅ ScrapingBee request successful: {url}")
                    
                    return result
                else:
                    # Log error
                    logger.error(f"❌ ScrapingBee request failed: HTTP {response.status_code}")
                    logger.error(f"   - Response: {response.text[:100]}...")
                    
                    # Back off before retrying
                    if retry_count < max_retries:
                        backoff_time = 2 ** (retry_count - 1)
                        logger.info(f"⏳ Backing off for {backoff_time}s before retry")
                        time.sleep(backoff_time)
                    
            except Exception as e:
                # Log error
                logger.error(f"❌ Exception during request: {str(e)}")
                
                # Back off before retrying
                if retry_count < max_retries:
                    backoff_time = 2 ** (retry_count - 1)
                    logger.info(f"⏳ Backing off for {backoff_time}s before retry")
                    time.sleep(backoff_time)
        
        # Maximum retries reached
        PERFORMANCE_STATS["requests_failure"] += 1
        logger.error("❌ Maximum retries reached")
        return {"error": "Maximum retries reached", "url": url}
