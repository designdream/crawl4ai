#!/usr/bin/env python3
"""
Direct test for ScrapingBee API using the exact format required.
Based on the previous successful implementation from our memory.
"""

import os
import requests
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scrapingbee_direct():
    """Test ScrapingBee API directly using the verified format from previous implementation"""
    # Load environment variables
    load_dotenv('.env', override=True)
    
    # Get API key
    api_key = os.environ.get('SCRAPINGBEE_KEY') or os.environ.get('SCRAPINGBEE_API_KEY')
    
    if not api_key:
        logger.error("❌ No ScrapingBee API key found in environment")
        return False
    
    logger.info(f"API Key found: {api_key[:5]}...{api_key[-5:]}")
    
    # Test URL
    test_url = "https://example.com"
    
    # Using the EXACT format from memory that is known to work:
    # {"proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"}
    proxy_config = {
        "proxy": f"http://{api_key}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
    }
    
    logger.info(f"Testing direct ScrapingBee request to: {test_url}")
    logger.info(f"Using proxy format: {json.dumps(proxy_config)}")
    
    # Direct request to the target URL using the proxy
    try:
        response = requests.get(
            test_url,
            proxies=proxy_config,
            timeout=30
        )
        
        # Check response
        if response.status_code == 200:
            logger.info(f"✅ SUCCESS: ScrapingBee request succeeded with status code {response.status_code}")
            if "Example Domain" in response.text:
                logger.info("✅ Content validation successful: Found 'Example Domain' in response")
                return True
            else:
                logger.error("❌ Content validation failed: 'Example Domain' not found in response")
                return False
        else:
            logger.error(f"❌ ScrapingBee request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text[:100]}...")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during request: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_scrapingbee_direct()
    exit(0 if success else 1)
