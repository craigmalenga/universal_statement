# backend/app/main.py - PRODUCTION OPTIMIZED
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import os
import tempfile
import uuid
from pathlib import Path
import logging
import traceback
import time
from datetime import datetime
import json

# Import logging config BEFORE other modules
from .logging_config import setup_logging

# Setup logging with appropriate level for production
# Use INFO for production, DEBUG only for development
log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logging(log_level)
logger = logging.getLogger(__name__)

# Import after logging setup to ensure proper log filtering
from .extraction import extract_pdf_content
from .parsing import parse_transactions
from .export import export_to_files
from .utils import cleanup_temp_files

app = FastAPI(title="Bank Statement Converter", version="1.0.0")

# CORS configuration - fixed
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://frontend-production-358c.up.railway.app",
]

# Add your frontend domain if different
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url and frontend_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for processing
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

# Store debug logs for sessions
debug_logs: Dict[str, list] = {}

def add_debug_log(session_id: str, level: str, message: str, data: Any = None):
    """Add a debug log entry for a session"""
    if session_id not in debug_logs:
        debug_logs[session_id] = []
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'data': data
    }
    
    debug_logs[session_id].append(log_entry)
    
    # Also log to file
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        f"[{session_id}] {message}" + (f" - Data: {data}" if data else "")
    )

@app.get("/")
async def root():
    return {"message": "Bank Statement Converter API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Enhanced health check with system info"""
    try:
        import psutil
        import pytesseract
        
        # Check Tesseract
        try:
            tesseract_version = pytesseract.get_tesseract_version()
            tesseract_status = f"Available (v{tesseract_version})"
        except Exception as e:
            tesseract_status = f"Error: {str(e)}"
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "memory_percent": psutil.virtual_memory().percent,
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "tesseract": tesseract_status,
                "temp_files": len(list(TEMP_DIR.glob("*")))
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {"status": "healthy", "error": str(e)}

@app.post("/convert")
async def convert_bank_statement(
    file: UploadFile = File(...),
    debug: bool = False  # Disable debug mode by default in production
):
    """
    Convert uploaded PDF bank statement to Excel and CSV format
    """
    session_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Initialize debug log only if debug mode is enabled
    if debug:
        add_debug_log(session_id, "INFO", "Starting conversion process", {
            "filename": file.filename,
            "content_type": file.content_type,
            "debug_mode": debug
        })
    else:
        logger.info(f"Starting conversion for session {session_id}, file: {file.filename}")
    
    if not file.filename.lower().endswith('.pdf'):
        error_msg = f"Invalid file type: {file.filename}"
        if debug:
            add_debug_log(session_id, "ERROR", error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    temp_pdf_path = TEMP_DIR / f"{session_id}_input.pdf"
    
    try:
        # Save uploaded file
        if debug:
            add_debug_log(session_id, "INFO", "Saving uploaded file")
        
        file_content = await file.read()
        file_size = len(file_content)
        
        with open(temp_pdf_path, "wb") as buffer:
            buffer.write(file_content)
        
        if debug:
            add_debug_log(session_id, "INFO", "File saved successfully", {
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024*1024), 2),
                "path": str(temp_pdf_path)
            })
        else:
            logger.info(f"File saved: {file_size} bytes")
        
        # Validate PDF
        with open(temp_pdf_path, 'rb') as f:
            header = f.read(5)
            if not header.startswith(b'%PDF-'):
                raise ValueError("Invalid PDF header")
        
        if debug:
            add_debug_log(session_id, "INFO", "PDF validation passed")
        
        # Extract content from PDF
        if debug:
            add_debug_log(session_id, "INFO", "Starting PDF content extraction")
            raw_content, extraction_details = extract_pdf_content_with_debug(
                str(temp_pdf_path), session_id
            )
        else:
            raw_content = extract_pdf_content(str(temp_pdf_path))
            extraction_details = {}
        
        if not raw_content or not raw_content.strip():
            error_msg = "No content extracted from PDF"
            if debug:
                add_debug_log(session_id, "ERROR", error_msg)
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": error_msg,
                    "debug_logs": debug_logs.get(session_id, []) if debug else None,
                    "raw_content": None
                }
            )
        
        # Parse transactions
        if debug:
            add_debug_log(session_id, "INFO", "Starting transaction parsing")
            transactions_df, parsing_details = parse_transactions_with_debug(
                raw_content, session_id
            )
        else:
            transactions_df = parse_transactions(raw_content)
            parsing_details = {}
        
        if transactions_df.empty:
            error_msg = "No transactions found in the PDF"
            if debug:
                add_debug_log(session_id, "WARNING", error_msg)
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": True,
                    "message": error_msg,
                    "debug_logs": debug_logs.get(session_id, []) if debug else None,
                    "raw_content": raw_content[:5000] if debug else None
                }
            )
        
        # Export to Excel and CSV
        if debug:
            add_debug_log(session_id, "INFO", "Starting export to Excel and CSV")
        
        excel_path, csv_path = export_to_files(transactions_df, session_id, TEMP_DIR)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        logger.info(f"Conversion completed for session {session_id}: {len(transactions_df)} transactions in {processing_time:.2f}s")
        
        # Prepare response
        response_data = {
            "session_id": session_id,
            "transactions_count": len(transactions_df),
            "excel_url": f"/download/{session_id}/excel",
            "csv_url": f"/download/{session_id}/csv",
            "processing_time": round(processing_time, 2),
            "success": True
        }
        
        # Add debug information if requested
        if debug:
            response_data.update({
                "debug_logs": debug_logs.get(session_id, []),
                "raw_content_preview": raw_content[:2000] if raw_content else None,
                "extraction_details": extraction_details,
                "parsing_details": parsing_details,
                "sample_transactions": transactions_df.head(5).to_dict('records') if not transactions_df.empty else []
            })
        
        return response_data
        
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        logger.error(f"Error in session {session_id}: {error_msg}")
        
        if debug:
            add_debug_log(session_id, "ERROR", error_msg, {
                "traceback": traceback.format_exc()
            })
        
        # Clean up on error
        cleanup_temp_files(session_id, TEMP_DIR)
        
        # Return detailed error response
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": error_msg,
                "session_id": session_id,
                "debug_logs": debug_logs.get(session_id, []) if debug else None,
                "traceback": traceback.format_exc() if debug else None
            }
        )

