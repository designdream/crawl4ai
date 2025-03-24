"""
ScrapingBee Helper - Server Optimized Version

This module provides optimized configurations for the ScrapingBee API
with a focus on maximizing remote processing and efficient resource usage
on server deployments (DigitalOcean).
"""
import os
import json
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

def get_scrapingbee_proxy_config(
    api_key: Optional[str] = None,
    additional_params: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Generate a proxy configuration for ScrapingBee.
    
    Args:
        api_key: ScrapingBee API key (defaults to env var)
        additional_params: Additional parameters to pass to ScrapingBee
        
    Returns:
        Dictionary with proxy configuration
    """
    # Load environment variables if needed
    load_dotenv(override=True)
    
    # Get API key from environment if not provided
    sb_api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY", "")
    
    if not sb_api_key:
        raise ValueError("ScrapingBee API key is required")
    
    # Build parameter string for proxy URL
    param_str = ""
    if additional_params:
        param_parts = []
        for key, value in additional_params.items():
            # Skip extract_rules as it's not supported in this format
            if key == 'extract_rules':
                continue
            param_parts.append(f"{key}={value}")
        
        if param_parts:
            param_str = "&".join(param_parts)
    
    # Format the proxy URL according to ScrapingBee's required format
    proxy_url = f"http://{sb_api_key}:{param_str}@proxy.scrapingbee.com:8886"
    
    # Return as a proxy configuration
    return {"proxy": proxy_url}

# Site-specific optimizations for ScrapingBee
# These configurations are optimized for server deployment
# Focus on reliability and maximizing remote processing
SITE_OPTIMIZATIONS = {
    # Default configurations
    'static': {
        'render_js': False,
        'premium_proxy': True,
        'timeout_ms': 10000,  # 10 seconds for server with good connectivity
        'block_resources': True,  # Still block resources to save bandwidth
        'block_ads': True,
        'wait_browser': None,
        'extract_rules': {  # Remote extraction of links
            'links': {
                'selector': 'a',
                'output': '@href'
            }
        },
        'extra_params': {
            'country_code': 'us',
        }
    },
    'js': {
        'render_js': True,
        'premium_proxy': True,
        'timeout_ms': 15000,  # Servers can wait longer than battery devices
        'block_resources': True,
        'block_ads': True,
        'wait_browser': 'domcontentloaded',  # Valid string value
        'extract_rules': {  # Remote extraction of links
            'links': {
                'selector': 'a',
                'output': '@href'
            }
        },
        'extra_params': {
            'country_code': 'us',
        }
    },
    # Site-specific configurations
    'cebroker': {
        'render_js': True,
        'premium_proxy': True,
        'timeout_ms': 20000,  # CE Broker needs extra time, can be longer on server
        'block_resources': False,  # May need all resources
        'block_ads': True,
        'wait_browser': 'networkidle0',  # Wait for network to be idle
        'extract_rules': {  # Remote extraction of links
            'links': {
                'selector': 'a',
                'output': '@href'
            }
        },
        'extra_params': {
            'country_code': 'us',
            'device': 'desktop',
            'stealth_proxy': 'true',  # Extra stealth for Cloudflare detection
        }
    },
    'ncsbn': {
        'render_js': True,
        'premium_proxy': True,
        'timeout_ms': 15000,
        'block_resources': True,
        'block_ads': True,
        'wait_browser': 'domcontentloaded',  # Valid string value
        'extract_rules': {  # Remote extraction of links
            'links': {
                'selector': 'a',
                'output': '@href'
            }
        },
        'extra_params': {
            'country_code': 'us',
            'device': 'desktop',
        }
    },
    'bon.texas': {
        'render_js': True,  # Texas BON appears to need JS
        'premium_proxy': True,
        'timeout_ms': 15000,
        'block_resources': True,
        'block_ads': True,
        'wait_browser': 'domcontentloaded',
        'extra_params': {
            'country_code': 'us',
        }
    },
}

def detect_site_type(url: str) -> str:
    """
    Determine whether a website is likely static or requires JavaScript rendering.
    Also identifies specific sites that have custom optimizations.
    
    Args:
        url: The URL to analyze
        
    Returns:
        str: Site type identifier ('js', 'static', or a specific site id)
    """
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain = parsed.netloc
    
    # Check for specific sites with custom configurations
    if 'cebroker.com' in domain:
        return 'cebroker'
    elif 'ncsbn.org' in domain:
        return 'ncsbn'
    elif 'bon.texas.gov' in domain:
        return 'bon.texas'
    
    # Known JS-heavy domains and platforms
    js_heavy_domains = [
        # Social media and complex web apps
        'facebook', 'twitter', 'linkedin', 'instagram',
        # CE and nursing platforms known to use JS heavily
        'nursys', 'nursingworld', 'ceapprentice',
        # State boards with modern JS interfaces
        'azbn.gov', 'doh.wa.gov',
    ]
    
    # Known static site indicators
    static_site_indicators = [
        # Government domains often have simpler, static sites
        '.gov', '.state.', 'health.ny', 'mbon.maryland',
        # Classic PHP sites
        '.php', 'wp-content',
        # Old-school state board sites
        'rn.ca.gov', 'maine.gov', 'dos.pa.gov'
    ]
    
    # First check for explicit JS frameworks in the URL
    js_framework_patterns = ['react', 'angular', 'vue', 'ember', 'backbone', 'spa']
    for pattern in js_framework_patterns:
        if pattern in url_lower:
            return 'js'
    
    # Check for JS-heavy domains
    for js_domain in js_heavy_domains:
        if js_domain in domain or js_domain in url_lower:
            return 'js'
    
    # Check for static site indicators
    for indicator in static_site_indicators:
        if indicator in domain or indicator in url_lower:
            return 'static'
    
    # Default to JS for unknown sites to ensure proper rendering
    # This is a conservative approach for regulatory sites which may have
    # important content loaded via JavaScript
    return 'js'


def get_optimized_scrapingbee_config(
    api_key: Optional[str] = None,
    render_js: bool = False,  # Default to False for speed
    premium_proxy: bool = True,
    timeout_ms: int = 12000,  # Default higher for server deployment
    block_resources: bool = True,
    block_ads: bool = True,
    wait_browser: Optional[str] = None,  # Must be one of: load, domcontentloaded, networkidle0, networkidle2
    site_type: str = "unknown",  # Used for site-specific optimizations
    extract_remotely: bool = True,  # Default to True for server - always use remote extraction
    additional_params: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Generate a server-optimized ScrapingBee proxy configuration.
    
    Args:
        api_key: ScrapingBee API key
        render_js: Enable JavaScript (only enable when needed)
        premium_proxy: Use premium proxies
        timeout_ms: Request timeout in milliseconds
        block_resources: Block loading of resources like CSS, images
        block_ads: Block advertisements
        wait_browser: Wait for browser to fully load resources
        site_type: Type of site for optimization
        extract_remotely: Use ScrapingBee's extract_rules to process links remotely
        additional_params: Any additional parameters
        
    Returns:
        Optimized proxy configuration dictionary
    """
    # Initialize params
    params = {}
    
    # Check for site-specific optimizations
    if site_type in SITE_OPTIMIZATIONS:
        # Get site-specific configuration
        site_config = SITE_OPTIMIZATIONS[site_type].copy()
        
        # Get extra params from the site config
        extra_params = site_config.pop('extra_params', {})
        if extra_params:
            params.update(extra_params)
            
        # Override function parameters with site-specific ones
        render_js = site_config.get('render_js', render_js)
        premium_proxy = site_config.get('premium_proxy', premium_proxy)
        timeout_ms = site_config.get('timeout_ms', timeout_ms)
        block_resources = site_config.get('block_resources', block_resources)
        block_ads = site_config.get('block_ads', block_ads)
        
        # Override wait_browser only if specified in site config and valid
        site_wait_browser = site_config.get('wait_browser')
        if site_wait_browser and site_wait_browser in ['load', 'domcontentloaded', 'networkidle0', 'networkidle2']:
            wait_browser = site_wait_browser

    # Set the parameters as strings for ScrapingBee format
    if render_js:
        params['render_js'] = 'true'
    if premium_proxy:
        params['premium'] = 'true'  # Note: this is 'premium' not 'premium_proxy' in the URL format
    if block_resources:
        params['block_resources'] = 'true'
    if block_ads:
        params['block_ads'] = 'true'
    # Handle wait_browser parameter correctly
    # Must be one of: load, domcontentloaded, networkidle0, networkidle2
    if wait_browser in ['load', 'domcontentloaded', 'networkidle0', 'networkidle2']:
        params['wait_browser'] = wait_browser
    
    # Convert timeout from ms to seconds for ScrapingBee format
    params['timeout'] = str(int(timeout_ms / 1000))
    
    # Add any additional parameters
    if additional_params:
        params.update(additional_params)
        
    # Get the configuration using the base helper function
    return get_scrapingbee_proxy_config(
        api_key=api_key,
        additional_params=params
    )
