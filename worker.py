#!/usr/bin/env python3
"""
Worker script for Crawl4AI that processes jobs from a Redis queue.
Designed for auto-scaling Kubernetes deployment on DigitalOcean.
"""
import os
import time
import json
import logging
import redis
from typing import Dict, Any, Optional, List

# Import our server-optimized ScrapingBee client
from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient

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

# Worker configuration
WORKER_POLL_INTERVAL = float(os.getenv("WORKER_POLL_INTERVAL", "1.0"))
WORKER_JOB_TIMEOUT = int(os.getenv("WORKER_JOB_TIMEOUT", "300"))  # 5 minutes

# Queue names
JOB_QUEUE = "crawl4ai:jobs"
RESULT_HASH = "crawl4ai:results"
PROCESSING_QUEUE = "crawl4ai:processing"
ERROR_HASH = "crawl4ai:errors"

class Crawler4AIWorker:
    """Worker process that pulls jobs from Redis and processes them"""
    
    def __init__(self):
        """Initialize the worker"""
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        
        # Create ScrapingBee client
        self.client = DirectScrapingBeeClient()
        
        # Generate a unique worker ID
        import socket
        import uuid
        self.worker_id = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🚀 Worker {self.worker_id} initialized")
        logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        logger.info(f"✅ ScrapingBee client initialized")
    
    def process_job(self, job_data: str) -> None:
        """Process a single job from the queue"""
        try:
            # Parse job data
            job = json.loads(job_data)
            job_id = job.get("id")
            url = job.get("url")
            params = job.get("params", {})
            
            if not job_id or not url:
                logger.error(f"❌ Invalid job data: {job_data}")
                return
                
            logger.info(f"🔄 Processing job {job_id}: {url}")
            
            # Mark as processing
            self.redis.hset(
                PROCESSING_QUEUE, 
                job_id, 
                json.dumps({"worker": self.worker_id, "started": time.time()})
            )
            
            # Process with ScrapingBee
            result = self.client.crawl_url(url, params)
            
            # Store the result
            logger.info(f"✅ Job {job_id} completed successfully")
            self.redis.hset(RESULT_HASH, job_id, json.dumps(result))
            
            # Remove from processing
            self.redis.hdel(PROCESSING_QUEUE, job_id)
            
        except Exception as e:
            logger.error(f"❌ Error processing job: {str(e)}")
            if 'job_id' in locals():
                # Store the error
                self.redis.hset(
                    ERROR_HASH,
                    job_id,
                    json.dumps({"error": str(e), "time": time.time()})
                )
                # Remove from processing
                self.redis.hdel(PROCESSING_QUEUE, job_id)
    
    def run(self) -> None:
        """Run the worker process continuously"""
        logger.info("🏃 Starting worker process loop...")
        
        while True:
            try:
                # Get a job from the queue with timeout
                job = self.redis.blpop(JOB_QUEUE, timeout=1)
                
                if job:
                    _, job_data = job
                    self.process_job(job_data)
                
                # Short sleep to prevent CPU spinning
                time.sleep(WORKER_POLL_INTERVAL)
                
            except redis.RedisError as e:
                logger.error(f"❌ Redis error: {str(e)}")
                time.sleep(5)  # Wait a bit longer on Redis errors
                
            except KeyboardInterrupt:
                logger.info("👋 Worker shutting down...")
                break
            
            except Exception as e:
                logger.error(f"❌ Unexpected error: {str(e)}")
                time.sleep(1)

if __name__ == "__main__":
    worker = Crawler4AIWorker()
    worker.run()
