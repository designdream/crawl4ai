"""
Serper Search Integration for Crawl4AI
Adapted from regBuddy's search_engine_client.py
"""
import os
import json
import logging
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal
from urllib.parse import urlparse, quote_plus
import threading
from collections import deque

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SerperSearchClient:
    """
    Client for Serper.dev search API - a cost-effective Google Search API
    Allows Crawl4AI to search for content when specific URLs aren't known
    
    Rate limits by tier:
    - Starter: 50 queries per second
    - Standard: 100 queries per second
    - Scale: 200 queries per second
    - Ultimate: 300 queries per second
    """
    
    # Rate limit tiers in queries per second
    RATE_LIMITS = {
        "starter": 50,
        "standard": 100,
        "scale": 200,
        "ultimate": 300
    }
    
    def __init__(self, api_key: str = None, cache_results: bool = True, 
                 tier: Literal["starter", "standard", "scale", "ultimate"] = "starter"):
        self.api_key = api_key or os.getenv('SERPER_API_KEY')
        self.cache_results = cache_results
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cache", "search")
        
        # Rate limiting settings
        self.tier = tier
        self.queries_per_second = self.RATE_LIMITS.get(tier, 50)  # Default to starter tier
        self.query_timestamps = deque(maxlen=self.queries_per_second)
        self.rate_limit_lock = threading.Lock()
        
        # Create cache directory
        if self.cache_results:
            os.makedirs(self.cache_dir, exist_ok=True)
            
        logger.info(f"Initialized SerperSearchClient with {tier} tier ({self.queries_per_second} QPS limit)")
    
    def _apply_rate_limiting(self):
        """
        Apply rate limiting based on the subscription tier.
        Ensures we don't exceed the queries per second limit.
        """
        with self.rate_limit_lock:
            now = time.time()
            
            # Remove timestamps older than 1 second
            while self.query_timestamps and now - self.query_timestamps[0] > 1.0:
                self.query_timestamps.popleft()
            
            # If we've reached the limit, sleep until we can make another request
            if len(self.query_timestamps) >= self.queries_per_second:
                sleep_time = 1.0 - (now - self.query_timestamps[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit approaching: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                    now = time.time()  # Update time after sleeping
            
            # Add current timestamp to the queue
            self.query_timestamps.append(now)
    
    def search(self, query: str, num_results: int = 10, search_type: str = "search", 
               retry_count: int = 3, retry_delay: float = 1.0) -> Dict:
        """
        Perform a search using Serper API with rate limiting and retry logic
        
        Args:
            query: Search query string
            num_results: Number of results to return
            search_type: Type of search (search, news, images, etc.)
            retry_count: Number of retries on rate limit or temporary errors
            retry_delay: Initial delay between retries (will use exponential backoff)
            
        Returns:
            Dict with search results
        """
        cache_file = None
        
        # Check cache if enabled
        if self.cache_results:
            cache_key = f"{query}_{num_results}_{search_type}".replace(" ", "_").lower()
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                        
                        # Check if cache is still fresh (less than 24 hours old)
                        cache_time = datetime.fromisoformat(cached_data.get('cache_timestamp', '2000-01-01T00:00:00'))
                        if (datetime.now() - cache_time).total_seconds() < 86400:  # 24 hours
                            logger.info(f"🔍 Using cached results for query: {query}")
                            return cached_data
                except Exception as e:
                    logger.error(f"Error reading cache: {e}")
        
        # If no valid cache, perform actual search
        if not self.api_key:
            logger.error("❌ SERPER_API_KEY not set")
            return {
                "error": "SERPER_API_KEY not set",
                "organic": []
            }
        
        logger.info(f"🔍 Searching for: {query}")
        
        # Apply rate limiting before making the request
        self._apply_rate_limiting()
        
        for attempt in range(retry_count):
            try:
                headers = {
                    'X-API-KEY': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'q': query,
                    'num': num_results
                }
                
                # Use different endpoints based on search type
                endpoint = 'search'
                if search_type == 'news':
                    endpoint = 'news'
                elif search_type == 'places':
                    endpoint = 'places'
                elif search_type == 'images':
                    endpoint = 'images'
                
                response = requests.post(
                    f'https://google.serper.dev/{endpoint}',
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                # Handle different response status codes
                if response.status_code == 200:
                    result = response.json()
                    
                    # Add cache timestamp
                    result['cache_timestamp'] = datetime.now().isoformat()
                    
                    # Cache result if enabled
                    if self.cache_results and cache_file:
                        try:
                            with open(cache_file, 'w') as f:
                                json.dump(result, f)
                        except Exception as e:
                            logger.error(f"Error caching search results: {e}")
                    
                    return result
                
                elif response.status_code == 429:  # Too Many Requests
                    # Rate limit exceeded
                    retry_wait = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limit exceeded. Retrying in {retry_wait} seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(retry_wait)
                    continue
                    
                elif response.status_code >= 500:  # Server errors
                    # Server error, retry
                    retry_wait = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Server error. Retrying in {retry_wait} seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(retry_wait)
                    continue
                    
                else:
                    logger.error(f"❌ Search API error: HTTP {response.status_code}: {response.text}")
                    return {
                        "error": f"API error: HTTP {response.status_code}",
                        "message": response.text,
                        "organic": []
                    }
                
            except requests.exceptions.RequestException as e:
                # Network error, retry
                if attempt < retry_count - 1:
                    retry_wait = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Network error. Retrying in {retry_wait} seconds (attempt {attempt+1}/{retry_count}): {str(e)}")
                    time.sleep(retry_wait)
                    continue
                else:
                    logger.error(f"❌ Network error after {retry_count} attempts: {str(e)}")
                    return {
                        "error": f"Network error: {str(e)}",
                        "organic": []
                    }
            except Exception as e:
                logger.error(f"❌ Search error: {str(e)}")
                return {
                    "error": str(e),
                    "organic": []
                }
    
    def get_urls_for_topic(self, topic: str, num_results: int = 5) -> List[str]:
        """
        Get a list of URLs related to a specific topic
        
        Args:
            topic: Topic to search for
            num_results: Maximum number of URLs to return
            
        Returns:
            List of URLs
        """
        results = self.search(topic, num_results=num_results)
        
        urls = []
        if 'organic' in results:
            for result in results['organic']:
                url = result.get('link')
                if url:
                    urls.append(url)
        
        return urls[:num_results]

# Initialize function for easy import
def initialize_serper_client(api_key: str = None, tier: str = "starter") -> SerperSearchClient:
    """
    Initialize a Serper search client instance
    
    Args:
        api_key: Serper API key (if None, reads from SERPER_API_KEY env var)
        tier: Subscription tier (starter, standard, scale, ultimate) - affects rate limiting
    
    Returns:
        SerperSearchClient instance configured with appropriate rate limits
    """
    if tier not in SerperSearchClient.RATE_LIMITS:
        logger.warning(f"Unknown Serper tier '{tier}', defaulting to 'starter'")
        tier = "starter"
        
    return SerperSearchClient(api_key=api_key, tier=tier)
