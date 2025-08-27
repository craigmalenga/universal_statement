# backend/app/extraction.py - OPTIMIZED FOR PRODUCTION
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import logging
import re
import io

logger = logging.getLogger(__name__)

def extract_pdf_content(pdf_path: str) -> str:
    """
    Extract content from PDF using text extraction first, OCR as fallback
    """
    try:
        # First, try text extraction
        text_content = extract_text_from_pdf(pdf_path)
        
        # Check if we got meaningful content
        if is_meaningful_text(text_content):
            logger.info("Successfully extracted text from PDF")
            return normalize_text(text_content)
        
        # Fallback to OCR if text extraction failed
        logger.info("Text extraction insufficient, falling back to OCR")
        ocr_content = extract_text_with_ocr(pdf_path)
        
        if is_meaningful_text(ocr_content):
            logger.info("Successfully extracted text using OCR")
            return normalize_text(ocr_content)
        
        raise Exception("Could not extract meaningful content from PDF")
        
    except Exception as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        raise

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using pdfplumber
    """
    text_content = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"Processing PDF with {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                        # Only log progress at intervals
                        if page_num % 10 == 0 or page_num == total_pages - 1:
                            logger.debug(f"Processed {page_num + 1}/{total_pages} pages")
                except Exception as e:
                    if page_num == 0:  # Only log first failure
                        logger.warning(f"Could not extract text from some pages: {str(e)}")
                    continue
        
        logger.info(f"Text extraction complete: extracted from {len(text_content)}/{total_pages} pages")
        return '\n'.join(text_content)
        
    except Exception as e:
        logger.error(f"Error in text extraction: {str(e)}")
        return ""

def extract_text_with_ocr(pdf_path: str) -> str:
    """
    Extract text from PDF using OCR (for scanned documents)
    """
    ocr_content = []
    
    try:
        # Convert PDF to images
        logger.info("Converting PDF to images for OCR...")
        images = convert_from_path(pdf_path, dpi=300)
        total_pages = len(images)
        logger.info(f"Starting OCR on {total_pages} pages")
        
        for page_num, image in enumerate(images):
            try:
                # Preprocess image for better OCR
                processed_image = preprocess_image_for_ocr(image)
                
                # Extract text using OCR
                text = pytesseract.image_to_string(
                    processed_image, 
                    config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/-:£$€ \n'
                )
                
                if text.strip():
                    ocr_content.append(text)
                    # Only log progress at intervals
                    if page_num % 5 == 0 or page_num == total_pages - 1:
                        logger.debug(f"OCR processed {page_num + 1}/{total_pages} pages")
                    
            except Exception as e:
                if page_num == 0:  # Only log first failure
                    logger.warning(f"OCR failed on some pages: {str(e)}")
                continue
        
        logger.info(f"OCR complete: extracted from {len(ocr_content)}/{total_pages} pages")
        return '\n'.join(ocr_content)
        
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        return ""

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy
    """
    try:
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast and sharpness
        from PIL import ImageEnhance
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        return image
        
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {str(e)}")
        return image

def is_meaningful_text(text: str) -> bool:
    """
    Check if extracted text contains meaningful bank statement content
    """
    if not text or len(text.strip()) < 50:
        return False
    
    # Look for common bank statement indicators
    indicators = [
        r'\d{2}[/-]\d{2}[/-]\d{2,4}',  # Date patterns
        r'£\s*\d+\.\d{2}',              # Currency amounts
        r'\$\s*\d+\.\d{2}',             # Dollar amounts
        r'€\s*\d+\.\d{2}',              # Euro amounts
        r'\d+\.\d{2}',                  # Decimal numbers (amounts)
        r'balance',                      # Balance keyword
        r'debit|credit',                # Transaction types
        r'description',                 # Column headers
    ]
    
    text_lower = text.lower()
    matches = sum(1 for pattern in indicators if re.search(pattern, text_lower))
    
    # If we find at least 3 different indicators, consider it meaningful
    return matches >= 3

def normalize_text(text: str) -> str:
    """
    Normalize extracted text for better parsing
    """
    if not text:
        return ""
    
    try:
        # Fix encoding issues
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        # Remove excessive whitespace but preserve structure
        lines = []
        for line in text.split('\n'):
            # Clean up each line
            line = re.sub(r'\s+', ' ', line.strip())
            if line:  # Only keep non-empty lines
                lines.append(line)
        
        # Rejoin lines
        normalized = '\n'.join(lines)
        
        # Fix common OCR errors
        normalized = fix_common_ocr_errors(normalized)
        
        return normalized
        
    except Exception as e:
        logger.warning(f"Text normalization failed: {str(e)}")
        return text

def fix_common_ocr_errors(text: str) -> str:
    """
    Fix common OCR recognition errors
    """
    # Common OCR mistakes - FIXED GROUP REFERENCES
    replacements = {
        r'£(\s+)': '£',          # Fix currency spacing
        r'\$(\s+)': '$',         # Fix dollar spacing
        r'€(\s+)': '€',          # Fix euro spacing
        r'(\d)\s+\.(\d)': r'\1.\2',  # Fix decimal point spacing
        r'(\d)\s+,(\d)': r'\1,\2',   # Fix thousand separator spacing
        r'[Il|]\s*(\d)': r'1\1',     # Fix 1 recognition
        r'(\d)\s*[Il|]': r'\g<1>0',  # FIXED: Use \g<1> instead of \10
        r'[Oo](\d)': r'0\1',         # Fix O->0 at start
        r'(\d)[Oo]': r'\g<1>0',      # FIXED: Use \g<1> instead of \10
    }
    
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    
    return text