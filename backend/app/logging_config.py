# backend/app/logging_config.py - SMART DEBUG MODE
import logging
import sys
import os

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
    
    # CRITICAL: Always silence the extremely noisy libraries regardless of log level
    noisy_loggers = [
        'pdfminer',
        'pdfminer.psparser',
        'pdfminer.pdfinterp', 
        'pdfminer.cmapdb',
        'pdfminer.pdfpage',
        'pdfminer.converter',
        'pdfminer.pdfparser',
        'pdfminer.pdfdocument',
        'pdfminer.layout',
        'pdfminer.pdfdevice',
        'pdfminer.pdffont',
        'pdfminer.pdfcolor',
        'pdfminer.psparser',
        'PIL.PngImagePlugin',
        'PIL.Image'
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    # Set reasonable levels for other libraries
    if log_level.upper() == "DEBUG":
        # Even in debug mode, keep libraries quieter
        logging.getLogger('pdfplumber').setLevel(logging.INFO)
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.INFO)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        
        # Our app can be verbose
        logging.getLogger('app').setLevel(logging.DEBUG)
        logging.getLogger('__main__').setLevel(logging.DEBUG)
    else:
        # Production mode - quiet everything
        logging.getLogger('pdfplumber').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('uvicorn').setLevel(logging.INFO)
        logging.getLogger('uvicorn.error').setLevel(logging.INFO)
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        
        # Our app at configured level
        logging.getLogger('app').setLevel(getattr(logging, log_level.upper()))
        logging.getLogger('__main__').setLevel(getattr(logging, log_level.upper()))