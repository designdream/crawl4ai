"""
ScrapingBee Helper for Crawl4AI

This module provides helper functions for ScrapingBee integration with Crawl4AI,
ensuring proper configuration with SSL certificate handling and the correct proxy format.
"""
import os
import logging
import urllib3
from typing import Dict, Optional, Tuple, Any, Union

# Disable SSL warnings when using ScrapingBee
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def get_scrapingbee_proxy_config(api_key: Optional[str] = None, 
                                render_js: bool = True,
                                premium_proxy: bool = True,
                                additional_params: Dict[str, Any] = None) -> Dict[str, str]:
    """
    Generate the correct ScrapingBee proxy configuration for integration with Crawl4AI.
    
    Args:
        api_key: ScrapingBee API key (if None, will try to get from SCRAPINGBEE_KEY env var)
        render_js: Whether to enable JavaScript rendering
        premium_proxy: Whether to use premium proxies
        additional_params: Additional parameters to include in the proxy password
    
    Returns:
        Dictionary with the proper ScrapingBee proxy configuration
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("SCRAPINGBEE_KEY")
        if not api_key:
            logger.warning("⚠️ No ScrapingBee API key provided. ScrapingBee integration will not work.")
            return {}
    
    # Build password parameters string
    password_params = []
    if render_js:
        password_params.append("render_js=true")
    if premium_proxy:
        password_params.append("premium_proxy=true")
    
    # Add any additional parameters
    if additional_params:
        for key, value in additional_params.items():
            password_params.append(f"{key}={value}")
    
    # Join all parameters with &
    password = "&".join(password_params)
    
    # Build the proxy configuration
    proxy_config = {
        "server": "http://proxy.scrapingbee.com:8886",
        "username": api_key,
        "password": password
    }
    
    logger.info(f"✅ Generated ScrapingBee proxy configuration. Server: {proxy_config['server']}")
    return proxy_config

def get_scrapingbee_url_format(api_key: Optional[str] = None,
                              render_js: bool = True,
                              premium_proxy: bool = True,
                              additional_params: Dict[str, Any] = None) -> str:
    """
    Generate the ScrapingBee proxy URL in the format expected by some libraries.
    
    Args:
        api_key: ScrapingBee API key (if None, will try to get from SCRAPINGBEE_KEY env var)
        render_js: Whether to enable JavaScript rendering
        premium_proxy: Whether to use premium proxies
        additional_params: Additional parameters to include in the proxy URL
    
    Returns:
        ScrapingBee proxy URL string
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("SCRAPINGBEE_KEY")
        if not api_key:
            logger.warning("⚠️ No ScrapingBee API key provided. ScrapingBee integration will not work.")
            return ""
    
    # Build password parameters string
    password_params = []
    if render_js:
        password_params.append("render_js=true")
    if premium_proxy:
        password_params.append("premium_proxy=true")
    
    # Add any additional parameters
    if additional_params:
        for key, value in additional_params.items():
            password_params.append(f"{key}={value}")
    
    # Join all parameters with &
    password = "&".join(password_params)
    
    # Build the proxy URL
    proxy_url = f"http://{api_key}:{password}@proxy.scrapingbee.com:8886"
    
    logger.info(f"✅ Generated ScrapingBee proxy URL")
    return proxy_url

def verify_scrapingbee_integration() -> Tuple[bool, str]:
    """
    Verify that ScrapingBee integration is working correctly.
    
    Returns:
        Tuple of (is_working, message)
    """
    import requests
    
    api_key = os.getenv("SCRAPINGBEE_KEY")
    if not api_key:
        return False, "❌ No ScrapingBee API key found in environment. Set SCRAPINGBEE_KEY."
    
    test_url = "https://httpbin.org/ip"
    
    # First make a direct request
    try:
        direct_response = requests.get(test_url, timeout=10)
        direct_ip = direct_response.json().get("origin", "unknown")
    except Exception as e:
        return False, f"❌ Error making direct request: {str(e)}"
    
    # Now try with ScrapingBee
    proxy_url = get_scrapingbee_url_format(api_key)
    proxies = {
        "http": proxy_url,
        "https": proxy_url.replace("http://", "https://").replace(":8886", ":8887")
    }
    
    try:
        # Important: Disable SSL verification for ScrapingBee as per their documentation
        proxy_response = requests.get(
            test_url, 
            proxies=proxies,
            verify=False,  # Disable SSL verification
            timeout=30
        )
        proxy_ip = proxy_response.json().get("origin", "unknown")
        
        # Check if the IPs are different
        if direct_ip != proxy_ip:
            return True, f"✅ ScrapingBee is working! Direct IP: {direct_ip}, Proxy IP: {proxy_ip}"
        else:
            return False, f"❌ ScrapingBee may not be working. Same IP for direct and proxy: {direct_ip}"
    except Exception as e:
        return False, f"❌ Error with ScrapingBee proxy: {str(e)}"

def is_scrapingbee_enabled() -> bool:
    """Check if ScrapingBee integration is enabled by checking for API key"""
    return bool(os.getenv("SCRAPINGBEE_KEY"))

if __name__ == "__main__":
    # When run directly, verify the integration
    import sys
    logging.basicConfig(level=logging.INFO)
    
    success, message = verify_scrapingbee_integration()
    print(message)
    
    if success:
        print("\n✅ ScrapingBee integration is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ ScrapingBee integration is NOT working correctly.")
        sys.exit(1)
