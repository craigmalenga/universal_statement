# backend/app/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import uuid
from pathlib import Path
import logging

from .extraction import extract_pdf_content
from .parsing import parse_transactions
from .export import export_to_files
from .utils import cleanup_temp_files

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bank Statement Converter", version="1.0.0")

# Configure CORS for Railway deployment
cors_origins = [
    "http://localhost:3000",  # Local development
    "https://localhost:3000", # Local development with HTTPS
]

# Add Railway domains dynamically
import os
railway_frontend_url = os.getenv("FRONTEND_URL")  # Set this in Railway env vars
if railway_frontend_url:
    cors_origins.append(railway_frontend_url)

# Also allow Railway's generated domains
cors_origins.extend([
    "https://*.railway.app",  # All Railway subdomains
    "https://*.up.railway.app",  # Railway's new domain format
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create temp directory for processing
TEMP_DIR = Path("temp_files")
TEMP_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Bank Statement Converter API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/convert")
async def convert_bank_statement(file: UploadFile = File(...)):
    """
    Convert uploaded PDF bank statement to Excel and CSV format
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    temp_pdf_path = TEMP_DIR / f"{session_id}_input.pdf"
    
    try:
        # Save uploaded file temporarily
        with open(temp_pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"Processing file: {file.filename} (Session: {session_id})")
        
        # Extract content from PDF
        raw_content = extract_pdf_content(str(temp_pdf_path))
        
        if not raw_content.strip():
            raise HTTPException(status_code=400, detail="Could not extract any content from the PDF")
        
        # Parse transactions
        transactions_df = parse_transactions(raw_content)
        
        if transactions_df.empty:
            raise HTTPException(status_code=400, detail="No transactions found in the PDF")
        
        # Export to Excel and CSV
        excel_path, csv_path = export_to_files(transactions_df, session_id, TEMP_DIR)
        
        logger.info(f"Successfully processed {len(transactions_df)} transactions")
        
        return {
            "session_id": session_id,
            "transactions_count": len(transactions_df),
            "excel_url": f"/download/{session_id}/excel",
            "csv_url": f"/download/{session_id}/csv"
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        cleanup_temp_files(session_id, TEMP_DIR)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/download/{session_id}/excel")
async def download_excel(session_id: str):
    """Download Excel file"""
    excel_path = TEMP_DIR / f"{session_id}_transactions.xlsx"
    
    if not excel_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
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
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(csv_path),
        filename=f"bank_transactions_{session_id}.csv",
        media_type="text/csv"
    )

@app.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """Clean up temporary files for a session"""
    cleanup_temp_files(session_id, TEMP_DIR)
    return {"message": "Files cleaned up successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)