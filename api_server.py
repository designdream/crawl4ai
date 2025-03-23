#!/usr/bin/env python3
"""
API Server for Crawl4AI that handles job submissions to the auto-scaling crawler.
"""
import os
import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
import redis
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Queue names (must match worker.py)
JOB_QUEUE = "crawl4ai:jobs"
RESULT_HASH = "crawl4ai:results"
PROCESSING_QUEUE = "crawl4ai:processing"
ERROR_HASH = "crawl4ai:errors"
STATS_KEY = "crawl4ai:stats"

# Create FastAPI app
app = FastAPI(
    title="Crawl4AI API",
    description="API for submitting crawl jobs to the auto-scaling Crawl4AI system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Pydantic models for request/response validation
class CrawlRequest(BaseModel):
    url: HttpUrl
    params: Optional[Dict[str, Any]] = {}
    priority: Optional[int] = 0
    callback_url: Optional[HttpUrl] = None

class CrawlResponse(BaseModel):
    job_id: str
    url: str
    status: str
    queue_position: Optional[int] = None
    submitted_at: float

class JobStatus(BaseModel):
    job_id: str
    status: str
    url: str
    submitted_at: float
    processing_started: Optional[float] = None
    completed_at: Optional[float] = None
    worker_id: Optional[str] = None
    error: Optional[str] = None
    result_available: bool

# Helper function to update stats
def update_stats(stat_name: str, increment: int = 1) -> None:
    """Update statistics in Redis"""
    try:
        redis_client.hincrby(STATS_KEY, stat_name, increment)
    except Exception as e:
        logger.error(f"Error updating stats: {e}")

# API routes
@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except redis.RedisError as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(e)}")

@app.post("/crawl", response_model=CrawlResponse)
async def submit_crawl_job(request: CrawlRequest):
    """Submit a URL to be crawled"""
    try:
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job data
        job_data = {
            "id": job_id,
            "url": str(request.url),
            "params": request.params,
            "priority": request.priority,
            "callback_url": str(request.callback_url) if request.callback_url else None,
            "submitted_at": time.time()
        }
        
        # Add to queue (right for normal, left for high priority)
        if request.priority > 0:
            redis_client.lpush(JOB_QUEUE, json.dumps(job_data))
        else:
            redis_client.rpush(JOB_QUEUE, json.dumps(job_data))
        
        # Get queue position
        queue_length = redis_client.llen(JOB_QUEUE)
        
        # Update stats
        update_stats("jobs_submitted")
        
        logger.info(f"Job submitted: {job_id} - {request.url}")
        
        return CrawlResponse(
            job_id=job_id,
            url=str(request.url),
            status="queued",
            queue_position=queue_length,
            submitted_at=job_data["submitted_at"]
        )
    
    except Exception as e:
        logger.error(f"Error submitting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a specific job"""
    try:
        # Check if job is in results
        result = redis_client.hget(RESULT_HASH, job_id)
        if result:
            return JobStatus(
                job_id=job_id,
                status="completed",
                url="",  # Would need to store this with the result
                submitted_at=0,  # Would need to store this with the result
                completed_at=time.time(),  # Approximate
                result_available=True
            )
        
        # Check if job is in processing
        processing = redis_client.hget(PROCESSING_QUEUE, job_id)
        if processing:
            proc_data = json.loads(processing)
            return JobStatus(
                job_id=job_id,
                status="processing",
                url="",  # Would need to store this with the result
                submitted_at=0,  # Would need to store this with the result
                processing_started=proc_data.get("started"),
                worker_id=proc_data.get("worker"),
                result_available=False
            )
        
        # Check if job is in errors
        error = redis_client.hget(ERROR_HASH, job_id)
        if error:
            error_data = json.loads(error)
            return JobStatus(
                job_id=job_id,
                status="error",
                url="",  # Would need to store this with the result
                submitted_at=0,  # Would need to store this with the result
                completed_at=error_data.get("time"),
                error=error_data.get("error"),
                result_available=False
            )
        
        # Check if job is in queue
        # Note: This is inefficient for large queues, would need a different approach
        queue = redis_client.lrange(JOB_QUEUE, 0, -1)
        for idx, job_data in enumerate(queue):
            job = json.loads(job_data)
            if job.get("id") == job_id:
                return JobStatus(
                    job_id=job_id,
                    status="queued",
                    url=job.get("url", ""),
                    submitted_at=job.get("submitted_at", 0),
                    queue_position=idx + 1,
                    result_available=False
                )
        
        # Job not found
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{job_id}")
async def get_job_result(job_id: str):
    """Get the result of a completed job"""
    try:
        # Check if job is in results
        result = redis_client.hget(RESULT_HASH, job_id)
        if result:
            return json.loads(result)
        
        # Check if job is in errors
        error = redis_client.hget(ERROR_HASH, job_id)
        if error:
            error_data = json.loads(error)
            raise HTTPException(
                status_code=400, 
                detail=f"Job failed with error: {error_data.get('error')}"
            )
        
        # Check if job is in processing
        processing = redis_client.hget(PROCESSING_QUEUE, job_id)
        if processing:
            raise HTTPException(status_code=202, detail=f"Job {job_id} is still processing")
        
        # Check if job is in queue
        queue = redis_client.lrange(JOB_QUEUE, 0, -1)
        for job_data in queue:
            job = json.loads(job_data)
            if job.get("id") == job_id:
                raise HTTPException(status_code=202, detail=f"Job {job_id} is queued")
        
        # Job not found
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting job result: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        # Get queue lengths
        queue_length = redis_client.llen(JOB_QUEUE)
        processing_count = redis_client.hlen(PROCESSING_QUEUE)
        results_count = redis_client.hlen(RESULT_HASH)
        errors_count = redis_client.hlen(ERROR_HASH)
        
        # Get accumulated stats
        stats = redis_client.hgetall(STATS_KEY) or {}
        
        # Combine stats
        return {
            "current": {
                "queued_jobs": queue_length,
                "processing_jobs": processing_count,
                "completed_jobs": results_count,
                "failed_jobs": errors_count
            },
            "accumulated": {
                k: int(v) for k, v in stats.items()
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch")
async def submit_batch(urls: List[HttpUrl], background_tasks: BackgroundTasks):
    """Submit a batch of URLs to be crawled"""
    try:
        job_ids = []
        
        for url in urls:
            # Generate a unique job ID
            job_id = str(uuid.uuid4())
            
            # Create job data
            job_data = {
                "id": job_id,
                "url": str(url),
                "params": {},
                "submitted_at": time.time()
            }
            
            # Add to queue
            redis_client.rpush(JOB_QUEUE, json.dumps(job_data))
            job_ids.append(job_id)
        
        # Update stats
        update_stats("jobs_submitted", len(urls))
        update_stats("batch_submissions")
        
        logger.info(f"Batch job submitted with {len(urls)} URLs")
        
        return {
            "status": "submitted",
            "count": len(urls),
            "job_ids": job_ids
        }
    
    except Exception as e:
        logger.error(f"Error submitting batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
