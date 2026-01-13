# Architecture Overview

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Frontend (Browser)                               │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  index.html (Complaint Dashboard)                                    │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│  │  │ Complaint  │  │ Complaint  │  │ Complaint  │  │ Complaint  │    │   │
│  │  │    Card    │  │    Card    │  │    Card    │  │    Card    │    │   │
│  │  │(Real Data) │  │(Real Data) │  │(Real Data) │  │(Real Data) │    │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │   │
│  │                                                                      │   │
│  │  Filters: Source | Sentiment | Date | Keyword                      │   │
│  │  Scrapers: Trustpilot | X | GitHub | Stack Overflow | HN | News   │   │
│  │  Backlog: Save & Export complaints                                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ HTTP GET /posts                         │
│                                    │ HTTP POST /scrape/trustpilot            │
│                                    │ HTTP POST /scrape/x                     │
│                                    │ HTTP POST /scrape/github                │
│                                    │ HTTP POST /scrape/stackoverflow         │
│                                    │ HTTP POST /scrape/hackernews            │
│                                    │ HTTP POST /scrape/news                  │
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
│  │  ├─ POST /scrape/trustpilot    ──┐                                  │   │
│  │  ├─ POST /scrape/x              ──┼─► Scraper Router                │   │
│  │  ├─ POST /scrape/github         ──┤    (Real data only)             │   │
│  │  ├─ POST /scrape/stackoverflow  ──┤                                 │   │
│  │  ├─ POST /scrape/hackernews     ──┤                                 │   │
│  │  ├─ POST /scrape/news           ──┘                                 │   │
│  │  └─ GET /posts                  ──► Database Fetch                  │   │
│  │                                                                      │   │
│  │  APScheduler:                                                       │   │
│  │  └─ auto_scrape_job() runs every 3 hours                            │   │
│  │     └─ Scrapes all sources with default queries                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│       │                              │                                       │
│       ▼                              │                                       │
│  ┌──────────────────────────────────┐│                                       │
│  │  scraper/ (6 Scraper Modules)   ││                                       │
│  │                                  ││                                       │
│  │  ├─ trustpilot.py                ││  Real Reviews                         │
│  │  │  └─ scrape_trustpilot_reviews()│  ├─ Ratings (⭐)                     │
│  │  │     └─ Trustpilot API         ││  └─ Mock fallback                    │
│  │  │                                ││                                       │
│  │  ├─ x_scraper.py                 ││  Complaint Tweets                     │
│  │  │  └─ scrape_x_multi_queries()   │  ├─ "OVH support bad"                │
│  │  │     └─ snscrape (Python 3.13) │  └─ "OVH expensive"                   │
│  │  │        (may fail)              │                                       │
│  │  │                                ││                                       │
│  │  ├─ github.py                     ││  Customer Experience Issues          │
│  │  │  └─ scrape_github_issues()     ││  ├─ "OVH domain" (UX)               │
│  │  │     ├─ "OVH domain"            ││  ├─ "OVH customer"                   │
│  │  │     ├─ "OVH customer"          ││  └─ "OVH experience"                 │
│  │  │     └─ GitHub API              ││                                       │
│  │  │                                ││                                       │
│  │  ├─ stackoverflow.py              ││  Technical Questions                 │
│  │  │  └─ scrape_stackoverflow()     ││  └─ "intitle:OVH"                   │
│  │  │     └─ Stack Overflow API      ││                                       │
│  │  │                                ││                                       │
│  │  ├─ hackernews.py                 ││  Tech Community Discussions          │
│  │  │  └─ scrape_hackernews()        ││  └─ Algolia API search              │
│  │  │     └─ Algolia API             ││                                       │
│  │  │                                ││                                       │
│  │  └─ news.py                       ││  News & Articles                     │
│  │     └─ scrape_google_news()       ││  └─ feedparser (RSS)                │
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
│  │  ├─ insert_post(post: dict)        Write to DB                     │   │
│  │  └─ get_posts(limit: int)          Read from DB                    │   │
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
       ▼
SQLite: INSERT INTO posts (source, author, content, ...)
       │
       ▼
Response: {added: n} (number of real posts added)
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
       │   ├─ hackernews.scrape_hackernews()
       │   └─ news.scrape_google_news()
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
│   │   │   ├── hackernews.py             # Hacker News discussions
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
│   └── index.html                        # Single-page dashboard (vanilla JS)
│
├── data.db                               # SQLite database (created at runtime)
├── README.md                             # Project documentation
├── ARCHITECTURE.md                       # This file
└── .venv/                                # Python virtual environment
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML5, CSS3, Vanilla JS | Real-time complaint dashboard, filters, backlog |
| **Backend API** | FastAPI (Python 3.13) | HTTP endpoints, async request handling |
| **Scheduler** | APScheduler | Auto-scraping every 3 hours |
| **Scrapers** | httpx, feedparser, snscrape | Real data from Trustpilot, X, GitHub, etc. |
| **Sentiment** | VADER (vaderSentiment) | Classify customer sentiment in complaints |
| **Database** | SQLite (sqlite3) | Persistent storage of real posts only |

## Key Design Decisions

1. **Real Data Only**: No mock data fallbacks. If scraper fails, return 503 error instead of fake posts.
2. **FastAPI**: Lightweight, async-capable, auto-documentation (Swagger).
3. **SQLite**: Zero-config, file-based, good for small/medium datasets.
4. **VADER Sentiment**: Fast, rule-based, tuned for social media language.
5. **Vanilla JS Frontend**: No build step, easy to extend, uses localStorage for backlog persistence.
6. **Modular Scrapers**: Each source (Trustpilot, X, GitHub, etc.) is isolated for independent development.
7. **Complaint-Focused**: All scrapers search for customer complaints, not generic mentions.
8. **APScheduler**: Background auto-scraping without external job queue.

## API Contract

### POST /scrape/trustpilot

```
Request:
  POST /scrape/trustpilot?query=OVH%20domain&limit=50
  
Response (200 OK):
  {"added": 5}
  
Response (503 Error - Real data unavailable):
  {"detail": "Trustpilot scraper unavailable"}
```

### POST /scrape/x

```
Request:
  POST /scrape/x?limit=50
  
Response (200 OK - Real tweets found):
  {"added": 12}
  
Response (503 Error - snscrape broken on Python 3.13):
  {"detail": "X/Twitter scraper unavailable (snscrape incompatibility with Python 3.13)"}
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

## Scaling Considerations

- **More posts**: Use PostgreSQL instead of SQLite, add indexes on `(source, created_at, sentiment_label)`.
- **More scrapers**: Add Redis queue for async jobs; use Celery for distributed task scheduling.
- **Better Sentiment**: Replace VADER with Hugging Face transformer model (DistilBERT-multilingual).
- **Real-time updates**: Add WebSocket endpoint to push new complaint alerts.
- **Analytics**: Add dashboard for sentiment trends, source distribution, complaint categories.
- **Caching**: Redis cache for `/posts` results (5-10 min TTL).

## Future Enhancements

- [ ] Multi-language support (French, German, Spanish)
- [ ] Complaint category detection (pricing, support, UX, delivery, etc.)
- [ ] Priority scoring: `sentiment * keyword_relevance * recency`
- [ ] Admin dashboard with trend charts and heatmaps
- [ ] Email/Slack alerts for critical complaints
- [ ] Manual tagging and flagging by support team
- [ ] Duplicate detection across platforms
- [ ] RateCard strategy optimization based on competitor pricing mentions
