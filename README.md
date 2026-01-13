# OVH Complaints Tracker

Real-time monitoring platform that collects and analyzes **customer complaints** and **feedback** about OVH domain services from multiple sources.

## 🎯 Objective

Track genuine customer complaints and feedback about OVH domain services (pricing, support quality, interface usability, renewal issues, etc.) across multiple platforms to identify patterns and pain points.

## 📊 Data Sources

The application collects **real customer feedback** from the following sources:

### ✅ Currently Supported

| Source | Type | Focus | Status |
|--------|------|-------|--------|
| **Trustpilot** | ⭐ Customer Reviews | Real customer ratings and reviews on OVH | Real data |
| **X/Twitter** | 💬 Social Media | Tweets with complaint keywords (bad support, expensive, etc.) | Real data (when available) |
| **GitHub Issues** | 📋 Issue Tracker | Customer experience issues and feature requests | Real data |
| **Stack Overflow** | ❓ Q&A Platform | Customer technical support questions about OVH domains | Real data |
| **Hacker News** | 🔗 Tech Community | Technical discussions from tech community | Real data |
| **Google News** | 📰 News Aggregator | News articles and press coverage about OVH | Real data |

### ❌ Not Supported

- **Reddit**: Anti-scraping measures (403 Forbidden) - would require OAuth2
- **LinkedIn**: Strictly prohibits automated data extraction in ToS
- **Facebook**: No public API - would violate platform terms

## ⚡ Key Features

### Data Collection
- **Manual Scraping**: Click buttons to fetch customer feedback immediately
- **Auto Scraping**: Every 3 hours, automatically collects feedback from all sources
- **Complaint-Focused**: Searches specifically for customer complaints, not generic mentions
- **Real Data Only**: No mock data - if a scraper fails, returns error instead

### Analysis & Filtering
- **Sentiment Analysis**: VADER sentiment analysis (negative/neutral/positive)
- **Multi-Filter Search**: Filter by date, source, sentiment, and keywords
- **Keyword Patterns**: Pre-configured patterns for domain-related issues
  - Domain creation/renewal issues
  - Transfer problems
  - DNS complications
  - Price complaints
  - Support quality issues

### Management
- **Backlog Feature**: Save important complaints for follow-up (localStorage)
- **CSV Export**: Export filtered results for analysis
- **Real-time Logs**: See scraping progress and errors in real-time

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── app/
│   ├── main.py              # FastAPI app, endpoints, scheduler
│   ├── db.py                # SQLite database operations
│   ├── scraper/
│   │   ├── trustpilot.py    # ⭐ Trustpilot reviews (NEW)
│   │   ├── x_scraper.py     # X/Twitter (complaint keywords)
│   │   ├── github.py        # GitHub Issues (customer experience)
│   │   ├── stackoverflow.py  # Stack Overflow Q&A
│   │   ├── hackernews.py    # Hacker News discussions
│   │   └── news.py          # Google News
│   └── analysis/
│       └── sentiment.py      # VADER sentiment analysis
├── requirements.txt         # Python dependencies
└── tests/
    ├── test_complaint_scrapers.py
    └── test_scrapers_qa.py
```

### Frontend (Vanilla JS)
```
frontend/
└── index.html               # Single-page dashboard
    ├── Controls (filters, scraping buttons)
    ├── Stats cards (total posts, sentiment distribution)
    ├── Gallery (card-based post display)
    ├── Backlog (saved items)
    └── Info panel (documentation)
```

### Database
- **SQLite** with post schema: source, author, content, url, created_at, sentiment_score, sentiment_label
- Persistent storage for all collected posts

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd ovh-complaints-tracker
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\Activate.ps1 # Windows PowerShell
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Run Backend

```bash
cd backend
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

### 4. Run Frontend

```bash
cd frontend
python -m http.server 3000
```

### 5. Access Application

Open browser: `http://127.0.0.1:3000/index.html`

## 📋 API Endpoints

```
POST /scrape/trustpilot        # Scrape Trustpilot reviews
POST /scrape/x                 # Scrape X/Twitter (complaint keywords)
POST /scrape/github            # Scrape GitHub Issues
POST /scrape/stackoverflow     # Scrape Stack Overflow
POST /scrape/hackernews        # Scrape Hacker News
POST /scrape/news              # Scrape Google News
GET  /posts?limit=100          # Get all posts from database
```

## 🔍 Search Keywords

Scrapers search for **customer complaint-related keywords**:

### X/Twitter
- "OVH support bad"
- "OVH domain expensive"
- "OVH customer service"
- "OVH renewal overpriced"
- "OVH interface confusing"

### GitHub
- "OVH domain" (customer experience)
- "OVH customer"
- "OVH support"
- "OVH renewal"
- "OVH experience"

### Frontend Keyword Filters
- Domain creation/registration issues
- Domain renewal problems
- Domain transfer complications
- Domain trading/selling
- Domain restoration
- DNS-related issues

## 📊 Sentiment Analysis

Posts are classified using VADER sentiment analysis:
- 🔴 **NEGATIVE** (score < -0.05): Complaints, issues, dissatisfaction
- ⚪ **NEUTRAL** (-0.05 to 0.05): Factual statements, no clear sentiment
- 🟢 **POSITIVE** (score > 0.05): Positive feedback, good experiences

## ⚙️ Technical Stack

- **Backend**: FastAPI, Python 3.13, uvicorn
- **Scrapers**: httpx, snscrape (X), feedparser (RSS)
- **Analysis**: VADER sentiment analysis
- **Database**: SQLite
- **Scheduling**: APScheduler (3-hour auto-scrape)
- **Frontend**: Vanilla JavaScript, localStorage, CSS Grid
- **Sentiment**: VADER (Valence Aware Dictionary and sEntiment Reasoner)

## ⚠️ Important Notes

### Only Real Data
- **No mock data in results** - if a scraper fails, returns 503 error instead
- **Trustpilot, GitHub, Stack Overflow** provide real customer feedback
- **X/Twitter** searches complaint keywords, but snscrape incompatibility with Python 3.13 may cause unavailability
- **Google News** via RSS feeds (subject to rate limiting)

### Rate Limiting
Some APIs have rate limiting:
- GitHub API: 60 requests/hour (unauthenticated)
- Google News: May be rate-limited by Google
- Trustpilot: Rate limiting may apply

### Legal & Ethics
- All scraped data is **publicly available** on social platforms
- Users are responsible for complying with platform Terms of Service
- This tool monitors public feedback only
- No personal data collection - only public posts/reviews

## 🔧 Development

### Test Scrapers

```bash
cd backend
python test_complaint_scrapers.py
python test_scrapers_qa.py
```

### View Logs

Backend logs are printed to console in real-time. Frontend logs appear in browser console.

## 📝 License

MIT License - feel free to use, modify, and distribute
