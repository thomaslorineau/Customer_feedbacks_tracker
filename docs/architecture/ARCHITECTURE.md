# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Frontend (Browser)                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Multi-Page Frontend Application                                      │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  /scraping (Scraping & Configuration)                         │ │   │
│  │  │  ├─ Keywords configuration                                     │ │   │
│  │  │  ├─ LLM configuration (OpenAI/Anthropic)                       │ │   │
│  │  │  ├─ Scraping controls & job management                         │ │   │
│  │  │  ├─ Statistics dashboard                                       │ │   │
│  │  │  ├─ Filters & Search                                           │ │   │
│  │  │  └─ Posts Gallery                                              │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  /dashboard (Dashboard Analytics)                              │ │   │
│  │  │  ├─ What's Happening (alerts, insights, recommended actions)  │ │   │
│  │  │  ├─ Timeline & Histogram (interactive charts)                  │ │   │
│  │  │  ├─ Distribution per Product                                   │ │   │
│  │  │  ├─ Posts to Address (critical & recent)                       │ │   │
│  │  │  └─ Advanced filtering (search, sentiment, product, date)      │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐ │   │
│  │  │  /improvements (Improvements Opportunities)                    │ │   │
│  │  │  ├─ Recurring Pain Points (top 5, last 30 days)               │ │   │
│  │  │  ├─ Product Distribution (opportunity scores)                 │ │   │
│  │  │  └─ Posts to Review (ranked by opportunity score)              │ │   │
│  │  └────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                      │   │
│  │  Navigation: Menu with theme toggle, consistent across all pages    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ HTTP GET /posts                         │
│                                    │ HTTP POST /scrape/trustpilot            │
│                                    │ HTTP POST /scrape/x                     │
│                                    │ HTTP POST /scrape/github                │
│                                    │ HTTP POST /scrape/stackoverflow         │
│                                    │ HTTP POST /scrape/reddit                │
│                                    │ HTTP POST /scrape/news                  │
│                                    │ HTTP POST /scrape/ovh-forum            │
│                                    │ HTTP POST /scrape/mastodon             │
│                                    │ HTTP POST /scrape/g2-crowd             │
│                                    ▼                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ localhost:8000
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + APScheduler)                          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  main.py (FastAPI App + Scheduler)                                   │   │
│  │                                                                      │   │
│  │  HTTP Routes:                                                        │   │
│  │  ├─ POST /scrape/trustpilot         ──┐                              │   │
│  │  ├─ POST /scrape/x                  ──┼─► Scraper Router            │   │
│  │  ├─ POST /scrape/github             ──┤    (Real data only)         │   │
│  │  ├─ POST /scrape/stackoverflow      ──┤                             │   │
│  │  ├─ POST /scrape/reddit             ──┤                             │   │
│  │  ├─ POST /scrape/news               ──┤                             │   │
│  │  ├─ POST /scrape/ovh-forum          ──┤                             │   │
│  │  ├─ POST /scrape/mastodon           ──┤                             │   │
│  │  ├─ POST /scrape/g2-crowd           ──┘                             │   │
│  │  ├─ POST /scrape/keywords           ──► Background Job System       │   │
│  │  ├─ GET  /scrape/jobs/{job_id}     ──► Job Status                   │   │
│  │  ├─ POST /api/recommended-actions   ──► LLM Recommended Actions      │   │
│  │  ├─ POST /generate-improvement-ideas─► LLM Idea Generation          │   │
│  │  ├─ GET  /api/pain-points          ──► Pain Points Analysis        │   │
│  │  ├─ GET  /api/product-opportunities─► Opportunity Scoring           │   │
│  │  ├─ GET  /api/posts-for-improvement─► Posts by Opportunity Score    │   │
│  │  ├─ GET  /api/llm-config           ──► LLM Configuration            │   │
│  │  ├─ POST /api/llm-config           ──► Save LLM Config              │   │
│  │  ├─ POST /admin/cleanup-duplicates ──► Database Cleanup             │   │
│  │  ├─ GET  /posts                     ──► Database Fetch               │   │
│  │  ├─ GET  /scraping                  ──► Serve Scraping Page          │   │
│  │  ├─ GET  /dashboard                 ──► Serve Dashboard Page         │   │
│  │  └─ GET  /improvements              ──► Serve Improvements Page      │   │
│  │                                                                      │   │
│  │  APScheduler:                                                       │   │
│  │  └─ auto_scrape_job() runs every 3 hours                            │   │
│  │     └─ Scrapes all sources with default queries                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                              │                                       │
│       ▼                              │                                       │
│  ┌──────────────────────────────────┐│                                       │
│  │  scraper/ (9 Scraper Modules)   ││                                       │
│  │                                  ││                                       │
│  │  ├─ trustpilot.py                ││  Real Reviews                         │
│  │  │  └─ scrape_trustpilot_reviews()│  ├─ Ratings (⭐)                     │
│  │  │     └─ HTML scraping          ││  └─ Empty list on failure            │
│  │  │                                ││                                       │
│  │  ├─ x_scraper.py                 ││  Complaint Tweets                     │
│  │  │  └─ scrape_x_multi_queries()   │  ├─ "OVH support bad"                │
│  │  │     └─ Nitter instances       │  └─ "OVH expensive"                   │
│  │  │        (fallback)              │                                       │
│  │  │                                ││                                       │
│  │  ├─ github.py                     ││  Customer Experience Issues          │
│  │  │  └─ scrape_github_issues()     ││  ├─ "OVH domain" (UX)               │
│  │  │     ├─ "OVH domain"            ││  ├─ "OVH customer"                   │
│  │  │     ├─ "OVH customer"          ││  └─ "OVH experience"                 │
│  │  │     └─ GitHub API              ││                                       │
│  │  │                                ││                                       │
│  │  ├─ stackoverflow.py              ││  Technical Questions                 │
│  │  │  └─ scrape_stackoverflow()     ││  └─ Stack Overflow API              │
│  │  │     └─ Stack Overflow API      ││                                       │
│  │  │                                ││                                       │
│  │  ├─ reddit.py                     ││  Reddit Discussions                  │
│  │  │  └─ scrape_reddit()            ││  └─ RSS feeds                       │
│  │  │     └─ feedparser (RSS)        ││                                       │
│  │  │                                ││                                       │
│  │  ├─ news.py                       ││  News & Articles                     │
│  │  │  └─ scrape_google_news()       ││  └─ feedparser (RSS)                │
│  │  │                                ││                                       │
│  │  ├─ ovh_forum.py                  ││  OVH Community Forum                 │
│  │  │  └─ scrape_ovh_forum()        ││  └─ HTML scraping                   │
│  │  │     └─ BeautifulSoup           ││                                       │
│  │  │                                ││                                       │
│  │  ├─ mastodon.py                   ││  Mastodon Posts                      │
│  │  │  └─ scrape_mastodon()          ││  └─ Mastodon API                     │
│  │  │                                ││                                       │
│  │  ├─ g2_crowd.py                   ││  G2 Crowd Reviews                    │
│  │  │  └─ scrape_g2_crowd()         ││  └─ HTML scraping                   │
│  │  │     └─ BeautifulSoup           ││                                       │
│  │  │                                ││                                       │
│  │  ├─ anti_bot_helpers.py          ││  Anti-Bot Protection                 │
│  │  │  ├─ get_realistic_headers()   ││  └─ Headers, delays, stealth        │
│  │  │  └─ create_stealth_session()  ││                                       │
│  │  │                                ││                                       │
│  │  └─ selenium_helper.py           ││  Browser Automation (Optional)       │
│  │     └─ scrape_with_playwright()   ││  └─ For JS-heavy sites              │
│  │        └─ RSS feeds               ││                                       │
│  └──────────────────────────────────┘│                                       │
│       │                               ▼                                       │
│       │  raw posts [{...}, {...}, ...]                                      │
│       │                               ✅ Only real data                      │
│       │  ❌ No mock data on failure!  (Returns 503 instead)                 │
│       │                                                                      │
│       ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  analysis/ (Sentiment & Processing)                                 │   │
│  │                                                                      │   │
│  │  ├─ sentiment.py                                                    │   │
│  │  │  └─ analyze(text: str)                                           │   │
│  │  │     ├─ VADER SentimentIntensityAnalyzer                          │   │
│  │  │     └─ Returns: {score: float, label: str}                       │   │
│  │  │        └─ label ∈ {positive, negative, neutral}                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       │  enriched posts [{id, source, author, content, sentiment...}, ...] │
│       ▼                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  db.py (SQLite Database Operations)                                 │   │
│  │                                                                      │   │
│  │  ├─ init_db()                      Initialize schema               │   │
│  │  ├─ insert_post(post: dict)        Write to DB (duplicate check)   │   │
│  │  ├─ get_posts(limit: int)          Read from DB                    │   │
│  │  ├─ delete_duplicate_posts()      Remove duplicates                │   │
│  │  └─ delete_duplicate_posts()      Remove duplicate posts          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                                                                      │
│       ▼                                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ SQLite file: data.db
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Database (SQLite)                                │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  posts table                                                         │   │
│  │  (Only contains REAL posts from actual scrapers)                    │   │
│  │                                                                      │   │
│  │  ┌────┬──────────┬──────────┬──────────┬────┬──────────┬──────────┐ │   │
│  │  │ id │  source  │ author   │ content  │url │sentiment_│sentiment_│ │   │
│  │  │    │          │          │          │    │  score   │  label   │ │   │
│  │  ├────┼──────────┼──────────┼──────────┼────┼──────────┼──────────┤ │   │
│  │  │ 1  │Trustpilot│Jean M.   │Domain... │url │ -0.80    │ negative │ │   │
│  │  │ 2  │ GitHub   │pierreP   │renewal..│url │ -0.65    │ negative │ │   │
│  │  │ 3  │ X        │ @techUser│ OVH exp.│url │ -0.72    │ negative │ │   │
│  │  │ 4  │Stack Ov. │user_456  │ renewal │url │ -0.45    │ negative │ │   │
│  │  │ .. │  ...     │  ...     │  ...    │... │  ...     │  ...     │ │   │
│  │  └────┴──────────┴──────────┴──────────┴────┴──────────┴──────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Scraping Flow (Manual)

