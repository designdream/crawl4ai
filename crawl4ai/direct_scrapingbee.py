"""
Direct ScrapingBee integration - Server Optimized Version

This module provides direct access to the ScrapingBee API, optimized for
server deployment on DigitalOcean. It focuses on efficient resource usage,
caching, and remote processing to maximize performance.
"""
import os
import time
import json
import logging
import requests
import hashlib
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Create cache directory if it doesn't exist
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# Cache settings
CACHE_ENABLED = True  # Set to False to disable caching
CACHE_TTL_HOURS = 24  # Cache time-to-live in hours

# Performance tracking
PERFORMANCE_STATS = {
    "cache_hits": 0,
    "cache_misses": 0,
    "remote_extraction_success": 0,
    "remote_extraction_failure": 0
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

class DirectScrapingBeeClient:
    """Client for directly accessing the ScrapingBee API on server deployments."""
    
    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True):
        """
        Initialize the Direct ScrapingBee client.
        
        Args:
            api_key: ScrapingBee API key (defaults to env var)
            use_cache: Whether to use caching
        """
        # Load environment variables
        load_dotenv(override=True)
        
        # Get API key
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY", "")
        if not self.api_key:
            logger.warning("⚠️ No ScrapingBee API key provided. DirectScrapingBeeClient will not work.")
            
        # Setup caching
        self.use_cache = use_cache and CACHE_ENABLED
        
        # Track initialization
        logger.info("✅ DirectScrapingBeeClient initialized")
        logger.info(f"   - Caching enabled: {self.use_cache}")
        
        # Base URL for ScrapingBee API
        self.base_url = "https://app.scrapingbee.com/api/v1/"
    
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
    
    def crawl_url(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Dict:
        """
        Crawl a URL using ScrapingBee.
        
        Args:
            url: The URL to crawl
            params: Additional parameters to pass to ScrapingBee
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with HTML content and metadata
        """
        from crawl4ai.scrapingbee_helper import get_optimized_scrapingbee_config, detect_site_type
        
        if not self.api_key:
            return {"error": "No ScrapingBee API key provided"}
            
        # Log the request
        logger.info(f"🐝 DIRECT SCRAPINGBEE REQUEST: {url}")
        
        # Detect site type for optimized config
        site_type = detect_site_type(url)
        logger.info(f"   - Site Type: {site_type}")
        
        # Default parameters
        extract_remotely = True  # Always try to extract remotely on server
        
        # Get optimized config for the site type
        sb_params = get_optimized_scrapingbee_config(
            api_key=self.api_key,
            site_type=site_type,
            extract_remotely=extract_remotely
        )
        
        # Override with any provided params
        if params:
            sb_params.update(params)
            
        # Generate cache key
        cache_key = get_cache_key(url, sb_params)
        
        # Check cache first
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            # Add metadata
            cached_response["_metadata"] = {
                "from_cache": True,
                "site_type": site_type,
                "remote_extraction": extract_remotely
            }
            duration = cached_response.get("_metadata", {}).get("duration", 0)
            logger.info(f"✅ SUCCESS for {url} in {duration:.2f}s")
            logger.info(f"   - Links extracted: {len(cached_response.get('links', []))}")
            logger.info(f"   - Remote extraction: {cached_response.get('_metadata', {}).get('remote_extraction', False)}")
            return cached_response
            
        # Cache miss
        PERFORMANCE_STATS["cache_misses"] += 1
        logger.info(f"🔍 Cache miss for {url} (hits: {PERFORMANCE_STATS['cache_hits']}, misses: {PERFORMANCE_STATS['cache_misses']})")
        
        # Prepare API URL
        api_url = f"{self.base_url}"
        
        # Handle retries
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Log the attempt
                retry_count += 1
                logger.info(f"🐝 Direct ScrapingBee request attempt {retry_count}/{max_retries}...")
                
                # Time the request
                start_time = time.time()
                
                # Send the request
                response = requests.get(
                    api_url,
                    params={
                        'url': url,
                        **sb_params
                    },
                    timeout=30
                )
                
                # Calculate duration
                duration = time.time() - start_time
                logger.info(f"⏱️ ScrapingBee response time: {duration:.2f}s")
                
                # Handle response
                if response.status_code == 200:
                    # Success
                    html_content = response.text
                    
                    # Initialize result
                    result = {
                        "html": html_content,
                        "status_code": response.status_code,
                        "url": url,
                        "links": [],
                        "_metadata": {
                            "duration": duration,
                            "site_type": site_type,
                            "remote_extraction": False
                        }
                    }
                    
                    # Flag to track if remote extraction was successful
                    remote_extracted = False
                    
                    try:
                        # Check if response has data from extract_rules
                        if 'extract_rules' in sb_params and extract_remotely:
                            # Try to parse the response as JSON
                            try:
                                json_response = response.json()
                                logger.info(f"  - Received JSON response with keys: {list(json_response.keys())}")
                                
                                # ScrapingBee may return extracted data in different formats
                                if 'extracted_data' in json_response and 'links' in json_response['extracted_data']:
                                    # Use the remotely extracted links
                                    href_list = json_response['extracted_data']['links']
                                    
                                    # Convert to our standard format and normalize URLs
                                    seen_urls = set()
                                    for href in href_list:
                                        if href and isinstance(href, str):
                                            # Skip invalid URLs
                                            if href.startswith(('javascript:', '#', 'tel:', 'mailto:')):
                                                continue
                                                
                                            # Normalize URL
                                            full_url = urljoin(url, href)
                                            # Clean the URL (remove fragments)
                                            clean_url = re.sub(r'#.*$', '', full_url)
                                            
                                            # Deduplicate
                                            if clean_url not in seen_urls:
                                                seen_urls.add(clean_url)
                                                result["links"].append({"url": clean_url})
                                    
                                    remote_extracted = True
                                    PERFORMANCE_STATS["remote_extraction_success"] += 1
                                    logger.info(f"✅ Used remote extraction for {url} - saved processing")
                                    logger.info(f"   - Extracted {len(result['links'])} links remotely")
                                
                            except Exception as json_parse_error:
                                logger.warning(f"JSON parsing failed: {json_parse_error}")
                                # Try alternative format: sometimes ScrapingBee returns differently
                                try:
                                    # Some versions of the API return a links array directly
                                    if hasattr(response, 'json') and callable(response.json):
                                        alternative_json = response.json()
                                        if isinstance(alternative_json, dict) and 'links' in alternative_json:
                                            href_list = alternative_json['links']
                                            if isinstance(href_list, list):
                                                seen_urls = set()
                                                for href in href_list:
                                                    if href and isinstance(href, str):
                                                        # Normalize URL
                                                        full_url = urljoin(url, href)
                                                        # Clean the URL (remove fragments)
                                                        clean_url = re.sub(r'#.*$', '', full_url)
                                                        
                                                        # Deduplicate
                                                        if clean_url not in seen_urls:
                                                            seen_urls.add(clean_url)
                                                            result["links"].append({"url": clean_url})
                                                
                                                remote_extracted = True
                                                PERFORMANCE_STATS["remote_extraction_success"] += 1
                                                logger.info(f"✅ Used alternative remote extraction for {url} - saved processing")
                                                logger.info(f"   - Extracted {len(result['links'])} links remotely")
                                except Exception as alt_parse_error:
                                    logger.warning(f"Alternative JSON parsing failed: {alt_parse_error}")
                    except Exception as e:
                        logger.warning(f"Remote extraction parsing failed: {e}")
                        PERFORMANCE_STATS["remote_extraction_failure"] += 1
                    
                    # Fall back to local extraction if remote extraction failed
                    if not remote_extracted and html_content:
                        try:
                            # Perform link extraction locally
                            from bs4 import BeautifulSoup
                            
                            # Try with lxml parser first (faster), fall back to html.parser
                            try:
                                soup = BeautifulSoup(html_content, 'lxml')
                            except Exception:
                                soup = BeautifulSoup(html_content, 'html.parser')
                                
                            # Extract all links
                            seen_urls = set()
                            for link in soup.find_all('a', href=True):
                                href = link.get('href')
                                
                                # Skip invalid URLs
                                if href.startswith(('javascript:', '#', 'tel:', 'mailto:')):
                                    continue
                                    
                                # Normalize URL
                                full_url = urljoin(url, href)
                                # Clean the URL (remove fragments)
                                clean_url = re.sub(r'#.*$', '', full_url)
                                
                                # Deduplicate
                                if clean_url not in seen_urls:
                                    seen_urls.add(clean_url)
                                    result["links"].append({"url": clean_url})
                                    
                            logger.info(f"   - Extracted {len(result['links'])} links locally")
                            
                        except Exception as extract_error:
                            logger.warning(f"Local link extraction failed: {extract_error}")
                    
                    # Update metadata
                    result["_metadata"]["remote_extraction"] = remote_extracted
                    
                    # Save to cache
                    self._save_to_cache(cache_key, result)
                    
                    # Log success
                    logger.info(f"✅ SUCCESS for {url} in {duration:.2f}s")
                    logger.info(f"   - Links extracted: {len(result['links'])}")
                    logger.info(f"   - Remote extraction: {remote_extracted}")
                    logger.info(f"   - Duration: {duration:.2f}s")
                    
                    return result
                else:
                    # Error
                    logger.error(f"❌ ScrapingBee request failed: HTTP {response.status_code}")
                    logger.error(f"   - Response: {response.text[:50]}...")
                    
                    # Implement exponential backoff
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        logger.info(f"⏳ Backing off for {wait_time}s before retry")
                        time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"❌ Error during ScrapingBee request: {e}")
                
                # Implement exponential backoff
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"⏳ Backing off for {wait_time}s before retry")
                    time.sleep(wait_time)
        
        # All retries failed
        logger.error(f"❌ Maximum retries reached")
        return {
            "error": "Maximum retries reached",
            "status_code": 500,
            "url": url,
            "_metadata": {
                "duration": time.time() - start_time
            }
        }
