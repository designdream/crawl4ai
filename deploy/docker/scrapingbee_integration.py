#!/usr/bin/env python3
"""
ScrapingBee Integration for Crawl4AI

This script provides a comprehensive integration between ScrapingBee proxy services
and your authenticated Crawl4AI deployment for production use.
"""

import argparse
import json
import os
import requests
import time
from typing import List, Dict, Any, Optional

class Crawl4AIClient:
    """Client for interacting with the authenticated Crawl4AI API with ScrapingBee integration"""
    
    def __init__(
        self, 
        crawl4ai_token: str, 
        scrapingbee_api_key: str,
        crawl4ai_url: str = "https://s.dy.me",
        use_scrapingbee: bool = True
    ):
        """
        Initialize the Crawl4AI client with ScrapingBee integration
        
        Args:
            crawl4ai_token: Your Crawl4AI JWT token
            scrapingbee_api_key: Your ScrapingBee API key
            crawl4ai_url: Base URL of your Crawl4AI deployment
            use_scrapingbee: Whether to use ScrapingBee proxies (can be toggled)
        """
        self.crawl4ai_token = crawl4ai_token
        self.scrapingbee_api_key = scrapingbee_api_key
        self.crawl4ai_url = crawl4ai_url.rstrip('/')
        self.use_scrapingbee = use_scrapingbee
        
        # Set up authentication headers
        self.headers = {
            "Authorization": f"Bearer {self.crawl4ai_token}",
            "Content-Type": "application/json"
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the Crawl4AI API is up and running"""
        response = requests.get(
            f"{self.crawl4ai_url}/health",
            headers=self.headers
        )
        return response.json()
    
    def crawl(
        self, 
        urls: List[str], 
        browser_config: Optional[Dict[str, Any]] = None,
        crawler_config: Optional[Dict[str, Any]] = None,
        country_code: Optional[str] = None,
        premium_proxy: bool = True,
        javascript_rendering: bool = True,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Crawl the specified URLs using Crawl4AI with optional ScrapingBee proxies
        
        Args:
            urls: List of URLs to crawl
            browser_config: Additional browser configuration options
            crawler_config: Additional crawler configuration options
            country_code: Country code for geolocation (e.g., 'us', 'gb', 'fr')
            premium_proxy: Whether to use premium residential proxies
            javascript_rendering: Whether to enable JavaScript rendering
            timeout: Request timeout in seconds
        
        Returns:
            JSON response from the Crawl4AI API
        """
        # Start with default configs
        browser_config = browser_config or {}
        crawler_config = crawler_config or {}
        
        # Add ScrapingBee proxy if enabled
        if self.use_scrapingbee:
            # Build ScrapingBee proxy options
            proxy_options = "render_js=true" if javascript_rendering else "render_js=false"
            
            if country_code:
                proxy_options += f"&country={country_code}"
            
            if premium_proxy:
                proxy_options += "&premium=true"
            
            # Configure proxy
            browser_config["proxy"] = {
                "server": "http://proxy.scrapingbee.com:8886",
                "username": self.scrapingbee_api_key,
                "password": proxy_options
            }
        
        # Build the request payload
        payload = {
            "urls": urls,
            "browser_config": browser_config,
            "crawler_config": crawler_config
        }
        
        # Send the request
        response = requests.post(
            f"{self.crawl4ai_url}/crawl",
            headers=self.headers,
            json=payload,
            timeout=timeout
        )
        
        return response.json()
    
    def stream_crawl(
        self,
        urls: List[str], 
        browser_config: Optional[Dict[str, Any]] = None,
        crawler_config: Optional[Dict[str, Any]] = None,
        country_code: Optional[str] = None,
        premium_proxy: bool = True,
        javascript_rendering: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Stream crawl the specified URLs and wait for completion
        
        This is similar to crawl() but uses the streaming endpoint
        and collects all chunks until completion
        """
        # Start with default configs
        browser_config = browser_config or {}
        crawler_config = crawler_config or {}
        
        # Add ScrapingBee proxy if enabled
        if self.use_scrapingbee:
            # Build ScrapingBee proxy options
            proxy_options = "render_js=true" if javascript_rendering else "render_js=false"
            
            if country_code:
                proxy_options += f"&country={country_code}"
            
            if premium_proxy:
                proxy_options += "&premium=true"
            
            # Configure proxy
            browser_config["proxy"] = {
                "server": "http://proxy.scrapingbee.com:8886",
                "username": self.scrapingbee_api_key,
                "password": proxy_options
            }
        
        # Build the request payload
        payload = {
            "urls": urls,
            "browser_config": browser_config,
            "crawler_config": crawler_config
        }
        
        # Send the request
        response = requests.post(
            f"{self.crawl4ai_url}/crawl_stream",
            headers=self.headers,
            json=payload,
            stream=True,
            timeout=timeout
        )
        
        # Collect all chunks
        result = []
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                result.append(chunk)
                
                # If it's the final chunk, we're done
                if chunk.get("done", False):
                    break
        
        # Combine all chunks into a final result
        final_result = {}
        for chunk in result:
            final_result.update(chunk)
        
        return final_result
        
    def toggle_scrapingbee(self, enabled: bool = True) -> None:
        """Toggle the use of ScrapingBee proxies"""
        self.use_scrapingbee = enabled


def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(description='Crawl4AI with ScrapingBee Integration')
    parser.add_argument('--crawl4ai-token', type=str, 
                        default=os.environ.get('CRAWL4AI_TOKEN'),
                        help='Crawl4AI JWT token (or set CRAWL4AI_TOKEN env var)')
    parser.add_argument('--scrapingbee-key', type=str, 
                        default=os.environ.get('SCRAPINGBEE_KEY'),
                        help='ScrapingBee API key (or set SCRAPINGBEE_KEY env var)')
    parser.add_argument('--url', type=str, required=True, 
                        help='URL to crawl')
    parser.add_argument('--country', type=str, default=None,
                        help='Country code for proxy (e.g., us, gb, fr)')
    parser.add_argument('--disable-scrapingbee', action='store_true',
                        help='Disable ScrapingBee proxies')
    parser.add_argument('--disable-js', action='store_true',
                        help='Disable JavaScript rendering')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file for results (JSON format)')
    parser.add_argument('--stream', action='store_true',
                        help='Use streaming endpoint')
    
    args = parser.parse_args()
    
    # Check for required credentials
    if not args.crawl4ai_token:
        print("Error: Crawl4AI token is required (use --crawl4ai-token or set CRAWL4AI_TOKEN env var)")
        return 1
        
    if not args.scrapingbee_key and not args.disable_scrapingbee:
        print("Error: ScrapingBee API key is required (use --scrapingbee-key or set SCRAPINGBEE_KEY env var)")
        return 1
    
    # Initialize the client
    client = Crawl4AIClient(
        crawl4ai_token=args.crawl4ai_token,
        scrapingbee_api_key=args.scrapingbee_key or "",
        use_scrapingbee=not args.disable_scrapingbee
    )
    
    # Check if the API is available
    try:
        health = client.health_check()
        print(f"Crawl4AI API is {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"Error connecting to Crawl4AI: {str(e)}")
        return 1
    
    # Start time
    start_time = time.time()
    
    # Crawl the URL
    try:
        if args.stream:
            print(f"Streaming crawl for {args.url}...")
            result = client.stream_crawl(
                urls=[args.url],
                country_code=args.country,
                javascript_rendering=not args.disable_js
            )
        else:
            print(f"Crawling {args.url}...")
            result = client.crawl(
                urls=[args.url],
                country_code=args.country,
                javascript_rendering=not args.disable_js
            )
        
        # Show elapsed time
        elapsed = time.time() - start_time
        print(f"Crawl completed in {elapsed:.2f} seconds")
        
        # Output or display the result
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))
            
        return 0
    except Exception as e:
        print(f"Error during crawl: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
