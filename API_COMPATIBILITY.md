# API Path Compatibility and Enhanced Features Documentation

## Overview

This document describes the implementation of the API path compatibility layer and enhanced features in Crawl4AI. It covers backward compatibility for legacy API paths, Serper rate limiting, enhanced PDF processing, and integration with CI/CD pipelines.

## API Path Compatibility

### Implementation Details

We've added a compatibility layer that allows clients to use both new and legacy API paths:

- **Current Path**: `/crawl`
- **Legacy Paths**: 
  - `/api/crawl`
  - `/api/v1/crawl`

The compatibility layer forwards requests from legacy paths to the current implementation, preserving all headers, parameters, and the request body. This ensures a seamless transition for existing clients while allowing new clients to use the current API design.

### How It Works

1. When a request is made to a legacy path (e.g., `/api/v1/crawl`), the request is intercepted by the compatibility layer
2. All request data (headers, body, query params) is preserved
3. The request is forwarded to the corresponding current path (e.g., `/crawl`)
4. The response from the current endpoint is returned to the client

### CI/CD Integration

The compatibility layer is designed to work with GitHub Actions CI/CD pipelines:

1. We've added `httpx` as a dependency in both the main `requirements.txt` and Docker's `requirements.txt`
2. The compatibility module includes error handling and logging to ensure robust operation
3. The implementation safely handles initialization errors to prevent deployment failures

## Enhanced PDF Processing

The enhanced PDF processing functionality has been fully integrated into the API:

- **OCR Support**: Extract text from images within PDFs
- **Table Recognition**: Extract tabular data from PDF documents
- **Redis Caching**: Improve performance for frequently accessed PDFs

### Configuration

PDF processing is controlled through parameters in the API request:

```json
{
  "url": "https://example.com/document.pdf",
  "params": {
    "enable_pdf_processing": true,
    "enable_ocr": true,
    "extract_tables": true
  }
}
```

### Redis Caching

The PDF processing results are cached in Redis to improve performance. Configure Redis connection using:

```
REDIS_URL=redis://username:password@redis-host:6379/0
```

## ScrapingBee Integration

ScrapingBee is used for accessing PDF content that requires browser rendering or is behind anti-scraping measures.

### Proxy Configuration Format

The ScrapingBee proxy configuration must use this specific format:

```json
{
  "proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"
}
```

### Environment Variables

ScrapingBee integration requires the `SCRAPINGBEE_KEY` environment variable to be set. In production environments, this should be configured through GitHub Secrets and Kubernetes secrets.

## Serper Rate Limiting

The Serper.dev API is used for search operations and has rate limits based on subscription tiers:

- **Starter**: 50 queries per second
- **Standard**: 100 queries per second
- **Scale**: 200 queries per second
- **Ultimate**: 300 queries per second

### Configuration

Configure Serper API access using the following environment variables:

```
SERPER_API_KEY=your_serper_api_key
```

## Deployment Instructions

### GitHub CI/CD Integration

1. Ensure your GitHub repository has the following secrets configured:
   - `SERPER_API_KEY`
   - `SCRAPINGBEE_KEY` (value: AJTU2OHTQB3M8Z8RRQ0WRID8IU0XSZM6CXYVH4U9MSICE3OE1WWYLA70MDOTL184644GKIXI3A5HEPQ1)
   - `DIGITALOCEAN_ACCESS_TOKEN` (for container registry access)
   - `KUBE_CONFIG` (Kubernetes configuration for deployment)
   - Other deployment-specific secrets

2. The deployment process uses the GitHub Actions workflow in `.github/workflows/deploy-api.yml` which:
   - Builds a new container image from the Dockerfile at `deploy/docker/Dockerfile.secure`
   - Pushes the image to the DigitalOcean container registry
   - Updates the Kubernetes deployment with the new image
   - Applies the necessary environment variables and resource configurations
   - Runs compatibility tests to verify all API endpoints are working

### Manual Deployment

For manual deployment, update the Kubernetes configuration with the required environment variables:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crawl4ai-api
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: SERPER_API_KEY
          valueFrom:
            secretKeyRef:
              key: serper-api-key
              name: crawl4ai-secrets
        - name: SCRAPINGBEE_KEY
          valueFrom:
            secretKeyRef:
              key: scrapingbee-key
              name: crawl4ai-secrets
```

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure `SERPER_API_KEY` and `SCRAPINGBEE_KEY` are properly set in your environment
2. **Dependency Errors**: Make sure `httpx` is installed for API compatibility layer
3. **Image Mismatch**: If deployment fails, check that you're using the correct container image

### Diagnosing Problems

1. Check pod logs: `kubectl logs <pod-name>`
2. Verify environment variables: `kubectl exec -it <pod-name> -- env | grep -E 'SERPER|SCRAPING'`
3. Test API endpoints: `kubectl exec -it <pod-name> -- curl -s http://localhost:8000/health`

## Conclusion

This implementation ensures backward compatibility while enhancing the application with robust PDF processing capabilities and reliable API rate limiting. The changes are fully compatible with the GitHub CI/CD pipeline, with necessary environment variables configured through Kubernetes secrets.
