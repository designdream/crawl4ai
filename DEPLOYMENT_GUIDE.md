# Crawl4AI Deployment Guide

This guide provides instructions for deploying Crawl4AI on Digital Ocean and Cloudflare.

## 1. Local Testing

Before deploying to the cloud, test the Docker container locally:

```bash
# Navigate to the repository
cd crawl4ai

# Build the Docker image
docker build -t crawl4ai .

# Run the container
docker run -p 8000:8000 --name crawl4ai-test crawl4ai
```

Test the API with:
```bash
curl http://localhost:8000/health
```

## 2. Digital Ocean Deployment

### Option 1: App Platform (Recommended)

1. Install the Digital Ocean CLI:
   ```bash
   brew install doctl
   doctl auth init
   ```

2. Configure app deployment:
   ```bash
   doctl apps create --spec digitalocean-app.yaml
   ```

3. Access your app at the URL provided by Digital Ocean.

### Option 2: Deploy to a Droplet

1. Create a Droplet with Docker pre-installed (Marketplace > Docker)

2. SSH into your Droplet:
   ```bash
   ssh root@your-droplet-ip
   ```

3. Clone the repository:
   ```bash
   git clone https://github.com/unclecode/crawl4ai.git
   cd crawl4ai
   ```

4. Set up environment variables:
   ```bash
   # Create .llm.env file for LLM API keys if needed
   nano .llm.env
   # Add your keys
   # OPENAI_API_KEY=your-key
   ```

5. Build and run the Docker container:
   ```bash
   docker build -t crawl4ai .
   docker run -d -p 80:8000 --env-file .llm.env --name crawl4ai crawl4ai
   ```

6. Your API will be available at http://your-droplet-ip

## 3. Cloudflare Deployment

### Using Cloudflare Workers

Cloudflare Workers is primarily for JavaScript applications, so we'll need to use Cloudflare Tunnel to route traffic to our Docker container.

1. Install cloudflared:
   ```bash
   # On macOS
   brew install cloudflare/cloudflare/cloudflared
   
   # On Linux
   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
   sudo dpkg -i cloudflared.deb
   ```

2. Authenticate with Cloudflare:
   ```bash
   cloudflared tunnel login
   ```

3. Create a tunnel:
   ```bash
   cloudflared tunnel create crawl4ai-tunnel
   ```

4. Configure the tunnel (create a config.yml file):
   ```yaml
   tunnel: <TUNNEL_ID>
   credentials-file: /path/to/.cloudflared/<TUNNEL_ID>.json
   
   ingress:
     - hostname: crawl4ai.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. Route DNS to your tunnel:
   ```bash
   cloudflared tunnel route dns <TUNNEL_ID> crawl4ai.yourdomain.com
   ```

6. Start your tunnel:
   ```bash
   cloudflared tunnel run <TUNNEL_ID>
   ```

Your Crawl4AI service will now be accessible at crawl4ai.yourdomain.com through Cloudflare's network.

## 4. Production Considerations

### Security
- Enable JWT authentication by setting `security.jwt_enabled` to `true` in config.yml
- Use HTTPS with proper certificates
- Implement rate limiting and firewall rules

### Scaling
- For high traffic, consider using a load balancer
- Set up monitoring using the /metrics endpoint
- Configure proper resource limits in your container

### Persistence
- For production, use Redis for caching instead of memory:
  - Change `storage_uri` in config.yml from "memory://" to "redis://redis:6379"
  - Add a Redis container or service
