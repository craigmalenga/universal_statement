# Bank Statement Converter

A minimalistic, production-ready web application that converts uploaded UK bank statement PDFs into structured Excel/CSV files. Similar functionality to bankstatementconverter.com with clean, simple, and reliable processing.

## Features

- **Multi-format Support**: Converts PDFs to both Excel (.xlsx) and CSV formats
- **Smart Recognition**: Handles both digital PDFs (with text layer) and scanned PDFs (image-based) using OCR fallback
- **UK Bank Compatibility**: Supports major UK banks including Barclays, HSBC, NatWest, and more
- **Mobile-Friendly**: Responsive design with drag-and-drop file upload
- **Secure Processing**: Files are automatically deleted after processing
- **Real-time Progress**: Visual progress indicators during conversion

## Project Structure

```
bank-statement-converter/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point and routes
│   │   ├── extraction.py     # PDF text extraction and OCR fallback
│   │   ├── parsing.py        # Transaction parsing with regex and pandas
│   │   ├── export.py         # DataFrame to Excel/CSV export
│   │   └── utils.py          # Helper functions and file cleanup
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile           # Container configuration
├── frontend/
│   ├── pages/
│   │   ├── index.tsx        # Main upload UI
│   │   └── _app.tsx         # Next.js app configuration
│   ├── components/
│   │   ├── FileUpload.tsx   # Drag-and-drop file upload component
│   │   ├── ProgressBar.tsx  # Processing progress indicator
│   │   └── DownloadLink.tsx # Download buttons for results
│   ├── styles/
│   │   └── globals.css      # Global styles with Tailwind
│   ├── package.json         # Node.js dependencies
│   ├── tailwind.config.js   # Tailwind CSS configuration
│   ├── next.config.js       # Next.js configuration
│   └── tsconfig.json        # TypeScript configuration
└── README.md
```

## Tech Stack

### Backend (Python)
- **Framework**: FastAPI for high-performance API
- **PDF Processing**: 
  - pdfplumber & pdfminer.six for text extraction
  - pdf2image & pytesseract for OCR fallback
- **Data Processing**: pandas for transaction parsing and structuring
- **Export**: openpyxl for Excel generation, built-in CSV support
- **Image Processing**: Pillow for OCR preprocessing

### Frontend (React/Next.js)
- **Framework**: Next.js 14 with TypeScript
- **Styling**: TailwindCSS for responsive design
- **Components**: Custom file upload, progress bar, and download components

## Installation & Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Tesseract OCR for scanned PDF processing

#### Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install poppler: Download from https://blog.alivate.com.au/poppler-windows/

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the backend server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file (.env.local):**
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Run the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## Deployment

### Backend Deployment (Railway)

1. **Connect your repository to Railway:**
   - Visit [railway.app](https://railway.app)
   - Create new project from GitHub repository
   - Select the backend folder

2. **Configure environment variables:**
   ```
   PORT=8000
   ```

3. **Railway will automatically:**
   - Build using the Dockerfile
   - Install system dependencies (Tesseract, Poppler)
   - Deploy the FastAPI application

### Frontend Deployment (Vercel)

1. **Connect your repository to Vercel:**
   - Visit [vercel.com](https://vercel.com)
   - Import your repository
   - Set root directory to `frontend`

2. **Configure environment variables:**
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```

3. **Vercel will automatically:**
   - Build the Next.js application
   - Deploy with global CDN
   - Provide custom domain

## API Documentation

### Endpoints

#### `POST /convert`
Convert uploaded PDF to Excel and CSV files.

**Request:**
- Content-Type: multipart/form-data
- Body: PDF file

**Response:**
```json
{
  "session_id": "uuid-string",
  "transactions_count": 45,
  "excel_url": "/download/uuid/excel",
  "csv_url": "/download/uuid/csv"
}
```

#### `GET /download/{session_id}/excel`
Download Excel file for the session.

#### `GET /download/{session_id}/csv`
Download CSV file for the session.

#### `DELETE /cleanup/{session_id}`
Clean up temporary files for the session.

## Processing Pipeline

### 1. PDF Parsing
- **Text Extraction**: Uses pdfplumber for digital PDFs with selectable text
- **OCR Fallback**: Converts pages to images using pdf2image, then applies pytesseract OCR for scanned documents
- **Preprocessing**: Enhances image contrast and sharpness for better OCR accuracy

### 2. Normalization
- Fixes encoding issues and unifies spacing
- Standardizes dates to YYYY-MM-DD format
- Corrects common OCR recognition errors

### 3. Transaction Parsing
- **Multiple Strategies**: Standard UK format, tabular format, and line-by-line parsing
- **Date Recognition**: Supports DD/MM/YYYY, DD MMM YYYY, and other common UK formats
- **Amount Extraction**: Detects debit/credit amounts and running balances
- **Smart Categorization**: Uses context clues and positioning to classify transaction types

### 4. Export Generation
- **Excel Output**: Professional formatting with styled headers, alternating row colors, and proper data types
- **CSV Output**: UTF-8 encoded with BOM for Excel compatibility
- **File Validation**: Verifies output files can be opened correctly

## Supported Banks

The converter works with PDF statements from major UK banks:
- Barclays
- HSBC
- NatWest
- Royal Bank of Scotland
- Santander
- Lloyds Banking Group
- TSB
- First Direct
- And many others

## File Requirements

- **Format**: PDF files only
- **Size Limit**: Maximum 50MB
- **Content**: Both digital PDFs and scanned documents supported
- **Language**: Optimized for UK English bank statements

## Error Handling

The application includes comprehensive error handling:
- Invalid file format detection
- File size validation
- PDF corruption handling
- OCR failure fallbacks
- Network error recovery
- User-friendly error messages

## Security Features

- **No Authentication Required**: Simplified user experience
- **Automatic Cleanup**: Files deleted after processing
- **No Persistent Storage**: All processing done in memory where possible
- **Security Headers**: CSRF protection and secure headers
- **Input Validation**: File type and size restrictions

## Performance

- **Concurrent Processing**: Handles multiple users simultaneously
- **Memory Efficient**: Streaming file processing where possible
- **Fast OCR**: Optimized image preprocessing for speed
- **CDN Delivery**: Frontend served via global CDN (Vercel)

## Development

### Running Tests
```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality
```bash
# Backend linting
cd backend
flake8 app/

# Frontend linting
cd frontend
npm run lint
```

## Troubleshooting

### Common Issues

1. **Tesseract not found**:
   - Ensure Tesseract is installed and in PATH
   - On Windows, add Tesseract installation directory to PATH

2. **PDF processing fails**:
   - Check if PDF is corrupted
   - Verify PDF contains readable text or images
   - Try with different PDF files

3. **OCR produces poor results**:
   - Ensure PDF has good image quality
   - Check if document is rotated correctly
   - Verify language settings match document content

4. **Excel file won't open**:
   - Check if file was completely downloaded
   - Verify Excel version compatibility
   - Try opening with LibreOffice as alternative

### Debug Mode

Enable debug logging:
```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload

# Frontend
export NODE_ENV=development
npm run dev
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Review troubleshooting section above

## Changelog

### v1.0.0
- Initial release
- Support for UK bank statement conversion
- Excel and CSV output formats
- OCR fallback for scanned documents
- Mobile-responsive web interface