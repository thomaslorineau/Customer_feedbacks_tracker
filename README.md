# OVH Customer Feedback Tracker

Real-time monitoring platform that collects and analyzes **customer feedback** and **complaints** about all OVH products from multiple sources. Track sentiment, identify improvement opportunities, and generate actionable product enhancement ideas using AI.

## 🎯 Objective

Track genuine customer feedback and complaints about all OVH products (domains, VPS, hosting, cloud, billing, support, etc.) across multiple platforms to identify patterns, pain points, and opportunities for product improvement.

## 📊 Data Sources

The application collects **real customer feedback** from the following sources:

### ✅ Currently Supported

| Source | Type | Focus | Status |
|--------|------|-------|--------|
| **Trustpilot** | ⭐ Customer Reviews | Real customer ratings and reviews on OVH | Real data |
| **X/Twitter** | 💬 Social Media | Tweets with complaint keywords (bad support, expensive, etc.) | Real data (when available) |
| **GitHub Issues** | 📋 Issue Tracker | Customer experience issues and feature requests | Real data |
| **Stack Overflow** | ❓ Q&A Platform | Customer technical support questions about OVH | Real data |
| **Reddit** | 🔗 Social Community | Reddit discussions and posts about OVH products | Real data (RSS feeds) |
| **Google News** | 📰 News Aggregator | News articles and press coverage about OVH | Real data |
| **OVH Forum** | 💬 Community Forum | Official OVH Community Forum discussions | Real data |
| **Mastodon** | 🐘 Social Network | Mastodon posts about OVH products | Real data |
| **G2 Crowd** | ⭐ Review Platform | B2B software reviews and ratings | Real data |

### ❌ Not Supported

- **Hacker News**: Decommissioned (not relevant for customer feedback)
- **LinkedIn**: Strictly prohibits automated data extraction in ToS
- **Facebook**: No public API - would violate platform terms

### 🛡️ Anti-Bot Protection

The application includes advanced anti-bot techniques:
- **Realistic headers** with rotating User-Agents
- **Human-like delays** between requests
- **Stealth sessions** with retry strategies
- **Selenium/Playwright support** for JavaScript-heavy sites (optional)
- See [Anti-Bot Guide](backend/ANTI_BOT_GUIDE.md) for details

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

### Management & Analysis
- **Backlog Sidebar**: Dedicated side panel for managing posts to review
  - Card view and compact list view
  - Comments/notes for each post
  - Export to CSV with comments
- **Product Labeling**: Automatic detection of OVH products (Domain, VPS, Hosting, etc.)
  - Manual override for incorrect labels
  - Persistent storage in localStorage
- **AI-Powered Idea Generation**: Generate product improvement ideas using LLM
  - Supports OpenAI and Anthropic APIs
  - Rule-based fallback when LLM unavailable
  - Validation modal to accept/reject ideas
- **Statistics & Analysis**: Visual analysis of posts over time
  - Timeline & Histogram with sentiment filtering
  - Filter by sentiment, product, and date range
  - Group by day/week/month
  - Pie chart showing distribution by product
- **Post Preview Modal**: View full post content without leaving the page
- **Light/Dark Mode**: Toggle between themes with improved contrast
- **CSV Export**: Export filtered results and backlog with comments
- **Real-time Logs**: See scraping progress and errors in real-time

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── app/
│   ├── main.py              # FastAPI app, endpoints, scheduler
│   ├── db.py                # SQLite database operations
│   ├── scraper/
│   │   ├── trustpilot.py    # ⭐ Trustpilot reviews
│   │   ├── x_scraper.py     # X/Twitter (complaint keywords)
│   │   ├── github.py        # GitHub Issues (customer experience)
│   │   ├── stackoverflow.py  # Stack Overflow Q&A
│   │   ├── reddit.py        # Reddit RSS feeds
│   │   ├── news.py          # Google News
│   │   ├── ovh_forum.py     # OVH Community Forum
│   │   ├── mastodon.py      # Mastodon social network
│   │   ├── g2_crowd.py      # G2 Crowd reviews
│   │   ├── anti_bot_helpers.py  # Anti-bot protection utilities
│   │   └── selenium_helper.py  # Browser automation (optional)
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

