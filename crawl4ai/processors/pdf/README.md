# Enhanced PDF Processing

This module provides advanced PDF processing capabilities for Crawl4AI, including:

- Text extraction with layout preservation using PyMuPDF
- OCR support for scanned documents via Tesseract
- Image and link extraction
- Table detection
- Redis-based caching for performance optimization

## Components

- `EnhancedPDFProcessorStrategy`: Core processing engine for PDF files
- `EnhancedPDFCrawlerStrategy`: Async crawler strategy for PDFs
- `EnhancedPDFContentScrapingStrategy`: Content scraping strategy for PDF URLs
- `PDFRedisCache`: Redis-based cache for PDF processing results

## Usage

### Installation

```bash
pip install "crawl4ai[pdf-enhanced]"
```

### Basic Usage

```python
from pathlib import Path
from crawl4ai.processors.pdf import EnhancedPDFProcessorStrategy

processor = EnhancedPDFProcessorStrategy(enable_ocr=True)
result = processor.process(Path("document.pdf"))
```

### With ScrapingBee

```python
from crawl4ai.processors.pdf import EnhancedPDFContentScrapingStrategy

# Configure ScrapingBee proxy
proxy_config = {
    "proxy": f"http://YOUR_API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"
}

scraper = EnhancedPDFContentScrapingStrategy(
    enable_ocr=True,
    proxy_config=proxy_config
)

# Scrape PDF from URL
result = await scraper.scrape_content("https://example.com/document.pdf")
```

### With Redis Caching

```python
from crawl4ai.processors.pdf import EnhancedPDFProcessorStrategy
from crawl4ai.processors.pdf.redis_cache import PDFRedisCache

# Connect to Redis
cache = PDFRedisCache(redis_url="redis://localhost:6379/0")

# Create processor with cache
processor = EnhancedPDFProcessorStrategy(
    enable_ocr=True,
    pdf_cache=cache
)

# Process PDF (will use cache if available)
result = processor.process("document.pdf")
```

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: "redis://localhost:6379/0")
- `SCRAPINGBEE_KEY`: ScrapingBee API key for proxy access

## More Information

See the [comprehensive documentation](../../docs/md_v2/advanced/enhanced_pdf_processing.md) for detailed usage examples and configuration options.
