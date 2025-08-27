# backend/Dockerfile - FIXED FOR DEBIAN COMPATIBILITY
FROM python:3.11-slim

# Install system dependencies for PDF processing, OCR, and table extraction
RUN apt-get update && apt-get install -y \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    # Java for Tabula (if available)
    default-jre || echo "Java not available, Tabula will not work" \
    # Ghostscript for Camelot
    ghostscript \
    # OpenCV/Graphics dependencies (using available packages)
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libxcb1 \
    # Network tools
    curl \
    wget \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "Some packages failed, installing core dependencies only" && \
     pip install --no-cache-dir \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        python-multipart==0.0.6 \
        pdfplumber==0.10.3 \
        pdf2image==1.16.3 \
        pytesseract==0.3.10 \
        pandas==2.1.4 \
        openpyxl==3.1.2 \
        Pillow==10.1.0 \
        psutil==5.9.6)

# Try to install optional table extraction libraries
RUN pip install --no-cache-dir tabula-py==2.9.0 || echo "Tabula not installed" && \
    pip install --no-cache-dir camelot-py[cv] || \
    pip install --no-cache-dir camelot-py || \
    echo "Camelot not installed"

# Copy application code
COPY . .

# Create temp directory
RUN mkdir -p temp_files

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (Railway will override this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]