### Prerequisites

- **Python 3.11 or 3.12** (Python 3.13 has compatibility issues with snscrape)
- **Git** (for cloning the repository)
- Internet connection (for scraping)
- Modern web browser

### Installation Options

**Option 1: Automatic Installation (Recommended for Linux VMs)**

```bash
# Download and run the installation script
curl -O https://raw.githubusercontent.com/thomaslorineau/complaints_tracker/master/install.sh
chmod +x install.sh
./install.sh
```

The script will automatically:
- ✅ Check Python and Git installation
- ✅ Download the application
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Configure the application
- ✅ Configure port (8000 default, or custom for Docker OVH)
- ✅ Configure CORS automatically
- ✅ Detect hostname via reverse DNS for public IP

Then start the application:
```bash
./start.sh
```

The application will display all access URLs (local network, Internet with hostname, etc.)

**Option 2: Manual Installation**

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

### 3. Configure Environment Variables (Optional)

Create a `.env` file in the `backend/` directory or set environment variables:

```bash
# Trustpilot API key (optional, for better scraping)
TRUSTPILOT_API_KEY=your_api_key_here

# CORS origins (optional, defaults to localhost:3000, localhost:8080)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# LLM API for idea generation (optional)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # Optional, defaults to gpt-4o-mini

# Or use Anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-3-haiku-20240307  # Optional
```

### 4. Run Backend

```bash
cd backend
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

Or use the provided script:
```bash
python start_backend.py
```

### 5. Run Frontend

```bash
cd frontend
python -m http.server 3000
```

### 6. Access Application

Open browser: `http://localhost:3000/index.html`

## 📋 API Endpoints

