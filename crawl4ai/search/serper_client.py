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
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, quote_plus

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
    """
    
    def __init__(self, api_key: str = None, cache_results: bool = True):
        self.api_key = api_key or os.getenv('SERPER_API_KEY')
        self.cache_results = cache_results
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "cache", "search")
        
        # Create cache directory
        if self.cache_results:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def search(self, query: str, num_results: int = 10, search_type: str = "search") -> Dict:
        """
        Perform a search using Serper API
        
        Args:
            query: Search query string
            num_results: Number of results to return
            search_type: Type of search (search, news, images, etc.)
            
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
            else:
                logger.error(f"❌ Search API error: HTTP {response.status_code}: {response.text}")
                return {
                    "error": f"API error: HTTP {response.status_code}",
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
def initialize_serper_client(api_key: str = None) -> SerperSearchClient:
    """Initialize a Serper search client instance"""
    return SerperSearchClient(api_key=api_key)