```
User Request (HTTP POST /scrape/trustpilot)
       │
       ▼
FastAPI Endpoint Handler
       │
       ▼
Scraper Module (trustpilot.py)
       │
       ├─► Try: Trustpilot API
       │   └─► Extract: source, author, content, url, rating, created_at
       │
       ├─ If API available:
       │   └─► Raw posts list
       │
       └─ If API fails/unavailable:
           └─► RAISE ERROR → Return 503 Service Unavailable
               (NO MOCK DATA!)
       │
       ▼
Sentiment Analysis (sentiment.py) - Only if real data
       │
       ├─► VADER Sentiment for each post
       │   └─► Classify: negative (-1.0 to -0.05)
       │                 neutral (-0.05 to 0.05)
       │                 positive (0.05 to 1.0)
       │
       ▼
Database Insert (db.py → insert_post)
       │
       ├─► Check for duplicate URL
       │   └─► If duplicate: skip insertion, return False
       │
       ▼
SQLite: INSERT INTO posts (source, author, content, ...)
       │   (Only if not duplicate)
       │
       ▼
Response: {added: n} (number of new posts added, duplicates excluded)
```

### 2. Auto Scraping Flow (Every 3 hours)

```
APScheduler Timer (3-hour interval)
       │
       ▼
auto_scrape_job()
       │
       ├─► Loop through all scrapers:
       │   ├─ trustpilot.scrape_trustpilot_reviews()
       │   ├─ x_scraper.scrape_x_multi_queries()
       │   ├─ github.scrape_github_issues()
       │   ├─ stackoverflow.scrape_stackoverflow()
       │   ├─ reddit.scrape_reddit()
       │   ├─ news.scrape_google_news()
       │   ├─ ovh_forum.scrape_ovh_forum()
       │   ├─ mastodon.scrape_mastodon()
       │   └─ g2_crowd.scrape_g2_crowd()
       │
       ├─ For each scraper:
       │   ├─ Try: Scrape → Analyze → Insert
       │   └─ Except: Log error (NO FALLBACK DATA!)
       │
       ▼
Console logs: "✓ Added 5 posts from Trustpilot"
              "✗ Error scraping X: snscrape unavailable"
```

