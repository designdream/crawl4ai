# Crawl4AI Token Management Guide

## Current Tokens

| User | Email | Created | Expires | Status |
|------|-------|---------|---------|--------|
| Felipe | f@dy.me | March 22, 2025 | April 21, 2025 | Active |
| Sean | | To be created | | Pending |

## How to Generate/Renew Tokens

1. SSH into the Digital Ocean server:
   ```bash
   ssh root@164.92.69.88
   ```

2. Generate a token using the command:
   ```bash
   docker exec -it crawl4ai-container python /app/generate_token.py --email user@example.com
   ```
   
   Replace `user@example.com` with the actual email.

3. For Sean's token:
   ```bash
   docker exec -it crawl4ai-container python /app/generate_token.py --email sean@example.com
   ```

4. Copy the token from the output and share it securely with the user.

5. Update the TOKEN_MANAGEMENT.md file with the new token details.

## Example Authentication Use

```python
import requests

# Authentication token (replace with actual token)
token = "eyJ0eXAiOiJKV1QiLCJhbGci..."

# Headers for authentication
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Make authenticated request
response = requests.get("https://s.dy.me/health", headers=headers)
print(response.json())
```

## ScrapingBee Integration

When integrating ScrapingBee with Crawl4AI, both will require authentication:

1. ScrapingBee API requests will need your ScrapingBee API key
2. Requests to Crawl4AI will need the JWT token

Example using both:

```python
import requests
import json

# Credentials
crawl4ai_token = "eyJ0eXAiOiJKV1QiLCJhbGci..."  # Your Crawl4AI JWT token
scrapingbee_api_key = "YOUR_SCRAPINGBEE_API_KEY"  # Your ScrapingBee API key

# Crawl4AI endpoint
url = "https://s.dy.me/crawl"

# Headers with Crawl4AI authentication
headers = {
    "Authorization": f"Bearer {crawl4ai_token}",
    "Content-Type": "application/json"
}

# Request data with ScrapingBee proxy configuration
data = {
    "urls": ["https://example.com"],
    "browser_config": {
        "headless": True,
        "proxy": {
            "server": "http://proxy.scrapingbee.com:8886",
            "username": scrapingbee_api_key,
            "password": "render_js=true"
        }
    }
}

# Send the authenticated request
response = requests.post(url, headers=headers, json=data)
result = response.json()
print(json.dumps(result, indent=2))
```

## Important Notes

- Tokens expire after 30 days by default
- Generate new tokens a few days before expiration
- Keep the SECRET_KEY in Dockerfile.secure secure
- Remember to update local applications when tokens are renewed
