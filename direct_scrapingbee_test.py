#!/usr/bin/env python3
"""
Simple script to directly test ScrapingBee API without going through Crawl4AI backend.
This helps diagnose connectivity issues and verify API functionality.
"""
import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Tuple

# Configure logging with colors
class ColorFormatter(logging.Formatter):
    """Formatter for adding colors to log messages."""
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[1;91m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, self.COLORS['RESET'])}{log_message}{self.COLORS['RESET']}"

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler with color formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

def direct_scrapingbee_request(url: str, render_js: bool = True, premium: bool = True) -> Tuple[str, int]:
    """
    Make a direct request to ScrapingBee API.
    
    Args:
        url: The URL to scrape
        render_js: Whether to render JavaScript
        premium: Whether to use premium proxies
        
    Returns:
        Tuple of (html_content, status_code)
    """
    # Get API key from environment
    api_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not api_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable is not set")
        return ("", 401)
    
    logger.info(f"🔑 Using ScrapingBee API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Format 1: Using the query parameters approach (standard way)
    scrapingbee_url = "https://app.scrapingbee.com/api/v1/"
    params = {
        "api_key": api_key,
        "url": url,
        "render_js": "true" if render_js else "false",
        "premium_proxy": "true" if premium else "false"
    }
    
    logger.info(f"🔗 Making direct ScrapingBee request to: {url}")
    logger.info(f"📋 With parameters: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(scrapingbee_url, params=params)
        status_code = response.status_code
        
        logger.info(f"📊 Response status code: {status_code}")
        
        if status_code == 200:
            content = response.text
            logger.info(f"✅ Successfully fetched content ({len(content)} bytes)")
            content_preview = content[:200] + "..." if len(content) > 200 else content
            logger.info(f"📄 Content preview: {content_preview}")
            return (content, status_code)
        else:
            logger.error(f"❌ Request failed with status code {status_code}")
            logger.error(f"🧨 Error response: {response.text[:500]}")
            return (response.text, status_code)
            
    except Exception as e:
        logger.error(f"❌ Exception during request: {str(e)}")
        return (str(e), 500)

def proxy_format_test(url: str):
    """
    Test the proxy format that's used in the Crawl4AI integration.
    
    Args:
        url: URL to test
    """
    api_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not api_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable is not set")
        return
    
    # Format 2: Using the proxy header approach
    proxy_url = f"http://{api_key}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
    
    logger.info(f"🧪 Testing proxy format: {proxy_url[:15]}...{proxy_url[-15:]}")
    
    try:
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        logger.info(f"🔗 Making request to {url} via proxy")
        response = requests.get(url, proxies=proxies, timeout=30)
        
        status_code = response.status_code
        logger.info(f"📊 Response status code: {status_code}")
        
        if status_code == 200:
            content = response.text
            logger.info(f"✅ Successfully fetched content via proxy ({len(content)} bytes)")
            content_preview = content[:200] + "..." if len(content) > 200 else content
            logger.info(f"📄 Content preview: {content_preview}")
        else:
            logger.error(f"❌ Proxy request failed with status code {status_code}")
            logger.error(f"🧨 Error response: {response.text[:500]}")
    
    except Exception as e:
        logger.error(f"❌ Exception during proxy request: {str(e)}")

def main():
    """Main entry point for the script."""
    logger.info("🚀 Starting direct ScrapingBee API test")
    
    if len(sys.argv) < 2:
        # Default test URL if none provided
        url = "https://nursing.ohio.gov/licensing-certification-ce/ce-for-lpns-rns-and-aprns/"
        logger.info(f"📝 No URL provided, using default test URL: {url}")
    else:
        url = sys.argv[1]
    
    # Test direct API access
    logger.info("\n=== 🧪 Testing Direct ScrapingBee API Access ===")
    content, status_code = direct_scrapingbee_request(url)
    
    # Test proxy format
    logger.info("\n=== 🧪 Testing ScrapingBee Proxy Format ===")
    proxy_format_test(url)
    
    return status_code == 200

if __name__ == "__main__":
    main()
