# backend/Dockerfile - ENHANCED VERSION WITH CAMELOT AND TABULA
FROM python:3.11-slim

# Install system dependencies for PDF processing, OCR, and table extraction
RUN apt-get update && apt-get install -y \
    # OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    # Java for Tabula
    default-jre \
    # Ghostscript for Camelot
    ghostscript \
    # OpenCV dependencies for Camelot
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgcc-s1 \
    libxcb1 \
    # Python tk for Camelot (sometimes needed)
    python3-tk \
    # Network tools
    curl \
    wget \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Verify Java installation (for debugging)
RUN java -version

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with better error handling
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "Initial install failed, trying without optional dependencies" && \
     pip install --no-cache-dir fastapi uvicorn[standard] python-multipart pdfplumber pdf2image pytesseract pandas openpyxl Pillow psutil && \
     pip install --no-cache-dir tabula-py || echo "Tabula install failed" && \
     pip install --no-cache-dir camelot-py[cv] || pip install --no-cache-dir camelot-py || echo "Camelot install failed")

# Copy application code
COPY . .

# Create temp directory
RUN mkdir -p temp_files

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# Set Java home for Tabula
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Expose port (Railway will override this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]