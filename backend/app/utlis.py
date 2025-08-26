# backend/app/utils.py
import os
import logging
from pathlib import Path
import time
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

def cleanup_temp_files(session_id: str, temp_dir: Path, max_age_hours: int = 24):
    """
    Clean up temporary files for a session
    """
    try:
        # Remove files for specific session
        patterns = [
            f"{session_id}_*.pdf",
            f"{session_id}_*.xlsx", 
            f"{session_id}_*.csv"
        ]
        
        files_removed = 0
        for pattern in patterns:
            for file_path in temp_dir.glob(pattern):
                try:
                    file_path.unlink()
                    files_removed += 1
                    logger.debug(f"Removed temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove temp file {file_path}: {str(e)}")
        
        logger.info(f"Cleaned up {files_removed} temp files for session {session_id}")
        
        # Also clean up old files from all sessions
        cleanup_old_temp_files(temp_dir, max_age_hours)
        
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")

def cleanup_old_temp_files(temp_dir: Path, max_age_hours: int = 24):
    """
    Clean up old temporary files from all sessions
    """
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        files_removed = 0
        
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                try:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        files_removed += 1
                        logger.debug(f"Removed old temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove old temp file {file_path}: {str(e)}")
        
        if files_removed > 0:
            logger.info(f"Cleaned up {files_removed} old temp files")
            
    except Exception as e:
        logger.error(f"Error cleaning up old temp files: {str(e)}")

def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes
    """
    try:
        return os.path.getsize(file_path)
    except Exception:
        return None

def validate_file_size(file_path: str, max_size_mb: int = 50) -> bool:
    """
    Validate that file size is within limits
    """
    try:
        file_size = get_file_size(file_path)
        if file_size is None:
            return False
        
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
        
    except Exception as e:
        logger.error(f"Error validating file size: {str(e)}")
        return False

def ensure_temp_directory(temp_dir: Path):
    """
    Ensure temporary directory exists and is writable
    """
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write permissions
        test_file = temp_dir / "test_write_permission.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        test_file.unlink()
        
        logger.info(f"Temp directory ready: {temp_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up temp directory: {str(e)}")
        return False

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def log_processing_stats(session_id: str, file_name: str, file_size: int, 
                        processing_time: float, transaction_count: int):
    """
    Log processing statistics for monitoring
    """
    try:
        stats = {
            'session_id': session_id,
            'file_name': file_name,
            'file_size': format_file_size(file_size),
            'processing_time_seconds': round(processing_time, 2),
            'transaction_count': transaction_count,
            'transactions_per_second': round(transaction_count / processing_time, 2) if processing_time > 0 else 0
        }
        
        logger.info(f"Processing stats: {stats}")
        
    except Exception as e:
        logger.warning(f"Error logging processing stats: {str(e)}")

def create_error_response(error_message: str, error_code: str = "PROCESSING_ERROR") -> dict:
    """
    Create standardized error response
    """
    return {
        'error': True,
        'error_code': error_code,
        'message': error_message,
        'timestamp': time.time()
    }

def validate_pdf_file(file_path: str) -> tuple[bool, str]:
    """
    Validate that the file is a valid PDF
    """
    try:
        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return False, "File is not a PDF"
        
        # Check file exists and has content
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = get_file_size(file_path)
        if file_size == 0:
            return False, "File is empty"
        
        # Try to read first few bytes to check PDF header
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if not header.startswith(b'%PDF-'):
                return False, "File is not a valid PDF format"
        
        return True, "Valid PDF file"
        
    except Exception as e:
        return False, f"Error validating PDF: {str(e)}"

def safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing/replacing dangerous characters
    """
    import re
    
    # Remove directory traversal attempts
    filename = os.path.basename(filename)
    
    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:96] + ext
    
    return filename

def get_system_info():
    """
    Get basic system information for debugging
    """
    try:
        import platform
        import psutil
        
        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
            'disk_free_gb': round(psutil.disk_usage('/').free / (1024**3), 2)
        }
        
        return info
        
    except Exception as e:
        logger.warning(f"Could not get system info: {str(e)}")
        return {'error': str(e)}

def setup_logging(log_level: str = "INFO"):
    """
    Setup logging configuration
    """
    try:
        level = getattr(logging, log_level.upper())
        
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('app.log', mode='a')
            ]
        )
        
        # Reduce noise from external libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('pytesseract').setLevel(logging.WARNING)
        
        logger.info(f"Logging setup complete at level: {log_level}")
        
    except Exception as e:
        print(f"Error setting up logging: {str(e)}")

def check_dependencies():
    """
    Check that all required dependencies are available
    """
    dependencies = {
        'pdfplumber': 'PDF text extraction',
        'pdf2image': 'PDF to image conversion',
        'pytesseract': 'OCR functionality',
        'pandas': 'Data processing',
        'openpyxl': 'Excel export',
        'PIL': 'Image processing'
    }
    
    missing_deps = []
    
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            logger.debug(f"✓ {dep} - {description}")
        except ImportError:
            missing_deps.append(f"{dep} - {description}")
            logger.error(f"✗ Missing: {dep} - {description}")
    
    if missing_deps:
        error_msg = f"Missing dependencies: {', '.join([dep.split(' -')[0] for dep in missing_deps])}"
        logger.error(error_msg)
        return False, error_msg
    
    logger.info("All dependencies are available")
    return True, "All dependencies check passed"

def check_tesseract_installation():
    """
    Check if Tesseract OCR is properly installed
    """
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {version}")
        return True, f"Tesseract {version} is available"
    except Exception as e:
        error_msg = f"Tesseract OCR not available: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg