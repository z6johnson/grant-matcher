# Grant Match

AI-powered faculty matching tool for UC San Diego's Herbert Wertheim School of Public Health. Upload a grant opportunity document and the tool identifies faculty whose research expertise aligns with the investigator requirements.

## How It Works

1. **Upload** a grant document (PDF or TXT, up to 10 MB)
2. **AI extracts** investigator requirements — PI, Co-PI, and key personnel needs
3. **AI matches** requirements against the faculty directory (~100 researchers)
4. **Results** show ranked faculty with match scores, recommended roles, and reasoning

Two sequential LLM calls power the analysis via [LiteLLM](https://github.com/BerriAI/litellm):
- **Call 1:** Extract structured grant requirements from the document text
- **Call 2:** Rank faculty by alignment with those requirements

## Architecture

Hybrid cloud deployment — the frontend and API run on separate free-tier platforms:

| Component | Platform | What it does |
|-----------|----------|--------------|
| **Frontend** | Vercel (Hobby) | Serves `index.html`, CSS, and JS as static files via CDN |
| **API** | Render (Free) | Runs the Flask app with gunicorn — no serverless timeout limits |

This split is necessary because Vercel Hobby has a 10-second serverless function timeout, and each LLM call takes 10–15 seconds.

```
Browser (Vercel CDN)          Render Web Service
┌─────────────────┐           ┌─────────────────────┐
│  index.html     │  POST     │  Flask app (app.py)  │
│  static/css/    │ ───────── │  ├─ /api/match       │
│  static/js/     │  /api/    │  ├─ document_parser   │
│                 │  match    │  ├─ grant_matcher     │
│                 │ ◄──────── │  └─ faculty.json      │
│                 │  JSON     │                       │
└─────────────────┘           └─────────────────────┘
```

## Project Structure

```
grant-match/
├── app.py                    # Flask API (CORS-enabled, deployed to Render)
├── requirements.txt          # Python dependencies
├── render.yaml               # Render blueprint for deployment
├── vercel.json               # Vercel config (static files only)
├── index.html                # Single-page frontend
├── .env.example              # Environment variable template
├── data/
│   └── faculty.json          # Faculty directory (~100 records)
├── static/
│   ├── css/style.css         # UCSD-branded styles
│   └── js/app.js             # Frontend logic
└── utils/
    ├── __init__.py
    ├── document_parser.py    # PDF/TXT text extraction (pdfplumber)
    └── grant_matcher.py      # LLM-powered matching engine (LiteLLM)
```

## Deployment

### Prerequisites

- A [LiteLLM](https://github.com/BerriAI/litellm)-compatible API endpoint and key
- A [Render](https://render.com) account (free tier)
- A [Vercel](https://vercel.com) account (Hobby tier)

### 1. Deploy the API to Render

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New Web Service**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Set environment variables in the Render dashboard:

   | Variable | Description |
   |----------|-------------|
   | `LITELLM_API_KEY` | Your LLM API key |
   | `LITELLM_API_BASE` | Your LLM API endpoint URL |
   | `LITELLM_MODEL` | Model identifier (default: `api-gpt-oss-120b`) |

5. Deploy. Note the service URL (e.g. `https://grant-match-api.onrender.com`)

### 2. Configure the frontend API URL

Update `index.html` with your Render service URL:

```html
<script>
    window.GRANT_MATCH_API_URL = "https://grant-match-api.onrender.com";
</script>
```

Commit and push the change.

### 3. Deploy the frontend to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard) → **Add New Project**
2. Import your GitHub repo
3. Vercel auto-detects `vercel.json` and serves static files only
4. No environment variables needed on Vercel

### Notes

- **Render free tier** spins down after 15 minutes of inactivity. First request after idle takes ~30 seconds (cold start).
- **CORS** is configured in `app.py` to accept requests from `*.vercel.app` origins.
- The `gunicorn --timeout 120` flag ensures workers aren't killed during the 15–30 second LLM processing time.

## API

### `POST /api/match`

Upload a grant document for faculty matching.

**Request:** `multipart/form-data` with a `file` field (PDF or TXT, max 10 MB)

**Response (200):**
```json
{
  "grant_summary": {
    "grant_title": "...",
    "funding_agency": "...",
    "pi_requirements": { "expertise_areas": [], "qualifications": [], "constraints": [] },
    "co_pi_requirements": { "expertise_areas": [], "qualifications": [], "constraints": [] },
    "key_personnel": [{ "role": "...", "expertise_areas": [], "qualifications": [] }],
    "overall_research_themes": []
  },
  "matches": [
    {
      "rank": 1,
      "first_name": "...",
      "last_name": "...",
      "degrees": [],
      "title": "...",
      "email": "...",
      "research_interests": "...",
      "match_score": 85,
      "recommended_role": "PI",
      "match_reasoning": "..."
    }
  ],
  "total_faculty_considered": 77,
  "faculty_without_interests_count": 23
}
```

**Error Response:**
```json
{ "error": "Human-readable error message" }
```
