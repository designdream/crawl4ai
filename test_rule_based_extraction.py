#!/usr/bin/env python3
"""
Test script for the Rule-Based Extraction strategy in Crawl4AI.

This script demonstrates how the rule-based extraction approach avoids hallucinations
by comparing it with LLM-based extraction methods on the same content.
"""

import os
import json
import argparse
from typing import Dict, Any, List
import time
import requests
from bs4 import BeautifulSoup

# Import Crawl4AI components
from crawl4ai.rule_based_extraction import RegulationExtractionStrategy
from crawl4ai.extraction_strategy import LLMExtractionStrategy, NoExtractionStrategy
from crawl4ai.types import LLMConfig
from crawl4ai.utils import sanitize_html


def load_env_variables():
    """Load necessary environment variables."""
    # Try to load from .env file if dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Check for necessary API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    
    return {
        "openai_key": openai_key
    }


def fetch_url(url):
    """Fetch HTML content from a URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return None


def compare_extractions(url, html_content):
    """Compare rule-based and LLM-based extractions for the same content."""
    # Initialize strategies
    rule_strategy = RegulationExtractionStrategy(verbose=True)
    
    env_vars = load_env_variables()
    
    llm_configs = []
    if env_vars["openai_key"]:
        llm_configs.append(
            ("OpenAI GPT-4o", LLMConfig(
                provider="openai/gpt-4o",
                api_token=env_vars["openai_key"],
                extra_args={"temperature": 0.1}
            ))
        )
    
    # Store results
    results = {
        "url": url,
        "extractions": {
            "rule_based": None
        }
    }
    
    print(f"\n\n{'='*80}")
    print(f"Testing extraction on URL: {url}")
    print(f"{'='*80}\n")
    
    # Extract with rule-based strategy
    print("Running Rule-Based Extraction...")
    start_time = time.time()
    rule_extractions = rule_strategy.extract(url, html_content)
    rule_time = time.time() - start_time
    
    results["extractions"]["rule_based"] = {
        "data": rule_extractions,
        "time": rule_time
    }
    
    # Extract with LLM strategies if available
    for name, llm_config in llm_configs:
        print(f"Running {name} Extraction...")
        
        # Create instruction for healthcare CE requirements
        instruction = """
        Extract healthcare continuing education requirements information.
        Focus on:
        1. Total CE hours required
        2. Renewal period
        3. Specialized topic requirements (e.g., ethics, pharmacology)
        4. Deadlines
        5. Exemptions or waivers
        """
        
        llm_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction=instruction,
            verbose=True
        )
        
        start_time = time.time()
        try:
            llm_extractions = llm_strategy.extract(url, html_content)
            llm_time = time.time() - start_time
            
            results["extractions"][name] = {
                "data": llm_extractions,
                "time": llm_time
            }
        except Exception as e:
            print(f"Error with {name} extraction: {e}")
            results["extractions"][name] = {
                "error": str(e)
            }
    
    return results


def print_comparison(results):
    """Print a human-readable comparison of extraction results."""
    print(f"\n\n{'='*80}")
    print(f"EXTRACTION COMPARISON FOR: {results['url']}")
    print(f"{'='*80}\n")
    
    # Print rule-based results
    print("\n--- RULE-BASED EXTRACTION ---")
    rule_data = results["extractions"]["rule_based"]["data"]
    rule_time = results["extractions"]["rule_based"]["time"]
    print(f"Time taken: {rule_time:.2f} seconds")
    
    if rule_data and len(rule_data) > 0:
        # Print structured data if available
        if "structured_data" in rule_data[0]:
            structured = rule_data[0]["structured_data"]
            print("\nStructured Regulation Data:")
            
            if structured["total_hours"]:
                print(f"• Total Hours: {structured['total_hours']['hours']} (confidence: {structured['total_hours']['confidence']:.2f})")
                print(f"  Context: {structured['total_hours']['context']}")
            
            if structured["renewal_period"]:
                print(f"• Renewal Period: {structured['renewal_period']['period']} (confidence: {structured['renewal_period']['confidence']:.2f})")
                print(f"  Context: {structured['renewal_period']['context']}")
            
            if structured["specialized_requirements"]:
                print("\n• Specialized Requirements:")
                for req in structured["specialized_requirements"]:
                    print(f"  - {req['hours']} hours in {req['topic']} (confidence: {req['confidence']:.2f})")
                    print(f"    Context: {req['context']}")
            
            if structured["deadlines"]:
                print("\n• Deadlines:")
                for deadline in structured["deadlines"]:
                    print(f"  - {deadline['deadline']} (confidence: {deadline['confidence']:.2f})")
                    print(f"    Context: {deadline['context']}")
            
            if structured["exemptions"]:
                print("\n• Exemptions:")
                for exemption in structured["exemptions"]:
                    print(f"  - {exemption['exemption']} (confidence: {exemption['confidence']:.2f})")
                    print(f"    Context: {exemption['context']}")
        else:
            # Print raw data
            print("\nRaw Extractions:")
            for item in rule_data:
                print(f"• Type: {item.get('type')}, Value: {item.get('value')}")
                print(f"  Confidence: {item.get('confidence', 0):.2f}")
                if "context" in item:
                    print(f"  Context: {item.get('context')}")
    else:
        print("No rule-based extractions found.")
    
    # Print LLM-based results
    for name in results["extractions"]:
        if name != "rule_based":
            print(f"\n\n--- {name.upper()} EXTRACTION ---")
            
            if "error" in results["extractions"][name]:
                print(f"Error: {results['extractions'][name]['error']}")
                continue
            
            llm_data = results["extractions"][name]["data"]
            llm_time = results["extractions"][name]["time"]
            print(f"Time taken: {llm_time:.2f} seconds")
            
            if llm_data and len(llm_data) > 0:
                print("\nExtractions:")
                for item in llm_data:
                    print(f"• {json.dumps(item, indent=2)}")
            else:
                print("No extractions found.")


def main():
    parser = argparse.ArgumentParser(description="Test rule-based vs. LLM extraction strategies")
    parser.add_argument("--url", help="URL to extract from")
    parser.add_argument("--html", help="Path to HTML file to extract from")
    parser.add_argument("--output", help="Path to save detailed JSON results")
    args = parser.parse_args()
    
    # Check for URL or HTML file
    html_content = None
    url = args.url
    
    if args.html:
        with open(args.html, 'r', encoding='utf-8') as f:
            html_content = f.read()
        url = url or "file://" + os.path.abspath(args.html)
    elif args.url:
        html_content = fetch_url(args.url)
    else:
        # Default test case if no input is provided
        url = "https://www.rn.ca.gov/licensees/ce-renewal.shtml"
        html_content = fetch_url(url)
    
    if not html_content:
        print("Error: Could not get HTML content.")
        return
    
    # Clean HTML
    html_content = sanitize_html(html_content)
    
    # Run comparison
    results = compare_extractions(url, html_content)
    
    # Print human-readable comparison
    print_comparison(results)
    
    # Save detailed results if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to {args.output}")


if __name__ == "__main__":
    main()
