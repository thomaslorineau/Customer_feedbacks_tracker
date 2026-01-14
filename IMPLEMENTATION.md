# Implementation Guide - OVH Customer Feedback Tracker

This guide provides step-by-step instructions for setting up and deploying the OVH Customer Feedback Tracker.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)
6. [Screenshots](#screenshots)

## Prerequisites

### Required Software

- **Python 3.11 or 3.12** (Python 3.13 has compatibility issues with some dependencies)
- **Git** for cloning the repository
- **Modern web browser** (Chrome, Firefox, Edge, Safari)
- **Internet connection** (for scraping data)

### Optional Software

- **Docker** (for containerized deployment)
- **Nginx** or **Apache** (for production reverse proxy)
- **PostgreSQL** (for production database, SQLite is used by default)

## Local Development Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/thomaslorineau/complaints_tracker.git
cd complaints_tracker
```

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables (Optional)

Create a `.env` file in the `backend/` directory:

```bash
# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# LLM Configuration (for AI idea generation)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Or use Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Trustpilot API (optional, for better scraping)
TRUSTPILOT_API_KEY=your_trustpilot_api_key_here
```

### Step 5: Initialize Database

The database will be automatically created on first run. To manually initialize:

```bash
cd backend
python -c "from app.db import init_db; init_db()"
```

### Step 6: Start Backend Server

**Option 1: Using Python directly**
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Option 2: Using the provided script (Windows)**
```powershell
cd backend
.\start_server.ps1
```

**Option 3: Using Python module**
```bash
cd backend
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

The backend should now be running at `http://127.0.0.1:8000`

### Step 7: Start Frontend Server

**Option 1: Using Python HTTP Server**
```bash
cd frontend
python -m http.server 3000
```

**Option 2: Using Node.js (if installed)**
```bash
cd frontend
npx http-server -p 3000
```

**Option 3: Open directly in browser**
Simply open `frontend/index.html` in your browser (some features may not work due to CORS)

### Step 8: Access the Application

Open your browser and navigate to:
- **Frontend**: `http://localhost:3000/index.html`
- **API Docs**: `http://127.0.0.1:8000/docs` (Swagger UI)
- **API Alternative**: `http://127.0.0.1:8000/redoc` (ReDoc)

## Production Deployment

### Option 1: Docker Deployment

**Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
docker build -t ovh-feedback-tracker .
docker run -p 8000:8000 -v $(pwd)/backend/data.db:/app/backend/data.db ovh-feedback-tracker
```

### Option 2: Systemd Service (Linux)

**Create service file** `/etc/systemd/system/ovh-tracker.service`:

```ini
[Unit]
Description=OVH Customer Feedback Tracker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ovh-tracker/backend
Environment="PATH=/opt/ovh-tracker/venv/bin"
ExecStart=/opt/ovh-tracker/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable ovh-tracker
sudo systemctl start ovh-tracker
```

### Option 3: Nginx Reverse Proxy

**Nginx configuration** `/etc/nginx/sites-available/ovh-tracker`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /opt/ovh-tracker/frontend;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Configuration

### Database Configuration

By default, the application uses SQLite (`backend/data.db`). For production, consider PostgreSQL:

1. Install PostgreSQL and create database
2. Update `backend/app/db.py` to use PostgreSQL connection
3. Update connection string in environment variables

### Scraper Configuration

Scrapers can be configured via environment variables or by modifying scraper files directly.

**Rate Limiting:**
- Each scraper has built-in delays to respect rate limits
- Adjust delays in `backend/app/scraper/anti_bot_helpers.py`

**Anti-Bot Protection:**
- The application includes anti-bot helpers for sites with protection
- For JavaScript-heavy sites, install Playwright:
  ```bash
  pip install playwright
  playwright install chromium
  ```

### Scheduler Configuration

The automatic scraping job runs every 3 hours by default. To change:

Edit `backend/app/main.py`:
```python
scheduler.add_job(
    auto_scrape_job,
    'interval',
    hours=3,  # Change this value
    id='auto_scrape'
)
```

## Troubleshooting

### Backend Won't Start

1. **Check Python version:**
   ```bash
   python --version  # Should be 3.11 or 3.12
   ```

2. **Check dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Check port availability:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

4. **Check logs:**
   Look for error messages in console output

### Scrapers Return No Data

1. **Check internet connection**
2. **Check rate limits** - Wait a few minutes and try again
3. **Check logs** - Look for error messages in the logs panel
4. **Test individual scrapers:**
   ```bash
   cd backend
   python test_scrapers_qa.py
   ```

### CORS Errors

1. **Check CORS_ORIGINS** environment variable
2. **Ensure frontend URL is in allowed origins**
3. **Default ports:** Frontend should run on 3000 or 8080

### Database Errors

1. **Check file permissions** - Ensure write access to `backend/data.db`
2. **Check disk space**
3. **Reset database** - Delete `backend/data.db` to start fresh (loses all data)

## Screenshots

To add screenshots to the repository:

1. **Create screenshots directory:**
   ```bash
   mkdir docs/screenshots
   ```

2. **Take screenshots of key features:**
   - Main dashboard
   - Statistics modal (timeline & histogram)
   - Backlog sidebar
   - Post preview modal
   - Filtering interface
   - Export functionality

3. **Recommended screenshot names:**
   - `01-main-dashboard.png`
   - `02-statistics-modal.png`
   - `03-backlog-sidebar.png`
   - `04-post-preview.png`
   - `05-filtering.png`
   - `06-export.png`
   - `07-light-mode.png`
   - `08-dark-mode.png`

4. **Add to README.md:**
   ```markdown
   ## Screenshots
   
   ![Main Dashboard](docs/screenshots/01-main-dashboard.png)
   ![Statistics](docs/screenshots/02-statistics-modal.png)
   ```

5. **Optimize images:**
   - Use PNG format for UI screenshots
   - Compress images to reduce file size
   - Recommended max size: 1920x1080

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md) - Detailed system architecture
- [Test Guide](GUIDE_TEST.md) - How to test the application
- [Anti-Bot Guide](backend/ANTI_BOT_GUIDE.md) - Techniques for bypassing anti-scraping protection
- [API Documentation](http://127.0.0.1:8000/docs) - Interactive API documentation (when server is running)

## Support

For issues, questions, or contributions:
1. Check existing issues on GitHub
2. Create a new issue with detailed description
3. Include error logs and system information

