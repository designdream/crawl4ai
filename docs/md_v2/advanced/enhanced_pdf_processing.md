# Enhanced PDF Processing

## Overview

Crawl4AI's Enhanced PDF Processing is a powerful feature that allows for advanced PDF document handling, text extraction, and content analysis. Built with PyMuPDF (fitz) and Tesseract OCR integration, it offers superior text extraction capabilities, layout preservation, and optical character recognition for scanned documents.

Redis caching is integrated to provide performance optimization, making repeated processing of the same PDF documents significantly faster.

## Key Features

### Advanced Text Extraction

- **Superior Text Quality**: Extract clean, properly formatted text while preserving original document layout
- **Structure Preservation**: Maintain headings, paragraphs, and formatting for better content understanding
- **Metadata Extraction**: Get comprehensive document metadata including title, author, creation date, and more

### OCR Capabilities

- **Scanned Document Support**: Process scanned PDFs and images embedded within PDFs
- **Multi-language OCR**: Support for multiple languages via Tesseract OCR
- **Image-to-Text Conversion**: Convert images within PDFs to searchable text

### Layout Analysis

- **Table Detection**: Identify and extract tabular data from PDFs
- **Image Extraction**: Pull out images with position and size information
- **Link Detection**: Extract hyperlinks and references from PDF documents

### Performance Optimization

- **Redis Caching**: Store processed results in Redis for lightning-fast retrieval
- **Distributed Caching**: Share cached results across distributed systems
- **Configurable Cache TTL**: Set expiration times for cached content based on your needs

## Usage Examples

### Basic PDF Processing

```python
from pathlib import Path
from crawl4ai.processors.pdf import EnhancedPDFProcessorStrategy

# Initialize the enhanced processor
processor = EnhancedPDFProcessorStrategy(
    enable_ocr=True,  # Enable OCR for scanned documents
    ocr_language="eng",  # Set OCR language
    extract_images=True,  # Extract images from the PDF
)

# Process a PDF file
pdf_path = Path("/path/to/document.pdf")
result = processor.process(pdf_path)

# Access the extracted content
print(f"Document title: {result.metadata.title}")
print(f"Number of pages: {len(result.pages)}")

# Print text from the first page
if result.pages:
    print(f"First page text: {result.pages[0].raw_text[:200]}...")
```

### Using Redis Caching

```python
from pathlib import Path
from crawl4ai.processors.pdf import EnhancedPDFProcessorStrategy
from crawl4ai.processors.pdf.redis_cache import PDFRedisCache

# Initialize Redis cache with default connection
pdf_cache = PDFRedisCache()

# Create processor with cache integration
processor = EnhancedPDFProcessorStrategy(
    enable_ocr=True,
    pdf_cache=pdf_cache,
    cache_ttl=3600,  # Cache results for 1 hour
)

# Process a PDF file (will use cache if available)
result = processor.process("/path/to/document.pdf")
```

### PDF Content Scraping

```python
import asyncio
from crawl4ai.processors.pdf import EnhancedPDFContentScrapingStrategy

async def scrape_pdf():
    # Initialize the PDF scraping strategy
    scraper = EnhancedPDFContentScrapingStrategy(
        enable_ocr=True,
        extract_tables=True
    )
    
    # Scrape PDF content from a URL
    pdf_url = "https://example.com/document.pdf"
    result = await scraper.scrape_content(pdf_url)
    
    # Access the scraped content
    print(f"PDF Title: {result.metadata.get('title')}")
    print(f"Content preview: {result.content[:200]}...")

# Run the async function
asyncio.run(scrape_pdf())
```

### Using with ScrapingBee Proxy

```python
import asyncio
import os
from crawl4ai.processors.pdf import EnhancedPDFContentScrapingStrategy

async def scrape_pdf_with_proxy():
    # Configure proxy for ScrapingBee
    scrapingbee_key = os.environ.get("SCRAPINGBEE_KEY")
    proxy_config = {
        "proxy": f"http://{scrapingbee_key}:render_js=true&premium=true@proxy.scrapingbee.com:8886"
    }
    
    # Initialize scraper with proxy configuration
    scraper = EnhancedPDFContentScrapingStrategy(
        enable_ocr=True,
        proxy_config=proxy_config
    )
    
    # Scrape PDF from a URL that might require a proxy
    result = await scraper.scrape_content("https://example.com/document.pdf")
    
    # Process the result
    if result.success:
        print("Successfully scraped PDF content")
        print(f"Content length: {len(result.content)} characters")
    else:
        print(f"Failed to scrape PDF: {result.metadata.get('error')}")

# Run the async function
asyncio.run(scrape_pdf_with_proxy())
```

## Configuration Options

### EnhancedPDFProcessorStrategy

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `extract_images` | bool | `True` | Whether to extract images from the PDF |
| `save_images_locally` | bool | `False` | Whether to save extracted images to disk |
| `enable_ocr` | bool | `False` | Whether to use OCR for text extraction |
| `ocr_language` | str | `"eng"` | Language for OCR (Tesseract language code) |
| `ocr_dpi` | int | `300` | DPI for OCR image processing |
| `extract_tables` | bool | `True` | Whether to extract tables from the PDF |
| `max_pages` | int | `None` | Maximum number of pages to process (None = all) |
| `password` | str | `None` | Password for encrypted PDFs |
| `pdf_cache` | PDFRedisCache | `None` | Redis cache instance for caching results |
| `cache_ttl` | int | `3600` | Time-to-live for cached results in seconds |

