#!/usr/bin/env python3
"""
Test script for verifying API path compatibility in Crawl4AI

This script tests both the current API path and legacy API paths
to ensure that the compatibility layer is working correctly.
"""
import os
import json
import argparse
import requests

# Default settings for testing
DEFAULT_API_URL = "http://localhost:8000"

def test_endpoint(api_url, path, print_response=False):
    """Test an API endpoint and print the result"""
    full_url = f"{api_url.rstrip('/')}/{path.lstrip('/')}"
    
    # Example request for testing PDF processing + ScrapingBee integration
    test_payload = {
        "url": "https://example.com/sample.pdf",
        "params": {
            "enable_pdf_processing": True,
            "enable_ocr": True,
            "extract_tables": True,
            "provider": "serper",
            "proxy": f"http://{os.environ.get('SCRAPINGBEE_KEY', 'YOUR_API_KEY')}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
        }
    }
    
    # Add bearer token if available
    headers = {
        "Content-Type": "application/json"
    }
    
    api_token = os.environ.get("CRAWL4AI_API_TOKEN")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    
    print(f"Testing endpoint: {full_url}")
    
    try:
        response = requests.post(full_url, json=test_payload, headers=headers)
        status = response.status_code
        
        print(f"Status: {status}")
        if print_response and status == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2))
        elif status != 200:
            print(f"Error: {response.text}")
        
        return status == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Crawl4AI API compatibility")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, 
                        help="API URL to test (default: http://localhost:8000)")
    parser.add_argument("--print-responses", action="store_true", 
                        help="Print API responses")
    args = parser.parse_args()
    
    # List of endpoints to test (current and legacy paths)
    endpoints = [
        "crawl",          # Current path
        "api/crawl",      # Legacy path 1
        "api/v1/crawl"    # Legacy path 2
    ]
    
    print("=== Testing API Path Compatibility ===\n")
    
    results = {}
    for endpoint in endpoints:
        results[endpoint] = test_endpoint(args.api_url, endpoint, args.print_responses)
        print()
    
    # Print summary
    print("=== Summary ===")
    all_passed = True
    for endpoint, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        all_passed = all_passed and passed
        print(f"/{endpoint.lstrip('/')}: {status}")
    
    print("\nOverall result:", "✅ PASSED" if all_passed else "❌ FAILED")
    
    if not all_passed:
        print("\nFAILURES DETECTED:")
        print("1. Make sure the API server is running")
        print("2. Check that the api_path_compatibility.py module is correctly integrated")
        print("3. Verify that httpx is installed (pip install httpx)")
        print("4. Run 'kubectl get pods' to ensure all pods are running")

if __name__ == "__main__":
    main()
