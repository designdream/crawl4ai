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

# Import our server-optimized clients
from crawl4ai.direct_scrapingbee import DirectScrapingBeeClient

# Import hybrid crawler if enabled
ENABLE_HYBRID_CRAWLER = os.getenv("ENABLE_HYBRID_CRAWLER", "false").lower() == "true"
if ENABLE_HYBRID_CRAWLER:
    try:
        from crawl4ai.search.hybrid_crawler import HybridCrawler, initialize_hybrid_crawler
        logger.info("✅ Hybrid crawler integration enabled")
    except ImportError as e:
        logger.warning(f"⚠️ Could not import hybrid crawler: {e}")
        ENABLE_HYBRID_CRAWLER = False

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
        
        # Create ScrapingBee client (always needed as primary crawler)
        self.client = DirectScrapingBeeClient()
        
        # Create hybrid crawler if enabled
        self.hybrid_crawler = None
        if ENABLE_HYBRID_CRAWLER:
            try:
                self.hybrid_crawler = initialize_hybrid_crawler()
                logger.info(f"✅ Hybrid crawler initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize hybrid crawler: {e}")
        
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
            search_query = job.get("search_query")
            params = job.get("params", {})
            
            # Validate job data
            if not job_id:
                logger.error(f"❌ Invalid job data (missing id): {job_data}")
                return
                
            if not url and not search_query:
                logger.error(f"❌ Invalid job data (missing url or search_query): {job_data}")
                return
            
            # Mark as processing
            self.redis.hset(
                PROCESSING_QUEUE, 
                job_id, 
                json.dumps({"worker": self.worker_id, "started": time.time()})
            )
            
            result = None
            
            # Determine job type and process accordingly
            if url:
                # Standard URL crawling job
                logger.info(f"🔄 Processing URL crawl job {job_id}: {url}")
                result = self.client.crawl_url(url, params)
            
            elif search_query and self.hybrid_crawler:
                # Search-based job - requires hybrid crawler
                logger.info(f"🔄 Processing search job {job_id}: {search_query}")
                
                # If max_results specified, use it, otherwise default to 3
                max_results = params.get("max_results", 3)
                
                if params.get("discover_and_crawl", True):
                    # Search + crawl discovered URLs
                    result = {
                        "search_query": search_query,
                        "discovered_content": self.hybrid_crawler.discover_and_crawl(
                            search_query, 
                            max_urls=max_results,
                            crawl_params=params.get("crawl_params", {})
                        )
                    }
                else:
                    # Search only, no crawling
                    result = {
                        "search_query": search_query,
                        "search_results": self.hybrid_crawler.search(
                            search_query, 
                            num_results=max_results
                        )
                    }
            else:
                # Cannot process search job without hybrid crawler
                if search_query:
                    error_msg = "Search job received but hybrid crawler not available"
                    logger.error(f"❌ {error_msg}")
                    result = {"error": error_msg}
                else:
                    error_msg = "Invalid job type - no URL or search query"
                    logger.error(f"❌ {error_msg}")
                    result = {"error": error_msg}
            
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
