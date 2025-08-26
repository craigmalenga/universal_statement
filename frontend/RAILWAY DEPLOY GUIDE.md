# Deploy Bank Statement Converter on Railway (Complete Guide)

## 🚂 Railway-Only Deployment (Recommended)

Host both backend and frontend on Railway for simplified management and deployment.

### Step 1: Prepare Your Repository

Make sure your repository has this structure:
```
bank-statement-converter/
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/
│   ├── components/
│   ├── package.json
│   └── next.config.js
└── README.md
```

### Step 2: Deploy Backend Service

1. **Create Railway Project:**
   - Go to [railway.app](https://railway.app)
   - Sign up/login with GitHub
   - Click "New Project"
   - Select "Deploy from GitHub repo"

2. **Configure Backend Service:**
   - Choose your repository
   - Railway will ask for root directory → Enter: `backend`
   - Railway auto-detects Dockerfile and starts deployment
   - Wait for deployment to complete

3. **Get Backend URL:**
   - In Railway dashboard, click on your backend service
   - Copy the public URL (looks like: `https://backend-production-xxxx.railway.app`)

### Step 3: Deploy Frontend Service

1. **Add Frontend Service:**
   - In the same Railway project, click "Add Service"
   - Select "GitHub Repo" (same repository)
   - Set root directory to: `frontend`

2. **Configure Environment Variables:**
   - Click on your frontend service
   - Go to "Variables" tab
   - Add: `NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app`

3. **Deploy Frontend:**
   - Railway auto-detects Next.js and builds/deploys
   - Get your frontend URL from the service dashboard

### Step 4: Update CORS Settings

Update your backend's main.py to allow your frontend domain:

```python
# In backend/app/main.py - update CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "https://your-frontend-name.railway.app"  # Add your Railway frontend URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 5: Test the Application

1. Visit your frontend Railway URL
2. Upload a test PDF bank statement
3. Verify conversion works and downloads are successful

## Alternative: Single Service Deployment

If you prefer everything in one service, create a simple Docker setup:

```dockerfile
# Dockerfile (place in project root)
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package.json ./frontend/

# Install frontend dependencies (for runtime)
WORKDIR /app/frontend
RUN npm ci --production

WORKDIR /app
EXPOSE 8000

# Start both services (you'd need a process manager like supervisord)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

But the **separate services approach is cleaner and more maintainable**.

## Railway Benefits

✅ **Auto-scaling**: Railway handles traffic spikes  
✅ **Built-in CI/CD**: Auto-deploy on git push  
✅ **Free tier**: Good for testing and low traffic  
✅ **Custom domains**: Add your own domain easily  
✅ **Environment management**: Easy env var updates  
✅ **Logs & monitoring**: Built-in logging and metrics  

## Cost Comparison

| Platform | Backend | Frontend | Total/Month |
|----------|---------|----------|-------------|
| Railway Only | $5-20 | $5-15 | $10-35 |
| Railway + Vercel | $5-20 | $0-20 | $5-40 |

Railway-only is often cheaper and definitely simpler to manage!

## Troubleshooting

**If frontend can't reach backend:**
1. Check `NEXT_PUBLIC_API_URL` environment variable
2. Verify CORS settings in backend
3. Ensure both services are deployed and running

**If OCR fails:**
1. Railway's Dockerfile includes Tesseract installation
2. Check Railway logs for any missing dependencies
3. Verify PDF file is valid and not corrupted

**For Railway-specific issues:**
1. Check Railway status page
2. Review deployment logs in Railway dashboard
3. Use Railway CLI for debugging: `railway logs`