### 3. Fetch Flow

```
User Request (HTTP GET /posts?limit=20)
       │
       ▼
FastAPI Endpoint Handler
       │
       ▼
Database Query (db.py → get_posts)
       │
       ├─► SELECT * FROM posts ORDER BY id DESC LIMIT 20
       │   (Only returns REAL posts)
       │
       ▼
Posts Array: [
  {id: 3, source: 'trustpilot', author: 'Jean', content: '...', sentiment_score: -0.80, ...},
  {id: 2, source: 'github', author: 'pierreP', content: '...', sentiment_score: -0.65, ...},
  ...
]
       │
       ▼
JSON Response to Frontend
       │
       ▼
Frontend: Render Card Gallery (index.html)
       │
       └─► Apply filters: Source | Sentiment | Date | Keywords
           Display filtered results
```

## File Structure

```
ovh-complaints-tracker/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI app, endpoints, scheduler
│   │   ├── db.py                         # SQLite helpers
│   │   │
│   │   ├── scraper/
│   │   │   ├── __init__.py
│   │   │   ├── trustpilot.py             # ⭐ Trustpilot reviews scraper
│   │   │   ├── x_scraper.py              # X/Twitter scraper (complaint keywords)
│   │   │   ├── github.py                 # GitHub Issues (customer experience)
│   │   │   ├── stackoverflow.py          # Stack Overflow Q&A
│   │   │   ├── reddit.py                 # Reddit RSS feeds
│   │   │   └── news.py                   # Google News RSS
│   │   │
│   │   └── analysis/
│   │       ├── __init__.py
│   │       └── sentiment.py              # VADER sentiment analysis
│   │
│   ├── requirements.txt                  # Python dependencies
│   ├── test_complaint_scrapers.py       # Test customer complaint scrapers
│   └── test_scrapers_qa.py              # QA test for all scrapers
│
├── frontend/
│   ├── index.html                        # Scraping & Configuration page
│   ├── css/
│   │   └── shared-theme.css              # Shared dark/light theme
│   ├── dashboard/
│   │   ├── index.html                    # Dashboard Analytics page
│   │   ├── css/
│   │   │   ├── styles.css                # Dashboard styles
│   │   │   └── navigation.css             # Navigation menu styles
│   │   └── js/
│   │       ├── app.js                     # Main app initialization
│   │       ├── api.js                     # API communication
│   │       ├── state.js                   # State management
│   │       ├── dashboard.js               # Dashboard UI logic
│   │       ├── charts.js                  # Chart.js visualizations
│   │       ├── whats-happening.js         # What's Happening analysis
│   │       ├── product-detection.js       # Product categorization
│   │       └── version-switch.js          # Version switching logic
│   └── improvements/
│       ├── index.html                    # Improvements Opportunities page
│       └── js/
│           └── app.js                     # Improvements page logic
│
├── data.db                               # SQLite database (created at runtime)
├── README.md                             # Project documentation
├── ARCHITECTURE.md                       # This file
└── .venv/                                # Python virtual environment
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML5, CSS3, Vanilla JS (ES6 Modules) | Multi-page application: Scraping, Dashboard, Improvements |
| **Backend API** | FastAPI (Python 3.11/3.12) | HTTP endpoints, async request handling, static file serving |
| **Scheduler** | APScheduler | Auto-scraping every 3 hours |
| **Scrapers** | httpx, feedparser, BeautifulSoup | Real data from Trustpilot, X (Nitter), GitHub, etc. |
| **Sentiment** | VADER (vaderSentiment) | Classify customer sentiment in complaints |
| **Database** | SQLite (sqlite3) | Persistent storage of real posts only |
| **Charts** | Chart.js | Interactive timeline, histogram, and product distribution charts |
| **LLM** | OpenAI GPT-4o-mini / Anthropic Claude 3 Haiku | AI-powered recommended actions and improvement ideas |

## Key Design Decisions

1. **Real Data Only**: No mock data fallbacks. If scraper fails, return empty list instead of fake posts.
2. **FastAPI**: Lightweight, async-capable, auto-documentation (Swagger).
3. **SQLite**: Zero-config, file-based, good for small/medium datasets. Indexed for performance.
4. **Duplicate Detection**: URL-based duplicate prevention to avoid data redundancy.
5. **VADER Sentiment**: Fast, rule-based, tuned for social media language.
6. **Multi-Page Frontend**: Three dedicated pages (Scraping, Dashboard, Improvements) with shared navigation and theme.
7. **ES6 Modules**: Frontend uses ES6 modules for better code organization and maintainability.
8. **Modular Scrapers**: Each source (Trustpilot, X, GitHub, etc.) is isolated for independent development.
9. **Complaint-Focused**: All scrapers search for customer complaints, not generic mentions.
10. **APScheduler**: Background auto-scraping without external job queue.
11. **Background Jobs**: Thread-based job system for long-running keyword searches with progress tracking.
12. **Fallback Strategies**: Scrapers use multiple strategies (HTML → API → empty list) for resilience.
13. **LLM Integration**: Dynamic, context-aware recommended actions based on filtered posts and active filters.
14. **Priority Scoring**: Multiplicative algorithm: `sentiment * keyword_relevance * recency` (0-100 scale) for accurate prioritization.
15. **Interactive Charts**: Chart.js visualizations with click/double-click filtering capabilities.
16. **Shared Theme System**: Consistent dark/light mode across all pages with localStorage synchronization.

## API Contract

### POST /scrape/trustpilot

```
Request:
  POST /scrape/trustpilot?query=OVH%20domain&limit=50
  
