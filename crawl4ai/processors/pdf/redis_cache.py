"""
Redis-based caching for PDF processing results.
This module provides a distributed caching layer for PDF processing,
allowing for high-performance retrieval of previously processed PDFs.
"""

import json
import hashlib
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import asdict

import redis
from redis.asyncio import Redis

from .processor import PDFProcessResult
from .enhanced_processor import EnhancedPDFProcessorStrategy

logger = logging.getLogger(__name__)

class PDFRedisCache:
    """
    Redis-based caching layer for PDF processing results.
    Provides methods for storing and retrieving processed PDF data,
    with configurable TTL and compression options.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "pdf:",
        ttl_seconds: int = 86400 * 7,  # Cache for 1 week by default
        compression: bool = True,
        processor_strategy = None
    ):
        """
        Initialize the Redis cache.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for PDF cache entries
            ttl_seconds: Time-to-live for cache entries in seconds
            compression: Whether to compress data (not implemented yet)
            processor_strategy: Strategy to use for processing PDFs when not in cache
        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        self.compression = compression
        
        # Default to enhanced processor if none provided
        self.processor_strategy = processor_strategy or EnhancedPDFProcessorStrategy()
        
        # Sync client for non-async contexts
        self.redis_sync = redis.from_url(redis_url)
        
        # Async client will be initialized on demand
        self._redis_async = None
    
    async def get_redis_async(self) -> Redis:
        """Get or initialize the async Redis client."""
        if self._redis_async is None:
            self._redis_async = Redis.from_url(self.redis_url)
        return self._redis_async
    
    def generate_cache_key(self, url_or_path: str) -> str:
        """
        Generate a cache key from a URL or file path.
        
        Args:
            url_or_path: PDF URL or file path
            
        Returns:
            Cache key for the PDF
        """
        # Create a hash of the URL or path
        key_hash = hashlib.sha256(url_or_path.encode()).hexdigest()
        return f"{self.prefix}{key_hash}"
    
    def get_cached_pdf_sync(self, url_or_path: str) -> Optional[Dict]:
        """
        Retrieve a cached PDF processing result synchronously.
        
        Args:
            url_or_path: PDF URL or file path
            
        Returns:
            Cached PDF processing result or None if not found
        """
        cache_key = self.generate_cache_key(url_or_path)
        cached_data = self.redis_sync.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached PDF data for {url_or_path}")
                return None
        
        return None
    
    def set_cached_pdf_sync(self, url_or_path: str, result: Union[PDFProcessResult, Dict]) -> bool:
        """
        Store a PDF processing result in the cache synchronously.
        
        Args:
            url_or_path: PDF URL or file path
            result: PDF processing result to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self.generate_cache_key(url_or_path)
        
        # Convert to dict if it's a PDFProcessResult
        if isinstance(result, PDFProcessResult):
            result_dict = asdict(result)
        else:
            result_dict = result
        
        try:
            # Serialize the result to JSON
            json_data = json.dumps(result_dict, default=str)
            
            # Store in Redis with TTL
            self.redis_sync.setex(
                cache_key,
                self.ttl_seconds,
                json_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache PDF data for {url_or_path}: {str(e)}")
            return False
    
    async def get_cached_pdf(self, url_or_path: str) -> Optional[Dict]:
        """
        Retrieve a cached PDF processing result asynchronously.
        
        Args:
            url_or_path: PDF URL or file path
            
        Returns:
            Cached PDF processing result or None if not found
        """
        redis_client = await self.get_redis_async()
        cache_key = self.generate_cache_key(url_or_path)
        
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached PDF data for {url_or_path}")
                return None
        
        return None
    
    async def set_cached_pdf(self, url_or_path: str, result: Union[PDFProcessResult, Dict]) -> bool:
        """
        Store a PDF processing result in the cache asynchronously.
        
        Args:
            url_or_path: PDF URL or file path
            result: PDF processing result to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        redis_client = await self.get_redis_async()
        cache_key = self.generate_cache_key(url_or_path)
        
        # Convert to dict if it's a PDFProcessResult
        if isinstance(result, PDFProcessResult):
            result_dict = asdict(result)
        else:
            result_dict = result
        
        try:
            # Serialize the result to JSON
            json_data = json.dumps(result_dict, default=str)
            
            # Store in Redis with TTL
            await redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cache PDF data for {url_or_path}: {str(e)}")
            return False
    
    async def process_with_cache(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Process a PDF with caching.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDF processing result, either from cache or freshly processed
        """
        path_str = str(pdf_path)
        
        # Try to get from cache first
        cached_result = await self.get_cached_pdf(path_str)
        if cached_result:
            logger.info(f"Cache hit for PDF: {path_str}")
            return cached_result
        
        # Not in cache, process the PDF
        logger.info(f"Cache miss for PDF: {path_str}, processing...")
        
        # Ensure path is a Path object
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        
        # Process the PDF
        result = self.processor_strategy.process(pdf_path)
        
        # Cache the result
        result_dict = asdict(result)
        await self.set_cached_pdf(path_str, result_dict)
        
        return result_dict
    
    def process_with_cache_sync(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Process a PDF with caching synchronously.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDF processing result, either from cache or freshly processed
        """
        path_str = str(pdf_path)
        
        # Try to get from cache first
        cached_result = self.get_cached_pdf_sync(path_str)
        if cached_result:
            logger.info(f"Cache hit for PDF: {path_str}")
            return cached_result
        
        # Not in cache, process the PDF
        logger.info(f"Cache miss for PDF: {path_str}, processing...")
        
        # Ensure path is a Path object
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        
        # Process the PDF
        result = self.processor_strategy.process(pdf_path)
        
        # Cache the result
        result_dict = asdict(result)
        self.set_cached_pdf_sync(path_str, result_dict)
        
        return result_dict


# Example usage
if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    
    async def main():
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        current_dir = Path(__file__).resolve().parent
        pdf_path = current_dir / "test.pdf"
        
        # Create PDF cache with enhanced processor
        processor = EnhancedPDFProcessorStrategy(enable_ocr=True)
        cache = PDFRedisCache(processor_strategy=processor)
        
        # Process PDF with caching
        result = await cache.process_with_cache(pdf_path)
        print(f"First processing, cached: {len(str(result))} bytes")
        
        # Process again (should be from cache)
        result2 = await cache.process_with_cache(pdf_path)
        print(f"Second processing, from cache: {len(str(result2))} bytes")
    
    # Run the async main function
    asyncio.run(main())
