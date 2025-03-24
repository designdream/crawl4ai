"""
Enhanced PDF crawler strategy with Redis caching.
This module integrates the enhanced PDF processor with Redis caching
for high-performance PDF crawling.
"""

import os
import logging
import tempfile
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import aiofiles

from ...models import AsyncCrawlResponse, ScrapingResult
# Import the base classes directly
from crawl4ai.async_crawler_strategy import AsyncCrawlerStrategy
from crawl4ai.content_scraping_strategy import ContentScrapingStrategy
from .enhanced_processor import EnhancedPDFProcessorStrategy
from .redis_cache import PDFRedisCache

logger = logging.getLogger(__name__)

class EnhancedPDFCrawlerStrategy(AsyncCrawlerStrategy):
    """
    Enhanced PDF Crawler Strategy with Redis caching.
    This strategy extends the base PDFCrawlerStrategy with
    enhanced processing capabilities and distributed caching.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_ocr: bool = False,
        ocr_language: str = "eng",
        extract_tables: bool = True,
        extract_images: bool = True
    ):
        """
        Initialize the enhanced PDF crawler strategy.
        
        Args:
            redis_url: Redis URL for caching (if None, uses environment variable)
            enable_ocr: Whether to use OCR for scanned documents
            ocr_language: Language for OCR processing
            extract_tables: Whether to extract tables from PDFs
            extract_images: Whether to extract images from PDFs
        """
        super().__init__()
        
        # Use environment variable if not provided
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        
        # Create processor strategy
        self.processor = EnhancedPDFProcessorStrategy(
            enable_ocr=enable_ocr,
            ocr_language=ocr_language,
            extract_tables=extract_tables,
            extract_images=extract_images
        )
        
        # Create Redis cache with the processor
        self.cache = PDFRedisCache(
            redis_url=self.redis_url,
            processor_strategy=self.processor
        )
    
    async def crawl(self, url: str, **kwargs) -> AsyncCrawlResponse:
        """
        Initiate crawling for a PDF URL.
        Simply returns an AsyncCrawlResponse with empty HTML
        and the scraper will handle the actual processing.
        
        Args:
            url: URL of the PDF to crawl
            **kwargs: Additional crawler parameters
            
        Returns:
            AsyncCrawlResponse object
        """
        # Just pass through with empty HTML - scraper will handle actual processing
        return AsyncCrawlResponse(
            html="",  # Scraper will handle the real work
            response_headers={"Content-Type": "application/pdf"},
            status_code=200
        )


class EnhancedPDFContentScrapingStrategy(ContentScrapingStrategy):
    """
    Enhanced PDF Content Scraping Strategy with Redis caching.
    This strategy extends the base ContentScrapingStrategy with
    enhanced PDF processing capabilities and distributed caching.
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        enable_ocr: bool = False,
        ocr_language: str = "eng",
        extract_tables: bool = True,
        extract_images: bool = True,
        pdf_timeout: int = 30,
        max_pdf_size_mb: int = 50,
        password: Optional[str] = None
    ):
        """
        Initialize the enhanced PDF content scraping strategy.
        
        Args:
            redis_url: Redis URL for caching (if None, uses environment variable)
            enable_ocr: Whether to use OCR for scanned documents
            ocr_language: Language for OCR processing
            extract_tables: Whether to extract tables from PDFs
            extract_images: Whether to extract images from PDFs
            pdf_timeout: Timeout for PDF download in seconds
            max_pdf_size_mb: Maximum PDF size to process in MB
            password: Password for encrypted PDFs (can be overridden by kwargs)
        """
        super().__init__()
        
        # Use environment variable if not provided
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        
        # Configuration
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.extract_tables = extract_tables
        self.extract_images = extract_images
        self.pdf_timeout = pdf_timeout
        self.max_pdf_size_mb = max_pdf_size_mb
        self.password = password
        self.max_pdf_size_bytes = max_pdf_size_mb * 1024 * 1024
        
        # Create processor strategy
        self.processor = EnhancedPDFProcessorStrategy(
            enable_ocr=enable_ocr,
            ocr_language=ocr_language,
            extract_tables=extract_tables,
            extract_images=extract_images,
            password=password
        )
        
        # Create Redis cache with the processor
        self.cache = PDFRedisCache(
            redis_url=self.redis_url,
            processor_strategy=self.processor
        )
    
    async def scrape_content(self, url: str, html: str = "", **kwargs) -> ScrapingResult:
        """
        Scrape content from a PDF URL.
        
        Args:
            url: URL of the PDF to scrape
            html: HTML content (not used for PDFs)
            **kwargs: Additional scraping parameters
            
        Returns:
            ContentScrapingResult with PDF content
        """
        logger.info(f"Scraping PDF content from URL: {url}")
        
        # Check if we have cached result for this URL
        cached_result = await self.cache.get_cached_pdf(url)
        if cached_result:
            logger.info(f"Using cached PDF content for URL: {url}")
            return self._create_result_from_pdf_data(cached_result, url)
        
        # Get password from kwargs if provided
        password = kwargs.get("pdf_password", self.password)
        
        # Set up processor with potentially updated password
        if password != self.processor.password:
            self.processor.password = password
        
        # Download and process the PDF
        try:
            temp_dir = tempfile.mkdtemp()
            pdf_path = await self._download_pdf(url, temp_dir)
            
            if not pdf_path:
                # Create a ScrapingResult with failure status
                return ScrapingResult(
                    cleaned_html="<p>Failed to download PDF.</p>",
                    success=False,
                    metadata={"error": f"Failed to download PDF from {url}", "url": url}
                )
            
            # Process the PDF with caching
            pdf_result = await self.cache.process_with_cache(pdf_path)
            
            # Create content scraping result
            result = self._create_result_from_pdf_data(pdf_result, url)
            
            # Cache the result for future use
            await self.cache.set_cached_pdf(url, pdf_result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping PDF content: {str(e)}", exc_info=True)
            # Create a ScrapingResult with failure status
            return ScrapingResult(
                cleaned_html=f"<p>Error processing PDF: {str(e)}</p>",
                success=False,
                metadata={"error": f"Error processing PDF: {str(e)}", "url": url}
            )
    
    def scrap(self, url: str, html: str = "", **kwargs) -> ScrapingResult:
        """
        Synchronous version of scrape_content (required by ContentScrapingStrategy)
        This is a wrapper around the async method, using asyncio to run it
        
        Args:
            url: URL of the PDF to scrape
            html: HTML content (not used for PDFs)
            **kwargs: Additional scraping parameters
            
        Returns:
            ScrapingResult with PDF content
        """
        # Use asyncio to run the async method
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.scrape_content(url, html, **kwargs))
    
    def ascrap(self, url: str, html: str = "", **kwargs) -> ScrapingResult:
        """
        Alias for scrape_content to comply with ContentScrapingStrategy interface
        
        Args:
            url: URL of the PDF to scrape
            html: HTML content (not used for PDFs)
            **kwargs: Additional scraping parameters
            
        Returns:
            ScrapingResult with PDF content
        """
        return self.scrape_content(url, html, **kwargs)
    
    async def _download_pdf(self, url: str, temp_dir: str) -> Optional[Path]:
        """
        Download a PDF from a URL to a temporary directory.
        
        Args:
            url: URL of the PDF to download
            temp_dir: Temporary directory to save the PDF
            
        Returns:
            Path to the downloaded PDF or None if download failed
        """
        try:
            # Generate a filename from the URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename.endswith(".pdf"):
                filename = f"downloaded_pdf_{hash(url) & 0xFFFFFFFF}.pdf"
            
            pdf_path = Path(temp_dir) / filename
            
            # Download the PDF with timeout
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.pdf_timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download PDF: HTTP {response.status}")
                        return None
                    
                    # Check content type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                        logger.warning(f"URL does not point to a PDF: {content_type}")
                    
                    # Check size
                    content_length = int(response.headers.get("Content-Length", "0"))
                    if content_length > self.max_pdf_size_bytes:
                        logger.error(f"PDF too large: {content_length} bytes")
                        return None
                    
                    # Download with progress check
                    downloaded_size = 0
                    async with aiofiles.open(pdf_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(1024 * 1024):
                            downloaded_size += len(chunk)
                            if downloaded_size > self.max_pdf_size_bytes:
                                logger.error(f"PDF too large during download: {downloaded_size} bytes")
                                return None
                            await f.write(chunk)
            
            logger.info(f"Downloaded PDF to {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}", exc_info=True)
            return None
    
    def _create_result_from_pdf_data(self, pdf_data: Dict, url: str) -> ScrapingResult:
        """
        Create a ContentScrapingResult from PDF data.
        
        Args:
            pdf_data: PDF processing result data
            url: Original URL of the PDF
            
        Returns:
            ContentScrapingResult with PDF content
        """
        # Extract text from the PDF pages
        raw_text = ""
        html_content = ""
        
        # Check for errors
        if pdf_data.get("error"):
            return ScrapingResult(
                cleaned_html=f"<p>Error processing PDF: {pdf_data['error']}</p>",
                success=False,
                metadata={"error": pdf_data["error"], "url": url}
            )
        
        # Process each page
        pages = pdf_data.get("pages", [])
        for page in pages:
            page_num = page.get("page_number", 0)
            
            # Add raw text
            if page.get("raw_text"):
                raw_text += f"\n\n--- Page {page_num} ---\n\n"
                raw_text += page["raw_text"]
            
            # Add HTML content
            if page.get("html"):
                html_content += f'<div class="pdf-page" data-page="{page_num}">'
                html_content += f'<h2 class="pdf-page-header">Page {page_num}</h2>'
                html_content += page["html"]
                html_content += '</div>'
        
        # Get metadata
        metadata = pdf_data.get("metadata", {})
        title = metadata.get("title") or "Untitled PDF"
        author = metadata.get("author") or "Unknown Author"
        
        # Create metadata HTML
        metadata_html = f"""
        <div class="pdf-metadata">
            <h1>{title}</h1>
            <p><strong>Author:</strong> {author}</p>
            <p><strong>Pages:</strong> {metadata.get("pages", 0)}</p>
        </div>
        """
        
        # Create full HTML
        full_html = f"""
        <div class="pdf-document" data-url="{url}">
            {metadata_html}
            <div class="pdf-content">
                {html_content}
            </div>
        </div>
        """
        
        # Create enhanced metadata with PDF specific information
        enhanced_metadata = {
            "title": title,
            "author": author,
            "pages": metadata.get("pages", 0),
            "producer": metadata.get("producer"),
            "created": str(metadata.get("created")),
            "modified": str(metadata.get("modified")),
            "pdf_processing_time": pdf_data.get("processing_time", 0),
            "url": url,
            "raw_text": raw_text
        }
        
        # Create media and links objects (extracted from PDF if available)
        from ...models import Media, Links, MediaItem, Link
        
        # Extract images from PDF data if available
        media = Media()
        if pdf_data.get("images"):
            for idx, img_data in enumerate(pdf_data.get("images", [])):
                media.images.append(MediaItem(
                    src=img_data.get("path", ""),
                    data=img_data.get("data", ""),
                    alt=f"PDF image {idx+1}",
                    desc=f"Image extracted from PDF page {img_data.get('page', 0)}",
                    score=50,
                    type="image",
                    format=img_data.get("format", "jpg")
                ))
        
        # Extract links from PDF data if available
        links = Links()
        if pdf_data.get("links"):
            for link_data in pdf_data.get("links", []):
                links.external.append(Link(
                    href=link_data.get("url", ""),
                    text=link_data.get("text", ""),
                    title=link_data.get("title", "")
                ))
        
        # Create the result
        return ScrapingResult(
            cleaned_html=full_html,
            success=True,
            media=media,
            links=links,
            metadata=enhanced_metadata
        )
