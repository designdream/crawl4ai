# Securing Crawl4AI with JWT Authentication

This guide explains how to secure your Crawl4AI deployment (both s.dy.me and direct IP access) using JWT-based authentication that's already built into the system.

## Overview

By enabling JWT authentication, all API endpoints on your Crawl4AI deployment will require a valid token for access. This ensures that only authorized users can access your web scraping service, protecting your resources and preventing unauthorized usage.

## Implementation Details

The security implementation:
- Uses JWT (JSON Web Tokens) for authentication
- Requires valid tokens in the `Authorization` header for all API requests
- Tokens have configurable expiration times
- Tokens can be restricted to specific email domains/addresses

## Deployment Steps

### 1. Generate a Secret Key

```bash
# Run this on your local machine
openssl rand -hex 32
```

Copy the output - this will be your SECRET_KEY.

### 2. Prepare Files for Deployment

The following files have been prepared in your local repository:
- `config.yml` - With security and JWT authentication enabled
- `generate_token.py` - Script to generate access tokens
- `Dockerfile.secure` - Docker configuration with security enabled

### 3. Upload Files to Your Server

```bash
# Run these commands on your local machine
scp deploy/docker/config.yml deploy/docker/generate_token.py deploy/docker/Dockerfile.secure root@164.92.69.88:~/
```

### 4. Build and Deploy on Server

SSH into your Digital Ocean server:

```bash
ssh root@164.92.69.88
```

Once connected, run:

```bash
# Build the secure image
# Be sure to replace the SECRET_KEY in the Dockerfile.secure file first!
sed -i 's/replace_with_a_secure_random_string/YOUR_GENERATED_SECRET_KEY/' Dockerfile.secure
docker build -t crawl4ai-secure:latest -f Dockerfile.secure .

# Stop the existing container
docker stop crawl4ai-container
docker rm crawl4ai-container

# Start the secured container
docker run -d -p 80:8000 --restart always --name crawl4ai-container crawl4ai-secure:latest
```

### 5. Generate Access Tokens

Once the secured container is running, generate access tokens for your users:

```bash
# Run on your server
docker exec -it crawl4ai-container python /app/generate_token.py --email your@email.com --expiry-days 30
```

The command will output a JWT token that can be used to authenticate with your API.

## Using Authentication with the API

To make authenticated requests to your secured Crawl4AI API, include the JWT token in the Authorization header:

```bash
# Example with curl
curl -H "Authorization: Bearer YOUR_TOKEN" https://s.dy.me/health

# Example for crawling with token
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"urls": ["https://example.com"]}' \
  https://s.dy.me/crawl
```

### Python Example

```python
import requests
import json

# Your Crawl4AI endpoint
crawl4ai_url = "https://s.dy.me/crawl"

# Your JWT token
token = "YOUR_JWT_TOKEN"

# Target website
target_url = "https://example.com"

# Prepare the request
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

payload = {
    "urls": [target_url],
    "browser_config": {
        "headless": True
    }
}

# Send the authenticated request
response = requests.post(
    crawl4ai_url,
    headers=headers,
    data=json.dumps(payload)
)

# Process the response
result = response.json()
print(result)
```

## Security Considerations

1. **Keep your SECRET_KEY secure** - Anyone with this key can generate valid tokens
2. **Set appropriate token expiration** - Shorter expiration times are more secure but require more frequent token renewal
3. **Restrict token distribution** - Only share tokens with trusted users
4. **Monitor API usage** - Regularly check logs to detect any unusual patterns

## Additional Configuration Options

You can further customize token generation:

```bash
# Generate a token valid for 7 days
docker exec -it crawl4ai-container python /app/generate_token.py --email your@email.com --expiry-days 7

# Use a different secret key for token generation
docker exec -it crawl4ai-container python /app/generate_token.py --email your@email.com --secret-key your-custom-secret
```

---

With this setup, your Crawl4AI deployment is now secured with JWT authentication, requiring valid tokens for all API access.
