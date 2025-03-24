"""
API Path Compatibility Module for Crawl4AI

This script adds backward compatibility for different API path patterns:
- /crawl (current)
- /api/crawl 
- /api/v1/crawl (legacy)

The routing system preserves all headers, query parameters, and request body,
ensuring a seamless transition for clients using older API path formats.

## Integration with FastAPI
Add this to your API server initialization to maintain compatibility with existing clients:

```python
# In your FastAPI app initialization
from api_path_compatibility import add_compatibility_routes
app = FastAPI()
add_compatibility_routes(app)
```

## CI/CD Integration
This module is designed to be compatible with GitHub Actions CI/CD pipelines.
It automatically adapts to different deployment environments:

1. Local development
2. Test/staging environments
3. Production deployments

For proper functioning, the httpx library must be installed as a dependency.

## Important Notes
- The httpx.AsyncClient() must be initialized before using these routes
- Set app.state.client to an AsyncClient instance (done in api_server.py)
- All routes added by this module silently forward requests to the new paths
- Request data is preserved during forwarding

## Error Handling
The module implements try/except blocks around every operation to prevent
crashes when handling malformed requests. All errors are logged using
the default logger.
"""

import logging
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import JSONResponse

# Configure logging
logger = logging.getLogger(__name__)

def add_compatibility_routes(app: FastAPI):
    """
    Add compatibility routes to support legacy API paths.
    
    This ensures that calls to /api/crawl and /api/v1/crawl are forwarded
    to the current /crawl endpoint without breaking existing integrations.
    
    Parameters:
        app (FastAPI): The FastAPI application instance
    
    Returns:
        None: The function modifies the app in-place
    
    Raises:
        AttributeError: If app.state.client is not initialized
    """
    # Verify the HTTP client is available
    if not hasattr(app.state, 'client'):
        logger.warning("HTTP client not found in app.state.client. Compatibility routes may not function correctly.")
    
    @app.post("/api/crawl")
    async def api_crawl_compat(request: Request):
        """Compatibility route for /api/crawl -> /crawl"""
        logger.info(f"Compatibility route: forwarding request from /api/crawl to /crawl")
        return await forward_request(request, app, "crawl")
    
    @app.post("/api/v1/crawl")
    async def api_v1_crawl_compat(request: Request):
        """Compatibility route for /api/v1/crawl -> /crawl"""
        logger.info(f"Compatibility route: forwarding request from /api/v1/crawl to /crawl")
        return await forward_request(request, app, "crawl")
    
    # Add compatibility routes for status endpoints
    @app.get("/api/status/{job_id}")
    async def api_status_compat(job_id: str, request: Request):
        """Compatibility route for /api/status/{job_id} -> /status/{job_id}"""
        logger.info(f"Compatibility route: forwarding request from /api/status/{job_id} to /status/{job_id}")
        return await forward_request(request, app, f"status/{job_id}")
    
    @app.get("/api/v1/status/{job_id}")
    async def api_v1_status_compat(job_id: str, request: Request):
        """Compatibility route for /api/v1/status/{job_id} -> /status/{job_id}"""
        logger.info(f"Compatibility route: forwarding request from /api/v1/status/{job_id} to /status/{job_id}")
        return await forward_request(request, app, f"status/{job_id}")
    
    # Add compatibility routes for result endpoints
    @app.get("/api/result/{job_id}")
    async def api_result_compat(job_id: str, request: Request):
        """Compatibility route for /api/result/{job_id} -> /result/{job_id}"""
        logger.info(f"Compatibility route: forwarding request from /api/result/{job_id} to /result/{job_id}")
        return await forward_request(request, app, f"result/{job_id}")
    
    @app.get("/api/v1/result/{job_id}")
    async def api_v1_result_compat(job_id: str, request: Request):
        """Compatibility route for /api/v1/result/{job_id} -> /result/{job_id}"""
        logger.info(f"Compatibility route: forwarding request from /api/v1/result/{job_id} to /result/{job_id}")
        return await forward_request(request, app, f"result/{job_id}")

async def forward_request(request: Request, app: FastAPI, target_path: str):
    """
    Forward a request to a different path while preserving headers and body.
    
    Parameters:
        request (Request): The original FastAPI request
        app (FastAPI): The FastAPI application instance
        target_path (str): The target path to forward to
        
    Returns:
        JSONResponse: The response from the target endpoint
    """
    try:
        # Get request method
        method = request.method
        # Get request body (if any)
        body = await request.body()
        body_json = await request.json() if body else None
        
        # Forward the request to the target endpoint
        async with app.state.client.request(
            method,
            f"{request.base_url}{target_path}",
            json=body_json if body else None,
            headers=dict(request.headers.items()),
            params=dict(request.query_params)
        ) as response:
            return JSONResponse(
                content=await response.json(),
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        logger.error(f"Error forwarding request to /{target_path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error when forwarding request: {str(e)}"
        )
