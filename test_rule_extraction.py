#!/usr/bin/env python3
"""
Test script for enhanced rule-based extraction with improved error handling and colorful logging.
"""
import os
import sys
import json
import time
import logging
import traceback
from dotenv import load_dotenv
import importlib.util
from typing import Dict, List, Any, Optional

# Configure detailed logging with color support
import logging

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
console_handler.setFormatter(ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Ensure all loggers show emojis
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Import the Crawl4AIClient dynamically
sys.path.append('/Users/feliperecalde/Desktop/Apps/regBuddy')
spec = importlib.util.spec_from_file_location("oog_nurse_search", "/Users/feliperecalde/Desktop/Apps/regBuddy/oog-nurse-search.py")
oog_nurse_module = importlib.util.module_from_spec(spec)
sys.modules["oog_nurse_search"] = oog_nurse_module
spec.loader.exec_module(oog_nurse_module)
Crawl4AIClient = oog_nurse_module.Crawl4AIClient

def test_rule_based_extraction(url: str, state_name: str = "Test State"):
    """
    Test rule-based extraction on a single URL with detailed logging
    """
    logger.info(f"🚀 Starting rule-based extraction test on URL: {url}")
    
    # Initialize the client
    api_token = os.environ.get("CRAWL4AI_API_TOKEN")
    if not api_token:
        logger.error("❌ CRAWL4AI_API_TOKEN environment variable is not set")
        return {"error": "Missing API token"}
    
    # Check for ScrapingBee API key
    scrapingbee_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not scrapingbee_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable is not set")
        return {"error": "Missing ScrapingBee API key"}
    
    # Setup client
    base_url = os.environ.get("CRAWL4AI_BASE_URL", "http://164.90.252.123")
    logger.info(f"🔌 Connecting to Crawl4AI API at: {base_url}")
    
    start_time = time.time()
    
    try:
        client = Crawl4AIClient(base_url=base_url, api_token=api_token)
        logger.info(f"✅ Client initialized successfully")
        
        # Submit the crawl job
        logger.info(f"📤 Submitting rule-based extraction job for URL: {url}")
        response = client.crawl_url(
            url=url,
            extraction_strategy="rule_based",
            render_js=True,
            premium=True,
            verbose=True
        )
        
        logger.info(f"📬 Initial response: {json.dumps(response, indent=2)}")
        
        job_id = response.get("job_id")
        if not job_id:
            logger.error(f"❌ No job ID returned in response: {response}")
            return {
                "success": False,
                "error": "No job ID returned",
                "raw_response": response
            }
        
        logger.info(f"🆔 Job submitted with ID {job_id}")
        
        # Add a small delay before starting to poll to give the backend time to process
        initial_delay = 3
        logger.info(f"⏱️ Waiting {initial_delay} seconds before starting to poll...")
        time.sleep(initial_delay)
        
        # Poll until job completes
        attempts = 60  # 5 minutes total wait time
        interval = 5
        poll_result = None
        
        logger.info(f"⏳ Starting to poll job {job_id} (max {attempts} attempts, every {interval}s)")
        
        for attempt in range(attempts):
            logger.info(f"🔄 Polling attempt {attempt+1}/{attempts}")
            
            try:
                status_result = client.check_job_status(job_id, verbose=True)
                
                # Check for actual errors in the job status check
                if "error" in status_result and status_result["error"] and status_result["error"] != "None":
                    logger.error(f"❌ Error checking job status: {status_result['error']}")
                    break
                    
                job_status = status_result.get("status", "unknown")
                logger.info(f"📊 Current job status: {job_status}")
                
                if job_status == "completed":
                    logger.info(f"✅ Job {job_id} completed successfully")
                    poll_result = client.get_job_result(job_id, verbose=True)
                    poll_result["job_status"] = status_result
                    break
                    
                elif job_status in ("failed", "error"):
                    logger.error(f"❌ Job {job_id} failed: {status_result.get('error', 'Unknown error')}")
                    poll_result = status_result
                    break
                elif job_status in ("queued", "processing"):
                    # Still waiting, continue polling
                    logger.info(f"⏱️ Job is {job_status}, waiting {interval} seconds...")
                    time.sleep(interval)
                else:
                    logger.warning(f"⚠️ Unknown job status: {job_status}")
                    time.sleep(interval)
            except Exception as e:
                logger.error(f"❌ Exception during polling: {str(e)}")
                logger.error(f"🧨 Traceback: {traceback.format_exc()}")
                time.sleep(interval)  # Continue polling despite the error
        
        duration = time.time() - start_time
        
        # Check if we timed out or had a real error
        if poll_result is None:
            logger.warning(f"⏰ Polling timed out for job {job_id}. Last status: processing or queued")
            # Jobs may still be running, get the last status
            status_result = client.check_job_status(job_id, verbose=True)
            logger.info(f"📊 Latest job status: {status_result}")
            
            return {
                "success": False,
                "job_id": job_id,
                "error": "Job still processing - consider increasing the timeout",
                "status": status_result.get("status", "unknown"),
                "duration": duration,
                "raw_result": status_result
            }
        elif "error" in poll_result and poll_result["error"] and poll_result["error"] != "None":
            logger.error(f"❌ Job errored: {poll_result['error']}")
            return {
                "success": False,
                "job_id": job_id,
                "error": poll_result.get("error", "Unknown error"),
                "duration": duration,
                "raw_result": poll_result
            }
        else:
            extractions = poll_result.get("extractions", [])
            logger.info(f"✨ Job completed successfully with {len(extractions)} extractions in {duration:.2f}s")
            
            # Save detailed results to a file
            result_file = f"{state_name.replace(' ', '_').lower()}_rule_based_result.json"
            with open(result_file, "w") as f:
                json.dump(poll_result, f, indent=2)
            
            logger.info(f"💾 Saved detailed results to {result_file}")
            
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
                "job_id": job_id,
                "duration": duration,
                "extractions_count": len(extractions),
                "result_file": result_file
            }
    
    except Exception as e:
        logger.error(f"❌ Exception during test: {str(e)}")
        logger.error(f"🧨 Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }

def check_direct_access(url: str):
    """
    Test direct access to the ScrapingBee API to verify connectivity
    """
    logger.info(f"🔍 Testing direct ScrapingBee access for URL: {url}")
    
    scrapingbee_key = os.environ.get("SCRAPINGBEE_API_KEY")
    if not scrapingbee_key:
        logger.error("❌ SCRAPINGBEE_API_KEY environment variable is not set")
        return {"error": "Missing ScrapingBee API key"}
        
    # Try to directly access the ScrapingBee API
    try:
        import requests
        
        # Import direct ScrapingBee module
        sys.path.append('/Users/feliperecalde/Desktop/Apps/crawl4ai')
        from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient
        
        logger.info(f"🔌 Initializing direct ScrapingBee client")
        sb_client = DirectScrapingBeeClient(api_key=scrapingbee_key)
        
        logger.info(f"📤 Making direct request to URL: {url}")
        # Use the crawl_url method and then access the HTML
        result = sb_client.crawl_url(url, {"render_js": True})
        
        if result.get("html") and result.get("status_code", 0) == 200:
            html = result.get("html", "")
            status_code = result.get("status_code", 0)
            logger.info(f"✅ Direct ScrapingBee access successful (status {status_code}, {len(html)} bytes)")
            return {
                "success": True,
                "status_code": status_code,
                "html_length": len(html),
                "html_sample": html[:200] + "..." if len(html) > 200 else html
            }
        else:
            status_code = result.get("status_code", 0)
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ Direct ScrapingBee access failed with status {status_code}: {error_msg}")
            return {
                "success": False,
                "status_code": status_code,
                "error": f"HTTP status {status_code}: {error_msg}"
            }
    except Exception as e:
        logger.error(f"❌ Exception during direct ScrapingBee access: {str(e)}")
        logger.error(f"🧨 Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main entry point for the script."""
    logger.info("🚀 Starting enhanced rule-based extraction test")
    
    if len(sys.argv) < 2:
        # Default test URL if none provided - use the Ohio nursing board that has CE requirements
        url = "https://nursing.ohio.gov/licensing-certification-ce/ce-for-lpns-rns-and-aprns/"
        state = "Ohio"
        logger.info(f"📝 No URL provided, using default test URL: {url}")
    else:
        url = sys.argv[1]
        state = sys.argv[2] if len(sys.argv) > 2 else "Test State"
    
    # First check direct access
    direct_result = check_direct_access(url)
    logger.info(f"📊 Direct ScrapingBee access result: {'✅ Success' if direct_result.get('success') else '❌ Failed'}")
    
    # Then test the extraction API
    result = test_rule_based_extraction(url, state)
    
    # Print summary
    logger.info("\n📋 --- Test Results Summary ---")
    if result.get("success"):
        ext_count = result.get("extractions_count", 0)
        duration = result.get("duration", 0)
        logger.info(f"✅ Rule-based extraction: Success ({ext_count} extractions in {duration:.2f}s)")
        logger.info(f"📄 Results saved to: {result.get('result_file')}")
    else:
        error = result.get("error", "Unknown error")
        duration = result.get("duration", 0)
        logger.info(f"❌ Rule-based extraction: Failed - {error} ({duration:.2f}s)")
    
    return result

if __name__ == "__main__":
    main()
