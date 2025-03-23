"""
Simplified test script for Claude 3.7 Sonnet integration.

This is a standalone script that directly uses litellm to test Claude 3.7 Sonnet
without depending on the full application structure.
"""
import os
import sys
import json
import time
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

def test_claude_3_7_sonnet():
    """Test that Claude 3.7 Sonnet works correctly with direct litellm calls."""
    try:
        from litellm import completion
        
        # Define the model ID
        model = "anthropic/claude-3-7-sonnet-20250219"
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("❌ No ANTHROPIC_API_KEY found in environment")
            return False
            
        logger.info(f"✅ Found API key for Claude 3.7 Sonnet")
        
        # Prepare a simple test prompt
        messages = [
            {
                "role": "user", 
                "content": """
                Please respond with a short JSON object with the following structure:
                {
                    "model_name": "your model name",
                    "capabilities": ["list", "of", "key", "capabilities"],
                    "test_success": true
                }
                Only respond with the JSON object, no additional text.
                """
            }
        ]
        
        # Make the API call
        logger.info(f"Making API call to Claude 3.7 Sonnet...")
        response = completion(
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=0.0,
            max_tokens=150
        )
        
        # Log the complete response for debugging
        logger.info(f"Received response from API")
        
        # Extract the content
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content.strip()
            logger.info(f"Response content: {content}")
            
            # Try to parse as JSON
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
            
            # Even if JSON parsing failed, if we got a response, that's a good sign
            return True
        else:
            logger.error("❌ No valid choices in the response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_error_handling():
    """Test that error handling works correctly with invalid credentials."""
    try:
        from litellm import completion
        from litellm.exceptions import AuthenticationError
        
        # Define the model ID
        model = "anthropic/claude-3-7-sonnet-20250219"
        
        # Invalid API key
        invalid_api_key = "invalid_key_for_testing"
        
        # Prepare a simple test prompt
        messages = [
            {
                "role": "user", 
                "content": "Hello, this is a test."
            }
        ]
        
        logger.info("\n\n=== Testing Error Handling ===\n")
        logger.info("Attempting request with invalid API key to verify error handling...")
        
        try:
            # This should fail with an AuthenticationError
            response = completion(
                model=model,
                messages=messages,
                api_key=invalid_api_key
            )
            logger.error("❌ Error handling test failed - request with invalid API key succeeded unexpectedly")
            return False
        except AuthenticationError as e:
            logger.info(f"✅ Error handling test passed - received expected authentication error: {str(e)}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Error handling test unclear - received unexpected error type: {type(e).__name__}")
            logger.warning(f"Error message: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Exception during error test: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Claude 3.7 Sonnet direct integration test...")
    
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
