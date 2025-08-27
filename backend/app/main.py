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
import pandas as pd
import numpy as np
from decimal import Decimal

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



def safe_json_convert(obj):
    """Convert numpy/pandas types to JSON-serializable types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif obj is None or pd.isna(obj):
        return None
    else:
        return str(obj)

@app.post("/convert")
async def convert_bank_statement(
    file: UploadFile = File(...),
    debug: bool = False
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
            
            # Return simple JSON response
            return {
                "error": True,
                "message": error_msg,
                "session_id": session_id,
                "debug_logs": debug_logs.get(session_id, []) if debug else None
            }
        
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
            
            # Return simple error response
            return {
                "error": True,
                "message": error_msg,
                "session_id": session_id,
                "debug_logs": debug_logs.get(session_id, []) if debug else None,
                "raw_content_preview": raw_content[:2000] if debug and raw_content else None
            }
        
        # Export to Excel and CSV
        if debug:
            add_debug_log(session_id, "INFO", "Starting export to Excel and CSV")
        
        excel_path, csv_path = export_to_files(transactions_df, session_id, TEMP_DIR)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        logger.info(f"Conversion completed for session {session_id}: {len(transactions_df)} transactions in {processing_time:.2f}s")
        
        # Prepare BASIC response first
        response_data = {
            "session_id": session_id,
            "transactions_count": int(len(transactions_df)),  # Ensure it's a Python int
            "excel_url": f"/download/{session_id}/excel",
            "csv_url": f"/download/{session_id}/csv",
            "processing_time": round(float(processing_time), 2),  # Ensure it's a Python float
            "success": True
        }
        
        # Add debug information SAFELY
        if debug:
            try:
                # Convert sample transactions safely
                sample_transactions = []
                if not transactions_df.empty:
                    sample_df = transactions_df.head(5).copy()
                    
                    # Convert DataFrame to records
                    records = sample_df.to_dict('records')
                    
                    # Ensure all values are JSON-serializable
                    for record in records:
                        safe_record = {}
                        for key, value in record.items():
                            safe_record[key] = safe_json_convert(value)
                        sample_transactions.append(safe_record)
                
                # Add debug info
                response_data["debug_logs"] = debug_logs.get(session_id, [])
                response_data["raw_content_preview"] = raw_content[:2000] if raw_content else None
                response_data["sample_transactions"] = sample_transactions
                
                # Only add details if they're safe
                if extraction_details and isinstance(extraction_details, dict):
                    response_data["extraction_details"] = extraction_details
                if parsing_details and isinstance(parsing_details, dict):
                    response_data["parsing_details"] = parsing_details
                    
            except Exception as e:
                logger.error(f"Error preparing debug data: {str(e)}")
                # Don't add debug data if it fails
                response_data["debug_error"] = "Failed to prepare debug data"
        
        # Return the response directly (FastAPI will handle JSON conversion)
        return response_data
        
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        logger.error(f"Error in session {session_id}: {error_msg}\n{traceback.format_exc()}")
        
        if debug:
            add_debug_log(session_id, "ERROR", error_msg, {
                "error_type": type(e).__name__
            })
        
        # Clean up on error
        cleanup_temp_files(session_id, TEMP_DIR)
        
        # Return simple error response
        return {
            "error": True,
            "message": error_msg,
            "session_id": session_id,
            "debug_logs": debug_logs.get(session_id, []) if debug else None
        }



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
    """Enhanced parsing with debugging info - MUCH SIMPLER!"""
    from .parsing import parse_transactions  # Only need this one import now!
    import pandas as pd
    
    parsing_details = {
        "strategy_used": "universal_parser",
        "strategies_tried": ["comprehensive"],
        "transactions_per_strategy": {}
    }
    
    try:
        # Use the new universal parser - it handles everything!
        add_debug_log(session_id, "DEBUG", "Starting universal transaction parsing")
        
        transactions_df = parse_transactions(raw_content)
        
        parsing_details["transactions_per_strategy"]["universal"] = len(transactions_df)
        
        if not transactions_df.empty:
            add_debug_log(session_id, "DEBUG", f"Universal parser found {len(transactions_df)} transactions")
            parsing_details["strategy_used"] = "universal_parser"
        else:
            add_debug_log(session_id, "WARNING", "No transactions found with universal parser")
        
        return transactions_df, parsing_details
        
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

# Add this to your main.py for debugging

@app.post("/test-extraction")
async def test_extraction(file: UploadFile = File(...)):
    """
    Test extraction and parsing - returns detailed analysis
    """
    session_id = str(uuid.uuid4())
    temp_pdf_path = TEMP_DIR / f"{session_id}_input.pdf"
    
    try:
        # Save uploaded file
        content = await file.read()
        with open(temp_pdf_path, "wb") as f:
            f.write(content)
        
        # Try different extraction methods
        results = {
            "session_id": session_id,
            "filename": file.filename,
            "extraction_methods": {}
        }
        
        # Method 1: PDFPlumber text extraction
        try:
            import pdfplumber
            text_lines = []
            with pdfplumber.open(temp_pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            if line.strip():
                                text_lines.append({
                                    'page': page_num + 1,
                                    'line': line.strip()
                                })
            
            results["extraction_methods"]["pdfplumber"] = {
                "success": True,
                "total_lines": len(text_lines),
                "sample_lines": text_lines[:50],  # First 50 lines
                "lines_with_dates": sum(1 for l in text_lines if re.search(r'\d{2}/\d{2}/\d{4}', l['line'])),
                "lines_with_amounts": sum(1 for l in text_lines if re.search(r'£?\d+\.\d{2}', l['line']))
            }
        except Exception as e:
            results["extraction_methods"]["pdfplumber"] = {
                "success": False,
                "error": str(e)
            }
        
        # Method 2: Try table extraction with pdfplumber
        try:
            import pdfplumber
            all_tables = []
            with pdfplumber.open(temp_pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            all_tables.append({
                                'page': page_num + 1,
                                'rows': len(table),
                                'cols': len(table[0]) if table else 0,
                                'sample': table[:5] if len(table) > 5 else table
                            })
            
            results["extraction_methods"]["pdfplumber_tables"] = {
                "success": True,
                "tables_found": len(all_tables),
                "table_info": all_tables
            }
        except Exception as e:
            results["extraction_methods"]["pdfplumber_tables"] = {
                "success": False,
                "error": str(e)
            }
        
        # Now test parsing
        from .parsing import parse_transactions, extract_all_transaction_lines, preprocess_content
        
        # Get the best extracted content
        raw_content = ""
        if results["extraction_methods"].get("pdfplumber", {}).get("success"):
            raw_content = '\n'.join([l['line'] for l in text_lines])
        
        if raw_content:
            # Preprocess
            processed_content = preprocess_content(raw_content)
            
            # Try extraction
            transactions = extract_all_transaction_lines(processed_content)
            
            results["parsing_results"] = {
                "raw_content_length": len(raw_content),
                "processed_content_length": len(processed_content),
                "transactions_found": len(transactions),
                "sample_transactions": transactions[:10] if transactions else [],
                "content_preview": processed_content[:1000]  # First 1000 chars
            }
            
            # Try full parsing
            df = parse_transactions(raw_content)
            if not df.empty:
                results["dataframe_results"] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample_data": df.head(10).to_dict('records')
                }
        
        # Save detailed results to file
        output_file = TEMP_DIR / f"{session_id}_debug.json"
        with open(output_file, 'w') as f:
            import json
            json.dump(results, f, indent=2, default=str)
        
        return JSONResponse(content=results)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()}
        )
    finally:
        # Cleanup
        if temp_pdf_path.exists():
            temp_pdf_path.unlink()


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