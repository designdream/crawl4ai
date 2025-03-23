"""
Test script for Claude 3.7 Sonnet integration.

This verifies that Claude 3.7 Sonnet is properly configured and can be used with
the application's perform_completion_with_backoff function.
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("claude_test")

# Load environment variables
load_dotenv()

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the required functions from the project
from crawl4ai.utils import perform_completion_with_backoff
from crawl4ai.config import PROVIDER_MODELS

def test_claude_3_7_sonnet():
    """Test that Claude 3.7 Sonnet is properly configured and working."""
    # Define the target model
    provider = "anthropic/claude-3-7-sonnet-20250219"
    
    # Check if the model is in our provider models
    logger.info(f"Checking if {provider} is in configured providers...")
    if provider in PROVIDER_MODELS:
        logger.info(f"✅ {provider} is configured in PROVIDER_MODELS")
    else:
        logger.error(f"❌ {provider} is NOT configured in PROVIDER_MODELS")
        return False
    
    # Get the API key
    api_token = PROVIDER_MODELS.get(provider)
    if not api_token:
        logger.error(f"❌ No API token found for {provider}. Make sure ANTHROPIC_API_KEY is set in your environment.")
        logger.info("Checking if ANTHROPIC_API_KEY environment variable is set...")
        if os.getenv("ANTHROPIC_API_KEY"):
            logger.info("✅ ANTHROPIC_API_KEY is set in environment")
        else:
            logger.error("❌ ANTHROPIC_API_KEY is not set in environment")
        return False
    
    logger.info(f"API token for {provider} is {'available' if api_token else 'not available'}")
    
    # Simple prompt for testing
    prompt = """
    Please respond with a short JSON object with the following structure:
    {
        "model_name": "your model name",
        "capabilities": ["list", "of", "key", "capabilities"],
        "test_success": true
    }
    Only respond with the JSON object, no additional text.
    """
    
    logger.info(f"Testing completion with {provider}...")
    try:
        # Configure additional parameters
        extra_args = {
            "extra_args": {
                "temperature": 0.0,  # Use deterministic output
                "max_tokens": 150,   # Limit the response size
            }
        }
        
        # Perform the completion
        response = perform_completion_with_backoff(
            provider=provider,
            prompt_with_variables=prompt,
            api_token=api_token,
            **extra_args
        )
        
        # Check if we got a successful response
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            logger.info(f"Response from Claude 3.7 Sonnet: {content}")
            
            # Try to parse the response as JSON
            try:
                json_response = json.loads(content)
                if json_response.get("test_success"):
                    logger.info("✅ Test passed! Claude 3.7 Sonnet is working correctly.")
                    logger.info(f"Model identified as: {json_response.get('model_name', 'unknown')}")
                    logger.info(f"Capabilities: {json_response.get('capabilities', [])}")
                    return True
                else:
                    logger.warning("⚠️ Response received but test_success flag not set to true.")
            except json.JSONDecodeError:
                logger.warning("⚠️ Couldn't parse response as JSON, but response was received.")
                logger.info("This might still indicate the model is working but not following instructions precisely.")
                return False
        
        # Check if we have an error
        if hasattr(response, 'debug_info') and response.debug_info:
            logger.error(f"❌ Error occurred: {response.debug_info.get('error_message')}")
            logger.error(f"Suggestion: {response.debug_info.get('suggestion')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during test: {str(e)}")
        return False
        
    return False

def test_error_handling():
    """Test that error handling works correctly with invalid credentials."""
    provider = "anthropic/claude-3-7-sonnet-20250219"
    
    logger.info("\n\n=== Testing Error Handling ===\n")
    logger.info("Attempting request with invalid API key to verify error handling...")
    
    # Simple prompt
    prompt = "Hello, this is a test."
    
    # Invalid API key
    invalid_api_key = "invalid_key_for_testing"
    
    try:
        # Perform the completion with invalid key
        response = perform_completion_with_backoff(
            provider=provider,
            prompt_with_variables=prompt,
            api_token=invalid_api_key
        )
        
        # We should get an error response object
        if hasattr(response, 'debug_info') and response.debug_info:
            logger.info("✅ Error handling test passed - received structured error response")
            logger.info(f"Error type: {response.debug_info.get('error_type')}")
            logger.info(f"Error message: {response.debug_info.get('error_message')}")
            return True
        else:
            logger.error("❌ Error handling test failed - did not receive error information")
            return False
            
    except Exception as e:
        logger.error(f"❌ Unexpected exception during error test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Claude 3.7 Sonnet integration test...")
    
    # Test with valid credentials
    success = test_claude_3_7_sonnet()
    
    # Test error handling
    error_test = test_error_handling()
    
    if success:
        logger.info("\n✅ Claude 3.7 Sonnet is properly configured and working!")
        sys.exit(0)
    else:
        if error_test:
            logger.warning("\n⚠️ Error handling works, but Claude 3.7 Sonnet test failed. Check your API key and model access.")
        else:
            logger.error("\n❌ Both tests failed. There may be issues with the integration code.")
        sys.exit(1)