def extract_pdf_content_with_debug(pdf_path: str, session_id: str) -> tuple[str, dict]:
    """Enhanced extraction with debugging info"""
    from .extraction import extract_text_from_pdf, extract_text_with_ocr, is_meaningful_text, normalize_text
    
    extraction_details = {
        "method": None,
        "pages_processed": 0,
        "text_extraction_result": None,
        "ocr_result": None
    }
    
    try:
        # Try text extraction
        add_debug_log(session_id, "DEBUG", "Attempting text extraction")
        text_content = extract_text_from_pdf(pdf_path)
        extraction_details["text_extraction_result"] = {
            "content_length": len(text_content),
            "has_content": bool(text_content.strip())
        }
        
        if is_meaningful_text(text_content):
            add_debug_log(session_id, "DEBUG", "Text extraction successful")
            extraction_details["method"] = "text_extraction"
            return normalize_text(text_content), extraction_details
        
        # Fallback to OCR
        add_debug_log(session_id, "DEBUG", "Text extraction insufficient, trying OCR")
        ocr_content = extract_text_with_ocr(pdf_path)
        extraction_details["ocr_result"] = {
            "content_length": len(ocr_content),
            "has_content": bool(ocr_content.strip())
        }
        
        if is_meaningful_text(ocr_content):
            add_debug_log(session_id, "DEBUG", "OCR extraction successful")
            extraction_details["method"] = "ocr"
            return normalize_text(ocr_content), extraction_details
        
        # Both methods failed
        add_debug_log(session_id, "WARNING", "Both extraction methods produced insufficient content")
        extraction_details["method"] = "failed"
        
        # Return whatever we got
        return text_content or ocr_content, extraction_details
        
    except Exception as e:
        add_debug_log(session_id, "ERROR", f"Extraction error: {str(e)}")
        extraction_details["error"] = str(e)
        raise