```
POST /scrape/trustpilot              # Scrape Trustpilot reviews
POST /scrape/x                       # Scrape X/Twitter (complaint keywords)
POST /scrape/github                  # Scrape GitHub Issues
POST /scrape/stackoverflow            # Scrape Stack Overflow
POST /scrape/reddit                  # Scrape Reddit RSS feeds
POST /scrape/news                    # Scrape Google News
POST /scrape/ovh-forum               # Scrape OVH Community Forum
POST /scrape/mastodon                # Scrape Mastodon posts
POST /scrape/g2-crowd                # Scrape G2 Crowd reviews
POST /generate-improvement-ideas     # Generate product improvement ideas (LLM)
POST /admin/cleanup-duplicates       # Remove duplicate posts
POST /admin/cleanup-hackernews-posts # Remove Hacker News posts
GET  /posts?limit=100                # Get all posts from database
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

- **Backend**: FastAPI, Python 3.11/3.12, uvicorn
- **Scrapers**: httpx, feedparser (RSS), BeautifulSoup (HTML parsing)
- **Analysis**: VADER sentiment analysis
- **Database**: SQLite with indexes for performance
- **Scheduling**: APScheduler (3-hour auto-scrape)
- **Frontend**: Vanilla JavaScript, localStorage, CSS Grid
- **Sentiment**: VADER (Valence Aware Dictionary and sEntiment Reasoner)

**Note**: Python 3.13 is not recommended due to snscrape incompatibility. The X/Twitter scraper uses Nitter instances as an alternative.

## ⚠️ Important Notes

### Only Real Data
- **No mock data in results** - if a scraper fails, returns empty list instead of sample data
- **Trustpilot, GitHub, Stack Overflow** provide real customer feedback
- **X/Twitter** uses Nitter instances (Python 3.13 compatible alternative to snscrape)
- **Google News** via RSS feeds (subject to rate limiting)
- **Duplicate Detection**: Posts with the same URL are automatically skipped

### Rate Limiting
Some APIs have rate limiting:
- GitHub API: 60 requests/hour (unauthenticated)
- Google News: May be rate-limited by Google
- Trustpilot: Rate limiting may apply
- Nitter instances: May have rate limits

### Database Features
- **Automatic duplicate detection** based on URL
- **Indexed columns** for fast filtering (source, sentiment, date, language)
- **Job persistence** for background scraping tasks

### Legal & Ethics
- All scraped data is **publicly available** on social platforms
- Users are responsible for complying with platform Terms of Service
- This tool monitors public feedback only
- No personal data collection - only public posts/reviews

## 🔧 Known Issues

### Python Version Compatibility
- **Python 3.13**: Not fully supported due to snscrape incompatibility. Use Python 3.11 or 3.12.
- **X/Twitter Scraper**: Uses Nitter instances as fallback when snscrape is unavailable

### Scraper Limitations
- **X/Twitter**: Relies on public Nitter instances which may be unstable
- **Trustpilot**: HTML scraping may break if Trustpilot changes their page structure
- **Reddit**: RSS feeds may have rate limits
- **Rate Limiting**: Some sources may temporarily block requests if too many are made
- **LLM API**: Idea generation requires API key (OpenAI or Anthropic). Falls back to rule-based generation if unavailable.

### Database
- SQLite is used for simplicity, but may not scale well beyond ~100k posts
- Consider migrating to PostgreSQL for production use

## 🐛 Troubleshooting

### Backend won't start
- **Check Python version**: `python --version` should be 3.11 or 3.12
- **Check dependencies**: `pip install -r backend/requirements.txt`
- **Check port availability**: Port 8000 must be free
- **Check logs**: Look for error messages in console output

### Scrapers return no data
- **Check internet connection**: Scrapers require internet access
- **Check rate limits**: Wait a few minutes and try again
- **Check logs**: Look for error messages in the logs panel
- **X/Twitter**: Nitter instances may be down, try again later

### CORS errors in browser
- **CORS is configured automatically** during installation
- The frontend automatically detects the backend URL (no manual configuration needed)
- If issues persist, run: `./configure_cors.sh`

### Database errors
- **Check file permissions**: Ensure write access to `backend/data.db`
- **Check disk space**: SQLite needs disk space for the database file
- **Reset database**: Delete `backend/data.db` to start fresh (loses all data)

### Frontend not loading
- **Check backend is running**: Use `./status.sh` to verify
- **Check browser console**: Look for JavaScript errors
- **Frontend auto-detects backend URL**: No manual configuration needed
- **Check port**: Ensure the port matches your configuration (see `backend/.app_config`)

## 🔧 Development

### Test Scrapers

```bash
cd backend
python test_complaint_scrapers.py
python test_scrapers_qa.py
```

### View Logs

Backend logs are printed to console in real-time. Frontend logs appear in browser console.

## 🌍 Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TRUSTPILOT_API_KEY` | Trustpilot API key for better scraping | None | No |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins | `http://localhost:3000,http://localhost:8080,...` | No |
| `OPENAI_API_KEY` | OpenAI API key for LLM idea generation | None | No |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` | No |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM idea generation | None | No |
| `LLM_PROVIDER` | LLM provider: `openai` or `anthropic` | `openai` | No |
| `ANTHROPIC_MODEL` | Anthropic model to use | `claude-3-haiku-20240307` | No |

## 📝 License

MIT License - feel free to use, modify, and distribute

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📚 Additional Resources

- [Architecture Documentation](ARCHITECTURE.md) - Detailed system architecture
- [Test Guide](GUIDE_TEST.md) - How to test the application
- [Implementation Guide](IMPLEMENTATION.md) - Step-by-step setup and deployment guide
- [Anti-Bot Guide](backend/ANTI_BOT_GUIDE.md) - Techniques for bypassing anti-scraping protection
- [Audit Report](AUDIT.md) - Security and code quality audit (may be outdated)

## 📸 Screenshots

Screenshots of the application can be added to the `docs/screenshots/` directory to showcase key features.