Response (200 OK):
  {"added": 5}  // Number of new posts added (duplicates excluded)
  
Response (200 OK - No data found):
  {"added": 0}  // Scraper succeeded but found no new posts
```

### POST /scrape/x

```
Request:
  POST /scrape/x?query=OVH&limit=50
  
Response (200 OK - Real tweets found):
  {"added": 12}  // New posts added
  
Response (200 OK - No data):
  {"added": 0}  // All methods failed or no new posts
```

### POST /scrape/keywords

```
Request:
  POST /scrape/keywords?limit=50&concurrency=2&delay=0.5
  Body: { "keywords": ["OVH", "domain"] }
  
Response (200 OK):
  {"job_id": "uuid-123"}
```

### GET /scrape/jobs/{job_id}

```
Response (200 OK):
  {
    "id": "uuid-123",
    "status": "running",
    "progress": {"total": 12, "completed": 5},
    "results": [{"added": 3}, {"added": 2}],
    "errors": [],
    "created_at": "2026-01-13T10:00:00",
    "updated_at": "2026-01-13T10:05:00"
  }
```

### POST /scrape/github

```
Request:
  POST /scrape/github?query=OVH&limit=50
  
Response (200 OK):
  {"added": 8}
```

### GET /posts

```
Request:
  GET /posts?limit=20
  
