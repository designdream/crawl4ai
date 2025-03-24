# Crawl4AI Production Deployment Checklist

This document provides a comprehensive checklist for deploying the latest Crawl4AI version to production, with special attention to the Serper.dev integration and enhanced PDF processing features.

## Pre-Deployment

✅ All pre-deployment tests have passed:
- Enhanced PDF processing functionality
- Redis caching for PDFs
- ScrapingBee integration with proper proxy format
- Serper rate limiting implementation

## Environment Variables

Ensure these environment variables are set in your Kubernetes secrets:

- `SERPER_API_KEY`: For Serper.dev search API integration
- `SCRAPINGBEE_KEY`: For ScrapingBee proxy integration
- `REDIS_URL`: For PDF and search result caching

## Kubernetes Configuration

1. Update deployment manifests with:
   - Latest container image tag
   - Environment variables from secrets
   - Resource limits appropriate for PDF processing

2. Apply rate limiting configuration:
   ```yaml
   # Add to your ConfigMap or deployment environment variables
   SERPER_TIER: "standard"  # Change based on your subscription: starter, standard, scale, ultimate
   ```

3. Ensure ScrapingBee proxy configuration is in the correct format:
   ```
   {"proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"}
   ```

## Deployment Steps

1. **Update Kubernetes Secrets**
   ```bash
   kubectl create secret generic crawl4ai-secrets \
     --from-literal=SERPER_API_KEY=<your-serper-api-key> \
     --from-literal=SCRAPINGBEE_KEY=<your-scrapingbee-key> \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Apply ConfigMap Updates**
   ```bash
   kubectl apply -f k8s/configmap.yaml
   ```

3. **Deploy Updated Application**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

4. **Verify Deployment Status**
   ```bash
   kubectl rollout status deployment/crawl4ai
   ```

5. **Test the Deployed API**
   ```bash
   # Get the service URL
   export SERVICE_URL=$(kubectl get svc crawl4ai -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   
   # Test the health endpoint
   curl http://$SERVICE_URL/health
   
   # Test the Serper integration
   curl -X POST http://$SERVICE_URL/api/search \
     -H "Content-Type: application/json" \
     -d '{"query":"test query", "provider":"serper"}'
   ```

## Post-Deployment Verification

1. Monitor logs for any errors:
   ```bash
   kubectl logs -f deployment/crawl4ai
   ```

2. Watch for rate limit warnings in logs:
   ```bash
   kubectl logs -f deployment/crawl4ai | grep "rate limit"
   ```

3. Test PDF processing functionality:
   ```bash
   curl -X POST http://$SERVICE_URL/api/process \
     -H "Content-Type: application/json" \
     -d '{"url":"https://example.com/sample.pdf", "enable_ocr":true}'
   ```

## Rollback Plan

If issues are detected, execute the rollback:

```bash
# Rollback to the previous stable version
kubectl rollout undo deployment/crawl4ai

# Verify rollback
kubectl rollout status deployment/crawl4ai
```

## Important Notes

1. **Serper.dev Rate Limits**:
   - Starter Package: 50 queries per second
   - Standard Package: 100 queries per second 
   - Scale Package: 200 queries per second
   - Ultimate Package: 300 queries per second

2. **ScrapingBee Integration**:
   - The proxy format must be exactly: `{"proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"}`
   - Any deviation from this format will cause the integration to fail

3. **API Endpoints**:
   - All endpoints now use `/api/crawl` instead of the deprecated `/api/v1/crawl`
   - POST requests with JSON body are required instead of GET requests with query parameters

## Monitoring

After deployment, monitor these metrics:
- API response times
- Error rates
- Serper API usage (to stay within rate limits)
- PDF processing time and success rate
- Cache hit/miss ratio

## Support Contacts

If deployment issues occur, contact:
- DevOps Team: devops@yourcompany.com
- Backend Team: backend@yourcompany.com
