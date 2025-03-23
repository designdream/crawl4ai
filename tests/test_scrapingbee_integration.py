#!/usr/bin/env python3
"""
Test Script for ScrapingBee Integration

This script tests the ScrapingBee integration helper functions to verify they work correctly
before pushing the changes. It tests both the configuration generation and actual API usage.
"""

import os
import sys
import json
import logging
import requests
import unittest
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawl4ai.scrapingbee_helper import (
    get_scrapingbee_proxy_config,
    get_scrapingbee_url_format,
    verify_scrapingbee_integration,
    is_scrapingbee_enabled
)

class TestScrapingBeeIntegration(unittest.TestCase):
    """Test cases for ScrapingBee integration helper functions"""
    
    def setUp(self):
        """Set up the test environment"""
        # Save current environment value to restore later
        self.original_api_key = os.environ.get('SCRAPINGBEE_KEY', '')
        # Set test API key
        os.environ['SCRAPINGBEE_KEY'] = 'test_api_key'
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment
        if self.original_api_key:
            os.environ['SCRAPINGBEE_KEY'] = self.original_api_key
        else:
            os.environ.pop('SCRAPINGBEE_KEY', None)
    
    def test_get_scrapingbee_proxy_config(self):
        """Test generating the ScrapingBee proxy configuration"""
        # Test with default parameters
        config = get_scrapingbee_proxy_config()
        self.assertEqual(config['server'], 'http://proxy.scrapingbee.com:8886')
        self.assertEqual(config['username'], 'test_api_key')
        self.assertEqual(config['password'], 'render_js=true&premium_proxy=true')
        
        # Test with custom parameters
        config = get_scrapingbee_proxy_config(
            api_key='custom_key',
            render_js=False,
            premium_proxy=False,
            additional_params={'country': 'us', 'device': 'desktop'}
        )
        self.assertEqual(config['server'], 'http://proxy.scrapingbee.com:8886')
        self.assertEqual(config['username'], 'custom_key')
        self.assertEqual(config['password'], 'country=us&device=desktop')
    
    def test_get_scrapingbee_url_format(self):
        """Test generating the ScrapingBee URL format"""
        # Test with default parameters
        url = get_scrapingbee_url_format()
        expected_url = 'http://test_api_key:render_js=true&premium_proxy=true@proxy.scrapingbee.com:8886'
        self.assertEqual(url, expected_url)
        
        # Test with custom parameters
        url = get_scrapingbee_url_format(
            api_key='custom_key',
            render_js=False,
            premium_proxy=True,
            additional_params={'country': 'fr'}
        )
        expected_url = 'http://custom_key:premium_proxy=true&country=fr@proxy.scrapingbee.com:8886'
        self.assertEqual(url, expected_url)
    
    def test_is_scrapingbee_enabled(self):
        """Test checking if ScrapingBee is enabled"""
        # Should be True since we set the env var in setUp
        self.assertTrue(is_scrapingbee_enabled())
        
        # Test when disabled
        os.environ.pop('SCRAPINGBEE_KEY', None)
        self.assertFalse(is_scrapingbee_enabled())
    
    @patch('requests.get')
    def test_verify_scrapingbee_integration(self, mock_get):
        """Test verifying ScrapingBee integration with mocked responses"""
        # Mock direct request
        direct_mock = MagicMock()
        direct_mock.json.return_value = {'origin': '123.45.67.89'}
        
        # Mock proxy request - different IP to simulate success
        proxy_mock = MagicMock()
        proxy_mock.json.return_value = {'origin': '98.76.54.32'}
        
        # Setup the mock to return different responses
        mock_get.side_effect = [direct_mock, proxy_mock]
        
        # Test successful integration
        success, message = verify_scrapingbee_integration()
        self.assertTrue(success)
        self.assertIn('ScrapingBee is working', message)
        
        # Now test a failure case (same IP)
        direct_mock.json.return_value = {'origin': '123.45.67.89'}
        proxy_mock.json.return_value = {'origin': '123.45.67.89'}
        mock_get.side_effect = [direct_mock, proxy_mock]
        
        success, message = verify_scrapingbee_integration()
        self.assertFalse(success)
        self.assertIn('may not be working', message)
    
    @patch('requests.get')
    def test_verify_scrapingbee_integration_error(self, mock_get):
        """Test error handling in verify integration"""
        # Mock an exception
        mock_get.side_effect = Exception("Test error")
        
        success, message = verify_scrapingbee_integration()
        self.assertFalse(success)
        self.assertIn('Error', message)


def live_test(api_key=None):
    """Run a live test against the actual ScrapingBee API"""
    print("\n🔍 Running live ScrapingBee integration test")
    
    # Use command line arg or environment variable
    api_key = api_key or os.environ.get('SCRAPINGBEE_KEY')
    if not api_key:
        print("❌ No ScrapingBee API key provided. Skipping live test.")
        return False
    
    # Run the actual verification
    try:
        success, message = verify_scrapingbee_integration()
        print(message)
        return success
    except Exception as e:
        print(f"❌ Error during live test: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test ScrapingBee integration")
    parser.add_argument("--api-key", type=str, 
                        help="ScrapingBee API key for live testing")
    parser.add_argument("--live-test", action="store_true",
                        help="Run a live test against the actual ScrapingBee API")
    parser.add_argument("--unit-tests", action="store_true", default=True,
                        help="Run unit tests (default: True)")
    
    args = parser.parse_args()
    
    # Run unit tests
    if args.unit_tests:
        unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    # Run live test if requested
    if args.live_test:
        live_test(args.api_key)
