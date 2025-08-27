# backend/app/logging_config.py
import logging
import sys

def setup_logging(log_level="INFO"):
    """
    Setup logging configuration with proper filtering
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler with a reasonable level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # CRITICAL: Silence noisy libraries
    logging.getLogger('pdfminer').setLevel(logging.WARNING)
    logging.getLogger('pdfminer.psparser').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.pdfinterp').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.cmapdb').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.pdfpage').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.converter').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.pdfparser').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.pdfdocument').setLevel(logging.ERROR)
    logging.getLogger('pdfminer.layout').setLevel(logging.ERROR)
    logging.getLogger('pdfplumber').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('pytesseract').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Log only important messages from uvicorn
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # Our app loggers can stay at configured level
    logging.getLogger('app').setLevel(getattr(logging, log_level.upper()))
    logging.getLogger('__main__').setLevel(getattr(logging, log_level.upper()))