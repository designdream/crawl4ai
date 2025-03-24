#!/usr/bin/env python3
"""
Test script for rule-based extraction using direct ScrapingBee integration.
This bypasses the proxy issues we're seeing with the Crawl4AI backend.
"""
import os
import sys
import json
import time
import logging
import requests
import traceback
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

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

# Import the rule-based extraction module
sys.path.append('/Users/feliperecalde/Desktop/Apps/crawl4ai')
from crawl4ai.rule_based_extraction import RuleBasedExtractionStrategy, RegulationExtractionStrategy

def get_html_from_scrapingbee(url: str) -> Dict[str, Any]:
    """
    Get HTML content directly from ScrapingBee API.
    
    Args:
        url: The URL to scrape
        
    Returns:
        Dictionary with html content and status information
    """
    # Get API key from environment
    api_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not api_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable is not set")
        return {"success": False, "error": "Missing ScrapingBee API key", "html": ""}
    
    logger.info(f"🔑 Using ScrapingBee API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Format using the query parameters approach (standard way)
    scrapingbee_url = "https://app.scrapingbee.com/api/v1/"
    params = {
        "api_key": api_key,
        "url": url,
        "render_js": "true",
        "premium_proxy": "true"
    }
    
    logger.info(f"🔗 Making direct ScrapingBee request to: {url}")
    
    try:
        response = requests.get(scrapingbee_url, params=params)
        status_code = response.status_code
        
        logger.info(f"📊 Response status code: {status_code}")
        
        if status_code == 200:
            content = response.text
            logger.info(f"✅ Successfully fetched content ({len(content)} bytes)")
            return {"success": True, "html": content, "status_code": status_code}
        else:
            logger.error(f"❌ Request failed with status code {status_code}")
            logger.error(f"🧨 Error response: {response.text[:200]}")
            return {"success": False, "error": f"HTTP status {status_code}", "html": "", "status_code": status_code}
            
    except Exception as e:
        logger.error(f"❌ Exception during request: {str(e)}")
        return {"success": False, "error": str(e), "html": "", "status_code": 500}

def test_rule_based_extraction(url: str, state_name: str = "Test State"):
    """
    Test rule-based extraction with direct ScrapingBee integration.
    
    Args:
        url: URL to extract from
        state_name: Name of the state for context
        
    Returns:
        Dictionary with extraction results
    """
    logger.info(f"🚀 Starting direct rule-based extraction test on URL: {url}")
    start_time = time.time()
    
    try:
        # Fetch HTML content using ScrapingBee
        fetch_result = get_html_from_scrapingbee(url)
        
        if not fetch_result["success"]:
            logger.error(f"❌ Failed to fetch HTML: {fetch_result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": fetch_result.get("error", "Failed to fetch HTML"),
                "duration": time.time() - start_time
            }
        
        html = fetch_result["html"]
        logger.info(f"🔍 Fetched HTML content, now extracting with rule-based strategy")
        
        # Initialize the extraction strategy
        extraction_strategy = RegulationExtractionStrategy()
        
        # Extract data using the strategy
        logger.info(f"⚙️ Applying rule-based extraction...")
        extraction_start = time.time()
        extractions = extraction_strategy.extract(url, html)
        extraction_duration = time.time() - extraction_start
        
        logger.info(f"⏱️ Extraction completed in {extraction_duration:.2f}s")
        
        if not extractions:
            logger.warning(f"⚠️ No data extracted from the URL")
            return {
                "success": True,
                "extractions": [],
                "extractions_count": 0,
                "duration": time.time() - start_time
            }
        
        # Save results to a file
        result_file = f"{state_name.replace(' ', '_').lower()}_direct_rule_based_result.json"
        with open(result_file, "w") as f:
            json.dump(extractions, f, indent=2)
        
        logger.info(f"💾 Saved {len(extractions)} extractions to {result_file}")
        
        # Show sample of extractions
        if extractions:
            logger.info(f"\n📋 Extraction Results Sample:")
            for i, ext in enumerate(extractions[:2]):
                logger.info(f"\n📌 Extraction {i+1}:")
                if isinstance(ext, dict):
                    for key, value in ext.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"  {key}: {value[:100]}...")
                        else:
                            logger.info(f"  {key}: {value}")
                else:
                    logger.info(f"  {ext}")
        
        return {
            "success": True,
            "extractions": extractions,
            "extractions_count": len(extractions),
            "duration": time.time() - start_time,
            "result_file": result_file
        }
    
    except Exception as e:
        logger.error(f"❌ Exception during rule-based extraction: {str(e)}")
        logger.error(f"🧨 Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }

def main():
    """Main entry point for the script."""
    logger.info("🚀 Starting direct rule-based extraction test")
    
    if len(sys.argv) < 2:
        # Default test URL if none provided - use the Ohio nursing board that has CE requirements
        url = "https://nursing.ohio.gov/licensing-certification-ce/ce-for-lpns-rns-and-aprns/"
        state = "Ohio"
        logger.info(f"📝 No URL provided, using default test URL: {url}")
    else:
        url = sys.argv[1]
        state = sys.argv[2] if len(sys.argv) > 2 else "Test State"
    
    # Run the test
    result = test_rule_based_extraction(url, state)
    
    # Print summary
    logger.info("\n📋 --- Test Results Summary ---")
    if result.get("success"):
        ext_count = result.get("extractions_count", 0)
        duration = result.get("duration", 0)
        logger.info(f"✅ Rule-based extraction: Success ({ext_count} extractions in {duration:.2f}s)")
        if ext_count > 0:
            logger.info(f"📄 Results saved to: {result.get('result_file')}")
    else:
        error = result.get("error", "Unknown error")
        duration = result.get("duration", 0)
        logger.info(f"❌ Rule-based extraction: Failed - {error} ({duration:.2f}s)")
    
    return result

if __name__ == "__main__":
    main()