Response (200 OK - Real posts only):
  [
    {
      "id": 1,
      "source": "trustpilot",
      "author": "Jean Martin",
      "content": "Domain renewal costs are way too high...",
      "url": "https://trustpilot.com/review/ovh.com",
      "created_at": "2026-01-13T15:30:00",
      "sentiment_score": -0.80,
      "sentiment_label": "negative"
    },
    {
      "id": 2,
      "source": "github",
      "author": "pierrepaap",
      "content": "internal error when renewing expired cert...",
      "url": "https://github.com/...",
      "created_at": "2026-01-12T10:15:00",
      "sentiment_score": -0.65,
      "sentiment_label": "negative"
    },
    ...
  ]
```

## Scraper Fallback Strategies

### X/Twitter Scraper
1. **Primary**: Nitter instances (nitter.net, nitter.poast.org, nitter.1d4.us)
2. **Fallback**: Twitter API (requires authentication, currently disabled)
3. **Final**: Empty list (no sample data)

### Trustpilot Scraper
1. **Primary**: HTML scraping from Trustpilot web page
2. **Fallback**: Trustpilot API (if TRUSTPILOT_API_KEY is set)
3. **Final**: Empty list (no sample data)

### Other Scrapers
- **GitHub, Stack Overflow, Reddit, News**: Direct API calls with retry logic
- **OVH Forum, G2 Crowd**: HTML scraping with anti-bot protection
- **Mastodon**: Mastodon API with hashtag search
- **Error Handling**: Return empty list on failure, log errors for debugging

## Background Job System

The application supports background keyword scraping jobs:

```
POST /scrape/keywords
  Body: { "keywords": ["OVH", "domain"] }
  Response: { "job_id": "uuid-123" }

