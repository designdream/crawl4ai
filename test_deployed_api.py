#!/usr/bin/env python3
"""
Script to test the deployed Crawl4AI API with kubernetes port-forwarding.
This script automates the process of port-forwarding to the API pod
and testing all the endpoints (both new and legacy paths).
"""
import os
import json
import time
import requests
import argparse
import subprocess
from typing import Dict, List, Tuple

def setup_port_forwarding() -> subprocess.Popen:
    """Set up kubectl port-forwarding to the API pod"""
    print("Setting up port forwarding to the API pod...")
    
    # Get the first running API pod
    result = subprocess.run(
        ["kubectl", "get", "pods", "-l", "app=crawl4ai-api", "-o", "jsonpath='{.items[0].metadata.name}'"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error getting API pod: {result.stderr}")
        exit(1)
    
    pod_name = result.stdout.strip().replace("'", "")
    if not pod_name:
        print("Error: No API pods found")
        exit(1)
    
    print(f"Found API pod: {pod_name}")
    
    # Start port-forwarding process
    process = subprocess.Popen(
        ["kubectl", "port-forward", pod_name, "8000:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for port-forwarding to be established
    print("Waiting for port-forwarding to be established...")
    time.sleep(3)
    
    return process

def test_endpoint(endpoint: str, test_url: str) -> Tuple[bool, Dict]:
    """Test an API endpoint with the provided test URL"""
    full_url = f"http://localhost:8000/{endpoint.lstrip('/')}"
    
    # Test payload for enhanced PDF processing and Serper integration
    payload = {
        "url": test_url,
        "params": {
            "enable_pdf_processing": True,
            "provider": "serper"
        }
    }
    
    print(f"\nTesting endpoint: {full_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(full_url, json=payload, timeout=10)
        status_code = response.status_code
        
        if status_code == 200:
            print(f"✅ Success (Status {status_code})")
            try:
                response_json = response.json()
                print(f"Response: {json.dumps(response_json, indent=2)[:200]}...")
                return True, response_json
            except json.JSONDecodeError:
                print(f"Warning: Response is not valid JSON: {response.text[:100]}...")
                return True, {"response_text": response.text[:100]}
        else:
            print(f"❌ Failed (Status {status_code})")
            print(f"Error: {response.text[:200]}")
            return False, {"error": response.text}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making request: {str(e)}")
        return False, {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Test the deployed Crawl4AI API")
    parser.add_argument("--test-url", default="https://example.com",
                      help="URL to use for testing the API (default: https://example.com)")
    parser.add_argument("--no-port-forward", action="store_true",
                      help="Skip port forwarding (if you already have it set up)")
    args = parser.parse_args()
    
    port_forward_process = None
    
    try:
        # Setup port forwarding if needed
        if not args.no_port_forward:
            port_forward_process = setup_port_forwarding()
        
        # Endpoints to test (both current and legacy paths)
        endpoints = [
            "crawl",       # Current path
            "api/crawl",   # Legacy path 1
            "api/v1/crawl" # Legacy path 2
        ]
        
        # Check API health
        try:
            health_response = requests.get("http://localhost:8000/health")
            print(f"\nAPI Health Check: {'✅ Healthy' if health_response.status_code == 200 else '❌ Unhealthy'}")
            print(f"Health Status: {health_response.text}")
        except requests.exceptions.RequestException as e:
            print(f"\nAPI Health Check: ❌ Failed - {str(e)}")
            print("Make sure port forwarding is working and the API is running")
            if not args.no_port_forward and port_forward_process:
                print("Port forwarding logs:")
                print(f"STDOUT: {port_forward_process.stdout.read() if port_forward_process.stdout else 'No output'}")
                print(f"STDERR: {port_forward_process.stderr.read() if port_forward_process.stderr else 'No output'}")
            return
        
        # Test all endpoints
        print("\n=== Testing API Endpoints ===")
        results = {}
        
        for endpoint in endpoints:
            results[endpoint] = test_endpoint(endpoint, args.test_url)
        
        # Print summary
        print("\n=== Test Summary ===")
        all_passed = True
        
        for endpoint, (passed, _) in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            all_passed = all_passed and passed
            print(f"/{endpoint.lstrip('/')}: {status}")
        
        print(f"\nOverall Result: {'✅ ALL ENDPOINTS PASSED' if all_passed else '❌ SOME ENDPOINTS FAILED'}")
        
        # Print recommendations if failures occurred
        if not all_passed:
            print("\nRecommendations for fixing failures:")
            print("1. Check that api_path_compatibility.py is properly integrated with api_server.py")
            print("2. Verify httpx is installed in the container")
            print("3. Check API pod logs: kubectl logs <pod-name>")
            print("4. Ensure environment variables are set correctly")
        else:
            print("\nAPI compatibility layer is working correctly!")
            print("Legacy paths are properly redirecting to the new path structure.")
    
    finally:
        # Clean up port forwarding
        if port_forward_process:
            print("\nCleaning up port forwarding...")
            port_forward_process.terminate()
            port_forward_process.wait()

if __name__ == "__main__":
    main()
