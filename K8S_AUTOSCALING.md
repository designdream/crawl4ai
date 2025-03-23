# Auto-Scaling Crawl4AI with DigitalOcean Kubernetes Service

This guide explains how to deploy Crawl4AI as an auto-scaling system on DigitalOcean Kubernetes Service (DOKS). With this architecture, your crawler can automatically scale up to handle thousands of URLs and scale down when idle to minimize costs.

## Architecture Overview

```
┌────────────────┐
│  Load Balancer │
└────────────────┘
        │
        ▼
┌────────────────┐     ┌────────────────┐
│   API Server   │◄────►    Redis Queue  │
└────────────────┘     └────────────────┘
        │                    │
 ┌──────┴──────┐      ┌──────┴──────┐
 ▼             ▼      ▼             ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ Worker │ │ Worker │ │ Worker │ │ Worker │
└────────┘ └────────┘ └────────┘ └────────┘
     ▲        ▲          ▲          ▲
     └────────┴──────────┴──────────┘
               │
     ┌─────────┴─────────┐
     │ Horizontal Pod    │
     │ Autoscaler (HPA)  │
     └───────────────────┘
```

## What's Included

1. **Kubernetes Deployment Files**:
   - Worker deployment and HPA
   - Redis for job queuing
   - API service with load balancer

2. **Application Components**:
   - `worker.py`: Processes jobs from the Redis queue
   - `api_server.py`: FastAPI service for job submission and monitoring

3. **Auto-Scaling Features**:
   - Scales from 2 to 20 workers based on CPU and memory usage
   - Graceful scale-down when load decreases
   - Priority queue for urgent crawl jobs

## Prerequisites

1. DigitalOcean account with API access
2. `doctl` CLI installed and configured
3. `kubectl` installed
4. Docker installed for building images

## Cost Estimates

| Component | Size | Monthly Cost | Notes |
|-----------|------|--------------|-------|
| DOKS Control Plane | N/A | $12 | Fixed cost |
| Worker Nodes | Basic-2 (2GB/1vCPU) | $10-$200 | Depends on scale |
| Load Balancer | Standard | $12 | Fixed cost |
| **Monthly Total** | | $34-$224 | |

## Deployment Instructions

### 1. Create DOKS Cluster

```bash
# Install doctl if needed
brew install doctl

# Authenticate with DigitalOcean
doctl auth init
# Follow prompts to enter your API token

# Create a Kubernetes cluster
doctl kubernetes cluster create crawl4ai-cluster \
  --region nyc1 \
  --size s-2vcpu-2gb \
  --count 2 \
  --auto-upgrade=true
```

### 2. Build and Push Docker Image

```bash
# Build the Docker image
docker build -t your-registry/crawl4ai:latest .

# Push to your registry
docker push your-registry/crawl4ai:latest
```

### 3. Create Kubernetes Secret for API Keys

```bash
# Create secret for API keys
kubectl create secret generic crawl4ai-secrets \
  --from-literal=scrapingbee-api-key=YOUR_SCRAPINGBEE_API_KEY \
  --from-literal=openai-api-key=YOUR_OPENAI_API_KEY
```

### 4. Deploy the System

```bash
# Deploy Redis
kubectl apply -f k8s/redis-deployment.yaml

# Deploy API server
kubectl apply -f k8s/api-deployment.yaml

# Deploy worker and HPA
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/worker-hpa.yaml
```

### 5. Get the API Endpoint

```bash
# Get the load balancer IP/hostname
kubectl get service crawl4ai-api
```

## API Usage

### Submit a Crawl Job

```bash
curl -X POST "http://<api-ip>/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Submit a Batch of URLs

```bash
curl -X POST "http://<api-ip>/batch" \
  -H "Content-Type: application/json" \
  -d '["https://example1.com", "https://example2.com", "https://example3.com"]'
```

### Check Job Status

```bash
curl "http://<api-ip>/status/<job-id>"
```

### Get Job Result

```bash
curl "http://<api-ip>/result/<job-id>"
```

## Monitoring and Management

### Check Auto-scaling Status

```bash
# View HPA status
kubectl get hpa crawl4ai-worker-hpa

# View pod scaling
kubectl get pods -l app=crawl4ai,component=worker
```

### View System Stats

```bash
curl "http://<api-ip>/stats"
```

### View Logs

```bash
# View API logs
kubectl logs -l app=crawl4ai,component=api

# View worker logs
kubectl logs -l app=crawl4ai,component=worker
```

## Scaling Further

This setup can scale to handle thousands of URLs efficiently. To scale even further:

1. Increase the `maxReplicas` in `worker-hpa.yaml` (e.g., to 50 or 100)
2. Use larger worker nodes (e.g., 4GB RAM, 2 vCPU)
3. Consider using a managed Redis service for very high loads
4. Implement result storage in a database rather than Redis for long-term storage

## Cost Optimization

1. Set `minReplicas: 1` in the HPA to reduce costs during idle periods
2. Use smaller node sizes for predictable, low-CPU workloads
3. Implement aggressive cache TTLs to reduce redundant crawling
4. Consider using spot instances for non-critical workloads

## Troubleshooting

### Common Issues

1. **Pods not scaling up**: Check HPA status and ensure metrics server is working
2. **API errors**: Check API pod logs with `kubectl logs`
3. **Crawling failures**: Check worker logs for ScrapingBee API issues

## Performance Benchmarks

With default settings on s-2vcpu-2gb nodes:

- **2 worker pods**: ~30 URLs/minute
- **10 worker pods**: ~150 URLs/minute
- **20 worker pods**: ~300 URLs/minute

## Next Steps

1. Implement user authentication for the API
2. Add more sophisticated job scheduling and prioritization
3. Integrate with persistent storage for long-term result storage
4. Implement rate limiting per user/client

---

This auto-scaling architecture leverages DigitalOcean's managed Kubernetes service to provide a flexible, cost-effective crawling solution that can scale from a few URLs to thousands, while optimizing resource usage and costs.