def parse_transactions_with_debug(raw_content: str, session_id: str) -> tuple:
    """Enhanced parsing with debugging info"""
    from .parsing import parse_standard_uk_format, parse_tabular_format, parse_line_by_line, clean_transaction_data, preprocess_content
    import pandas as pd
    
    parsing_details = {
        "strategy_used": None,
        "strategies_tried": [],
        "transactions_per_strategy": {}
    }
    
    try:
        # Preprocess content
        content = preprocess_content(raw_content)
        add_debug_log(session_id, "DEBUG", "Content preprocessed", {
            "original_length": len(raw_content),
            "processed_length": len(content)
        })
        
        transactions = []
        
        # Try Strategy 1: Standard UK format
        add_debug_log(session_id, "DEBUG", "Trying standard UK format parsing")
        transactions = parse_standard_uk_format(content)
        parsing_details["strategies_tried"].append("standard_uk")
        parsing_details["transactions_per_strategy"]["standard_uk"] = len(transactions)
        
        if transactions:
            parsing_details["strategy_used"] = "standard_uk"
            add_debug_log(session_id, "DEBUG", f"Standard UK format found {len(transactions)} transactions")
        
        # Try Strategy 2: Tabular format
        if not transactions:
            add_debug_log(session_id, "DEBUG", "Trying tabular format parsing")
            transactions = parse_tabular_format(content)
            parsing_details["strategies_tried"].append("tabular")
            parsing_details["transactions_per_strategy"]["tabular"] = len(transactions)
            
            if transactions:
                parsing_details["strategy_used"] = "tabular"
                add_debug_log(session_id, "DEBUG", f"Tabular format found {len(transactions)} transactions")
        
        # Try Strategy 3: Line-by-line
        if not transactions:
            add_debug_log(session_id, "DEBUG", "Trying line-by-line parsing")
            transactions = parse_line_by_line(content)
            parsing_details["strategies_tried"].append("line_by_line")
            parsing_details["transactions_per_strategy"]["line_by_line"] = len(transactions)
            
            if transactions:
                parsing_details["strategy_used"] = "line_by_line"
                add_debug_log(session_id, "DEBUG", f"Line-by-line found {len(transactions)} transactions")
        
        if not transactions:
            add_debug_log(session_id, "WARNING", "No transactions found with any strategy")
            return pd.DataFrame(), parsing_details
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        df = clean_transaction_data(df)
        df = df.sort_values('date').reset_index(drop=True)
        
        add_debug_log(session_id, "DEBUG", f"Final DataFrame created with {len(df)} transactions")
        
        return df, parsing_details
        
    except Exception as e:
        add_debug_log(session_id, "ERROR", f"Parsing error: {str(e)}")
        parsing_details["error"] = str(e)
        raise

@app.get("/download/{session_id}/excel")
async def download_excel(session_id: str):
    """Download Excel file"""
    excel_path = TEMP_DIR / f"{session_id}_transactions.xlsx"
    
    if not excel_path.exists():
        logger.error(f"Excel file not found: {excel_path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"Downloading Excel file for session {session_id}")
    return FileResponse(
        path=str(excel_path),
        filename=f"bank_transactions_{session_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/download/{session_id}/csv")
async def download_csv(session_id: str):
    """Download CSV file"""
    csv_path = TEMP_DIR / f"{session_id}_transactions.csv"
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"Downloading CSV file for session {session_id}")
    return FileResponse(
        path=str(csv_path),
        filename=f"bank_transactions_{session_id}.csv",
        media_type="text/csv"
    )

@app.get("/debug/{session_id}")
async def get_debug_logs(session_id: str):
    """Get debug logs for a session"""
    logs = debug_logs.get(session_id, [])
    return {"session_id": session_id, "logs": logs}

@app.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up temporary files and debug logs for a session"""
    cleanup_temp_files(session_id, TEMP_DIR)
    
    # Clean up debug logs
    if session_id in debug_logs:
        del debug_logs[session_id]
    
    return {"message": "Files and logs cleaned up successfully"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run startup checks"""
    logger.info("Starting Bank Statement Converter API")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    
    # Check dependencies
    try:
        import pytesseract
        tesseract_version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract available: {tesseract_version}")
    except Exception as e:
        logger.error(f"Tesseract not available: {str(e)}")
    
    # Clean old temp files
    for old_file in TEMP_DIR.glob("*"):
        if old_file.is_file():
            try:
                age = time.time() - old_file.stat().st_mtime
                if age > 3600:  # 1 hour old
                    old_file.unlink()
                    logger.debug(f"Cleaned old file: {old_file}")
            except Exception as e:
                logger.warning(f"Could not clean {old_file}: {str(e)}")
    
    logger.info("Startup complete")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    
    # Use INFO level for production
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
        log_level="debug",  # Changed from debug/info
        access_log=True,  # Disable access logs in production or True
    )