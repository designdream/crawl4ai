"""
Enhanced PDF processor using PyMuPDF (fitz) and Tesseract OCR.
This processor provides better text extraction, layout preservation,
and OCR capabilities for scanned documents.
"""

import os
import re
import json
import base64
import logging
import tempfile
from time import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union, Tuple, Any

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# Import required classes from local modules
from .processor import PDFProcessorStrategy, PDFProcessResult, PDFMetadata, PDFPage

from dataclasses import dataclass, field, asdict

# This import is now redundant since we're importing above
# Keeping line for reference

logger = logging.getLogger(__name__)

class EnhancedPDFProcessorStrategy(PDFProcessorStrategy):
    """
    Enhanced PDF processor using PyMuPDF and Tesseract for OCR.
    Provides superior text extraction with layout preservation and
    OCR capabilities for scanned documents.
    """
    
    def __init__(
        self,
        extract_images: bool = True,
        save_images_locally: bool = False,
        enable_ocr: bool = False,
        ocr_language: str = "eng",
        ocr_dpi: int = 300,
        extract_tables: bool = True,
        max_pages: Optional[int] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize the enhanced PDF processor strategy.
        
        Args:
            extract_images: Whether to extract images from the PDF
            save_images_locally: Whether to save extracted images to disk
            enable_ocr: Whether to use OCR for scanned documents
            ocr_language: Language for OCR (e.g., 'eng', 'fra', 'deu')
            ocr_dpi: DPI for OCR rendering
            extract_tables: Whether to extract tables from the PDF
            max_pages: Maximum number of pages to process (None for all)
            password: Password for encrypted PDFs
        """
        self.extract_images = extract_images
        self.save_images_locally = save_images_locally
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language
        self.ocr_dpi = ocr_dpi
        self.extract_tables = extract_tables
        self.max_pages = max_pages
        self.password = password
        self.current_page_number = 0
    
    def process(self, pdf_path: Path) -> PDFProcessResult:
        """
        Process a PDF file to extract text, images, and metadata.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            PDFProcessResult object containing metadata and page contents
        """
        start_time = time()
        # Create initial metadata (will be populated later)
        metadata = PDFMetadata()
        
        # Initialize result with empty pages and metadata
        result = PDFProcessResult(
            metadata=metadata,
            pages=[],
            processing_time=0.0
        )
        
        try:
            # Create image directory if needed
            image_dir = None
            if self.extract_images and self.save_images_locally:
                image_dir = pdf_path.parent / f"{pdf_path.stem}_images"
                image_dir.mkdir(exist_ok=True)
            
            # Open the PDF document with potential password
            # PyMuPDF handles passwords differently than our original setup
            doc = fitz.open(str(pdf_path))
            
            # Handle password if document is encrypted and password is provided
            if doc.is_encrypted and self.password:
                # Try to authenticate with provided password
                success = doc.authenticate(self.password)
                if not success:
                    raise ValueError(f"Invalid password for encrypted PDF: {pdf_path}")
            
            # Extract metadata
            result.metadata = self._extract_metadata(pdf_path, doc)
            
            # Determine pages to process
            total_pages = len(doc)
            pages_to_process = min(total_pages, self.max_pages or total_pages)
            
            # Process each page
            for i in range(pages_to_process):
                self.current_page_number = i + 1
                page = doc[i]
                pdf_page = self._process_page(page, image_dir)
                result.pages.append(asdict(pdf_page))
                
        except fitz.FileDataError as e:
            result.error = f"Invalid or corrupted PDF file: {str(e)}"
            logger.error(f"Failed to process PDF: {result.error}")
        except fitz.EmptyFileError as e:
            result.error = f"Empty PDF file: {str(e)}"
            logger.error(f"Failed to process PDF: {result.error}")
        except Exception as e:
            result.error = f"Error processing PDF: {str(e)}"
            logger.error(f"Failed to process PDF: {result.error}", exc_info=True)
        
        # Calculate processing time
        result.processing_time = time() - start_time
        return result
    
    def process_async(self, pdf_path: Path, batch_size: int = 5) -> PDFProcessResult:
        """
        Process a PDF file asynchronously in batches.
        This is a placeholder - in a real implementation this would use asyncio.
        
        Args:
            pdf_path: Path to the PDF file
            batch_size: Number of pages to process in each batch
            
        Returns:
            PDFProcessResult object containing metadata and page contents
        """
        # For now, just call the sync method as a placeholder
        # In a real implementation, this would use asyncio to process pages concurrently
        return self.process(pdf_path)
        
    def _process_page(self, page, image_dir: Optional[Path]) -> PDFPage:
        """Process a single page of the PDF document."""
        
        pdf_page = PDFPage(
            page_number=self.current_page_number,
        )
        
        # Extract text with formatting information
        text_blocks = page.get_text("dict")
        pdf_page.raw_text = page.get_text()
        
        # Track layout information
        for block in text_blocks.get("blocks", []):
            if "lines" in block:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        pdf_page.layout.append({
                            "type": "text",
                            "text": span.get("text", ""),
                            "x": span.get("origin", [0, 0])[0],
                            "y": span.get("origin", [0, 0])[1],
                            "font": span.get("font", ""),
                            "font_size": span.get("size", 0),
                            "color": span.get("color", 0)
                        })
        
        # Check if OCR is needed
        if self.enable_ocr and len(pdf_page.raw_text.strip()) < 100:
            ocr_text = self._apply_ocr(page)
            if ocr_text.strip():
                pdf_page.raw_text = ocr_text
                pdf_page.ocr_applied = True
        
        # Extract images if requested
        if self.extract_images:
            pdf_page.images = self._extract_images(page, image_dir)
        
        # Extract links
        pdf_page.links = self._extract_links(page)
        
        # Extract tables if requested
        if self.extract_tables:
            pdf_page.tables = self._extract_tables(page)
        
        # Generate clean text and HTML
        from .utils import clean_pdf_text, clean_pdf_text_to_html
        pdf_page.markdown = clean_pdf_text(self.current_page_number, pdf_page.raw_text)
        pdf_page.html = clean_pdf_text_to_html(self.current_page_number, pdf_page.raw_text)
        
        return pdf_page
    
    def _apply_ocr(self, page) -> str:
        """Apply OCR to a page image for text extraction."""
        try:
            # Render page to an image at the specified DPI
            pix = page.get_pixmap(matrix=fitz.Matrix(self.ocr_dpi/72, self.ocr_dpi/72))
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Apply OCR
            text = pytesseract.image_to_string(img, lang=self.ocr_language)
            return text
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            return ""
    
    def _extract_images(self, page, image_dir: Optional[Path]) -> List[Dict]:
        """Extract images from a page."""
        images = []
        
        if not self.extract_images:
            return images
        
        try:
            # Extract images using PyMuPDF
            img_list = page.get_images(full=True)
            
            # Process each image
            for img_index, img_info in enumerate(img_list):
                try:
                    xref = img_info[0]  # Image reference in the PDF
                    base_img = page.parent.extract_image(xref)
                    
                    if base_img:
                        img_data = base_img["image"]
                        img_ext = base_img["ext"]
                        img_width = base_img.get("width", 0)
                        img_height = base_img.get("height", 0)
                        img_colorspace = base_img.get("colorspace", 0)
                        
                        img_filename = f"page_{self.current_page_number}_img_{img_index+1}"
                        
                        # Handle image based on save preference
                        if self.save_images_locally and image_dir:
                            final_path = (image_dir / img_filename).with_suffix(f".{img_ext}")
                            with open(final_path, "wb") as f:
                                f.write(img_data)
                            image_data = str(final_path)
                        else:
                            image_data = base64.b64encode(img_data).decode('utf-8')
                        
                        # Add image info to results
                        image_info = {
                            "format": img_ext,
                            "width": img_width,
                            "height": img_height,
                            "color_space": str(img_colorspace),
                            "bits_per_component": 8  # Default assumption
                        }
                        
                        if self.save_images_locally:
                            image_info["path"] = image_data
                        else:
                            image_info["data"] = image_data
                            
                        images.append(image_info)
                except Exception as e:
                    logger.error(f"Error processing image {img_index}: {str(e)}")
        except Exception as e:
            logger.error(f"Image extraction error: {str(e)}")
        
        return images
    
    def _extract_links(self, page) -> List[str]:
        """Extract links from a page."""
        links = []
        try:
            for link in page.get_links():
                if link.get("uri"):
                    links.append(link["uri"])
        except Exception as e:
            logger.error(f"Link extraction error: {str(e)}")
        return links
    
    def _extract_tables(self, page) -> List[Dict]:
        """Extract tables from a page."""
        tables = []
        try:
            # PyMuPDF doesn't have direct table extraction
            # This is a placeholder for future implementation
            # Consider using tabula-py or camelot-py for table extraction
            pass
        except Exception as e:
            logger.error(f"Table extraction error: {str(e)}")
        return tables
    
    def _extract_metadata(self, pdf_path: Path, doc) -> PDFMetadata:
        """Extract metadata from a PDF document."""
        try:
            meta = doc.metadata
            
            # Parse dates
            created = self._parse_pdf_date(meta.get("creationDate", ""))
            modified = self._parse_pdf_date(meta.get("modDate", ""))
            
            return PDFMetadata(
                title=meta.get("title"),
                author=meta.get("author"),
                producer=meta.get("producer"),
                created=created,
                modified=modified,
                pages=len(doc),
                encrypted=doc.is_encrypted,
                file_size=pdf_path.stat().st_size
            )
        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            # Return minimal metadata
            return PDFMetadata(
                pages=len(doc) if doc else 0,
                file_size=pdf_path.stat().st_size
            )
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date format."""
        try:
            if not date_str:
                return None
            
            # PyMuPDF date format: "D:20200101120000+01'00'"
            match = re.match(r'D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', date_str)
            if not match:
                return None
                
            return datetime(
                year=int(match[1]),
                month=int(match[2]),
                day=int(match[3]),
                hour=int(match[4]),
                minute=int(match[5]),
                second=int(match[6])
            )
        except Exception:
            return None


# Usage example
if __name__ == "__main__":
    import json
    from pathlib import Path
    
    current_dir = Path(__file__).resolve().parent
    pdf_path = f'{current_dir}/test.pdf'
    
    # Test the enhanced processor
    strategy = EnhancedPDFProcessorStrategy(enable_ocr=True)
    result = strategy.process(Path(pdf_path))
    
    # Convert to JSON
    json_output = asdict(result)
    print(json.dumps(json_output, indent=2, default=str))
    
    # Generate HTML output
    with open(f'{current_dir}/test_enhanced.html', 'w') as f:
        for page in result.pages:
            f.write(f'<h1>Page {page["page_number"]}</h1>')
            f.write(page['html'])