### EnhancedPDFContentScrapingStrategy

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_ocr` | bool | `False` | Whether to use OCR for text extraction |
| `extract_tables` | bool | `True` | Whether to extract tables from the PDF |
| `proxy_config` | dict | `None` | Proxy configuration for downloading PDFs |
| `cache_ttl` | int | `3600` | Time-to-live for cached results in seconds |
| `redis_url` | str | `"redis://localhost:6379/0"` | Redis connection URL for caching |

## Redis Cache Configuration

The Enhanced PDF Processing module uses Redis for caching processed PDFs. By default, it connects to a local Redis instance, but you can configure it to use a remote Redis server:

```python
from crawl4ai.processors.pdf.redis_cache import PDFRedisCache

# Connect to a specific Redis server
cache = PDFRedisCache(
    redis_url="redis://username:password@redis-server:6379/0",
    prefix="pdf_cache:",  # Custom key prefix
    ttl=86400  # 24 hours TTL
)
```

You can configure the Redis connection using the `REDIS_URL` environment variable:

```bash
export REDIS_URL="redis://redis-server:6379/0"
```

## API Integration

### Using with the Crawl4AI API

The Enhanced PDF Processing capabilities are fully integrated with the Crawl4AI API service. You can enable PDF processing by including specific parameters in your API requests.

#### API Endpoints

The API supports multiple endpoint paths for backward compatibility:

- Primary endpoint: `/crawl` (recommended for new integrations)
- Legacy endpoints (fully supported):
  - `/api/crawl`
  - `/api/v1/crawl`

#### Example API Request (Current Endpoint)

```bash
curl -X POST \
  https://api.example.com/crawl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{"url":"https://example.com/document.pdf","params":{"enable_pdf_processing":true,"enable_ocr":true,"extract_tables":true}}'
```

#### Example API Request (Legacy Endpoint)

```bash
curl -X POST \
  https://api.example.com/api/v1/crawl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{"url":"https://example.com/document.pdf","params":{"enable_pdf_processing":true,"enable_ocr":true,"extract_tables":true}}'
```

#### ScrapingBee Integration

For PDFs behind anti-scraping protection, you can utilize ScrapingBee by including a proxy configuration:

```bash
curl -X POST \
  https://api.example.com/crawl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{"url":"https://example.com/protected-document.pdf","params":{"enable_pdf_processing":true,"proxy":"http://AJTU2OHTQB3M8Z8RRQ0WRID8IU0XSZM6CXYVH4U9MSICE3OE1WWYLA70MDOTL184644GKIXI3A5HEPQ1:render_js=true&premium=true@proxy.scrapingbee.com:8886"}}'
```

> **Important**: The ScrapingBee proxy configuration must use this specific format: `http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886`
- Compatible legacy endpoints: 
  - `/api/crawl`
  - `/api/v1/crawl`

#### Example Request

```bash
curl -X POST https://api.crawl4ai.com/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/document.pdf",
    "params": {
      "enable_pdf_processing": true,
      "enable_ocr": true,
      "extract_tables": true
    }
  }'
```

The same request would also work with the legacy endpoints:

```bash
curl -X POST https://api.crawl4ai.com/api/crawl \
  -H "Content-Type: application/json" \
  -d '{ ... }'
```

### ScrapingBee Integration

When processing PDFs from websites that require browser rendering or are behind anti-scraping protections, use the ScrapingBee proxy configuration:

```json
{
  "url": "https://example.com/document.pdf",
  "params": {
    "enable_pdf_processing": true,
    "proxy": "http://API_KEY:render_js=true&premium=true@proxy.scrapingbee.com:8886"
  }
}
```

Replace `API_KEY` with your ScrapingBee API key. In production environments, this key should be securely loaded from environment variables.

## Requirements

The Enhanced PDF Processing module requires the following dependencies:

- PyMuPDF (fitz)
- pytesseract
- Tesseract OCR (system dependency)
- pdf2image
- Poppler (system dependency)
- Redis
- hiredis (optional, for better Redis performance)
- httpx (for API compatibility layer)

You can install these dependencies using:

```bash
pip install "crawl4ai[pdf-enhanced]"
```

For system dependencies (Tesseract and Poppler), please refer to their installation instructions for your specific platform.

## Error Handling

The enhanced PDF processor includes robust error handling to manage various failure scenarios:

- Invalid or corrupted PDFs
- Password-protected documents
- OCR processing failures
- Redis connection issues

All errors are properly logged and can be caught using standard exception handling mechanisms.

## Performance Considerations

- OCR processing can be resource-intensive, especially for large documents
- Consider setting `max_pages` for very large PDFs to limit processing time
- Redis caching significantly improves performance for repeated processing
- For production environments, consider using a dedicated Redis instance