GET /scrape/jobs/{job_id}
  Response: {
    "id": "uuid-123",
    "status": "running|completed|failed|cancelled",
    "progress": { "total": 12, "completed": 5 },
    "results": [...],
    "errors": [...]
  }

POST /scrape/jobs/{job_id}/cancel
  Response: { "cancelled": true }
```

**Job Flow:**
1. Job created in memory (JOBS dict) and database
2. Background thread processes keywords across all sources
3. Progress updated in real-time
4. Results and errors persisted to database
5. Frontend polls job status every 2 seconds

## Error Handling Strategy

### Scraper Level
- **Network errors**: Retry with exponential backoff (3 attempts)
- **HTTP errors**: Log and return empty list
- **Parsing errors**: Skip item, continue with next
- **All failures**: Return empty list (never sample data)

### Database Level
- **Duplicate URLs**: Skip insertion, return False
- **Constraint violations**: Log error, skip item
- **Connection errors**: Raise exception (handled by endpoint)

### API Level
- **Scraper failures**: Return `{added: 0}` with 200 status
- **Database errors**: Return 500 with error detail
- **Validation errors**: Return 400 with validation details

## Scaling Considerations

- **More posts**: Use PostgreSQL instead of SQLite, add indexes on `(source, created_at, sentiment_label)`.
- **More scrapers**: Add Redis queue for async jobs; use Celery for distributed task scheduling.
- **Better Sentiment**: Replace VADER with Hugging Face transformer model (DistilBERT-multilingual).
- **Real-time updates**: Add WebSocket endpoint to push new complaint alerts.
- **Analytics**: Add dashboard for sentiment trends, source distribution, complaint categories.
- **Caching**: Redis cache for `/posts` results (5-10 min TTL).
- **Rate Limiting**: Add middleware to prevent API abuse.

## Future Enhancements

- [ ] Multi-language support (French, German, Spanish)
- [ ] Complaint category detection (pricing, support, UX, delivery, etc.)
- [x] Priority scoring: `sentiment * keyword_relevance * recency` ✅ Implemented
- [ ] Admin dashboard with trend charts and heatmaps
- [ ] Email/Slack alerts for critical complaints
- [ ] Manual tagging and flagging by support team
- [ ] Duplicate detection across platforms
- [ ] RateCard strategy optimization based on competitor pricing mentions
