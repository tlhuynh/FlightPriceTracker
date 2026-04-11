# Flight Tracker — Project Context & Progress

## What this project does
Monitors flight prices for specific routes and airlines, saves price history
to a database, sends email alerts when prices change, and displays a
dashboard with price history and reports.

---

## Architecture — two separate projects

### 1. flight-tracker-python (this project — VS Code)
Background service handling all data work:
- Fetches flight prices via SerpApi (Google Flights)
- Runs on a schedule once per day (APScheduler)
- Detects price changes and sends email alerts (SendGrid)
- Saves all price history to the database
- Exposes a REST API via FastAPI so the dashboard can read data

### 2. flight-tracker-dotnet (separate repo — Rider)
Frontend + thin backend for visualization:
- ASP.NET Minimal API — optional proxy/auth layer, calls Python FastAPI
- Angular — dashboard UI with price history charts and reports
- ng2-charts for price history visualization

---

## Tech stack

| Layer            | Technology              | Notes                          |
|------------------|-------------------------|--------------------------------|
| Price data       | SerpApi                 | Google Flights, 100 free/mo    |
| Scheduler        | APScheduler             | runs once per day              |
| Database         | SQL Server (existing)   | reuse live Azure SQL Server    |
| Python DB driver | pyodbc + SQLAlchemy     | mssql+pyodbc connection string |
| Email alerts     | SendGrid                | 100 emails/day free            |
| Python API       | FastAPI + uvicorn       | port 8000                      |
| .NET backend     | ASP.NET Minimal API     | port 5000, optional BFF layer  |
| Frontend         | Angular                 | port 4200 in dev               |
| Charts           | ng2-charts              | price history graphs           |
| Containers       | Docker + docker-compose | 3 containers, add before Azure |
| Cloud            | Azure Container Apps    | all 3 services deployed here   |
| Image registry   | Azure Container Registry| stores built Docker images     |
| Secrets          | Azure Key Vault         | API keys, connection strings   |
| Angular hosting  | Azure Static Web Apps   | free tier, better for SPA      |

---

## Target routes and airlines
- Routes: IAH → NRT (Tokyo Narita), IAH → HND (Tokyo Haneda)
- Airlines: United Airlines, ANA, Japan Airlines, Delta, American Airlines
- Dates tracked: 1 month out and 6 months from current date
- Alert threshold: notify on any price change (configurable)

---

## Database
SQL Server everywhere — no SQLite fallback.
- Local dev: SQL Server running in Docker on local network
- Production: Azure SQL Server (existing instance, already paid for)
- Both use mssql+pyodbc connection string via DATABASE_URL env var
- New database called FlightTracker on each server
- Requires ODBC Driver 18 for SQL Server (install via Homebrew on Mac)

---

## Docker setup (add before first Azure deploy, not from day one)
Three containers managed by docker-compose:
- python-service  → tracker + FastAPI (port 8000)
- dotnet-api      → ASP.NET backend (port 5000)
- angular-app     → nginx + Angular (port 80)

Containers communicate by service name internally (e.g. http://python-service:8000).
Python Dockerfile needs Microsoft ODBC driver 18 installed for SQL Server.

---

## Dev environment (Mac)
- macOS with Homebrew
- pyenv managing Python versions (Python 3.12.11 active)
- Poetry 2.3.3 installed via Homebrew for dependency management
- VS Code for Python service
- Rider for .NET + Angular
- Azure Data Studio for database management
- Docker Desktop for containers

### Key pyenv/Poetry setup
```bash
# Python version pinned per project
pyenv local 3.12.11        # creates .python-version file

# Poetry virtual environment
# Located at: /Users/tlhuynh/Library/Caches/pypoetry/virtualenvs/flight-tracker-python-w0Eadt9m-py3.12
# Python: 3.12.11 CPython — Valid: True
```

---

## Project structure

```
flight-tracker-python/
├── .python-version           ← pyenv pins 3.12.11 for this project
├── pyproject.toml            ← Poetry config + dependencies
├── poetry.lock               ← exact pinned versions (commit this)
├── README.md
├── CLAUDE.md                 ← this file
├── .env                      ← never commit (real secrets)
├── .env.example              ← commit this (template)
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py               ← entry point, starts scheduler + API
│   ├── config.py             ← routes, airlines, settings
│   ├── scheduler.py          ← APScheduler job definitions
│   ├── checker.py            ← fetch prices, detect changes
│   ├── serpapi.py            ← SerpApi calls, filter by airline
│   ├── notifier.py           ← email alert logic
│   ├── db.py                 ← SQLAlchemy DB access
│   └── api/
│       ├── __init__.py
│       ├── routes.py         ← FastAPI endpoints
│       └── schemas.py        ← Pydantic request/response models
├── tests/
│   ├── __init__.py
│   ├── test_checker.py
│   └── test_api.py
└── migrations/               ← Alembic DB migrations (add later)
```

---

## FastAPI endpoints (Python exposes these)
- GET /prices/{route}?days=90  → price history for a route
- GET /prices/latest            → latest price per route/airline
- GET /routes                   → list of watched routes

---

## Environment variables

```bash
# .env.example — commit this
SERPAPI_KEY=your_serpapi_key_here
DB_HOST=localhost
DB_PORT=1434
DB_NAME=FlightTracker
DB_USER=sa
DB_PASSWORD=your_password_here
SENDGRID_API_KEY=your_sendgrid_api_key_here
EMAIL_FROM=you@example.com
NOTIFY_EMAILS=you@example.com,another@example.com
CHECK_INTERVAL_HOURS=48
ALERT_THRESHOLD_USD=50
```

DB_* vars are used with SQLAlchemy URL.create() — avoids ODBC parsing issues with a single DATABASE_URL string.
Local dev: Azure SQL Edge Docker on port 1434. Production: Azure SQL Server.

---

## Azure deployment flow
1. Build Docker images locally
2. Push to Azure Container Registry (ACR)
3. Azure Container Apps pulls from ACR and runs containers
4. Secrets stored in Azure Key Vault, injected as env vars
5. GitHub Actions automates build → push → deploy pipeline

---

## Build order — what to build next

### Done
- [x] Mac dev environment set up (pyenv, Python 3.12.11, Poetry 2.3.3)
- [x] Poetry project created (poetry new flight-tracker-python)
- [x] pyenv local set to 3.12.11 (pyenv local 3.12.11)
- [x] Poetry virtual environment created and verified (Valid: True)
- [x] Renamed default package folder from flight_tracker_python/ to app/

- [x] Create remaining folder structure and empty files (see structure above)
- [x] Update pyproject.toml packages reference from flight_tracker_python to app
- [x] Added purpose comments to all .py files

- [x] Set up .gitignore
- [x] Set up .env and .env.example
- [x] Install dependencies via Poetry (+ ruff as dev dependency)
- [x] Write config.py (routes, airlines, settings, outbound date calculation)
- [x] Write serpapi.py (fetch prices from SerpApi, filter by airline)
- [x] Write db.py (SQLAlchemy models for FlightRecord + ApiCallLog, CRUD functions)
- [x] Write checker.py (all features: logging, new/disappeared/untracked flight alerts, error handling, dedup, price validation, rate limiting, DB check)
- [x] Write notifier.py (SendGrid email alerts, grouped by alert type)
- [x] Write scheduler.py (APScheduler, run every 48 hours)
- [x] Write main.py (lifespan startup, logging config, uvicorn, router)
- [x] Write api/schemas.py (Pydantic models with from_attributes)
- [x] Write api/routes.py (FastAPI endpoints: /routes, /prices/latest, /prices/{dep}/{arr})

- [x] Set up local SQL Server Docker container on Mac (Azure SQL Edge on port 1434)
- [x] Create FlightTracker database
- [x] Test app startup (poetry run python -m app.main)
- [x] Set up SendGrid with domain authentication (tlhuynh.dev)
- [x] Test SendGrid email sending (noreply@tlhuynh.dev)
- [x] Refactored DATABASE_URL to individual DB_* env vars with URL.create()

### Up next
- [ ] Set up SerpApi account and test real flight data fetch
- [ ] Set up GitHub Actions for CI/CD
- [ ] Set up Azure services (Container Registry, Container Apps, Key Vault)
- [ ] Add Docker (Dockerfile + docker-compose.yml)
- [ ] Deploy to Azure Container Apps
- [ ] Add unit tests

### Future checker.py enhancements (TODO)
- [ ] #2 — Price trend detection (e.g., "dropped 3 times in a row")
- [ ] #6 — Cheapest flight summary per route
- [ ] #7 — Price per stop comparison
- [ ] #8 — Weekend vs weekday price tracking

---

## Key decisions already made
- Two separate repos (Python / .NET+Angular) — not a monorepo
- SQL Server over PostgreSQL — reuse existing Azure instance, zero extra cost
- Docker added before first Azure deployment, not from day one of dev
- SQL Server everywhere — local Docker instance for dev, Azure SQL Server for production
- ASP.NET layer is optional — Angular can call FastAPI directly for MVP
- Angular hosted on Azure Static Web Apps (free tier)
- Poetry over plain pip/venv — cleaner dependency management
- Python 3.12.11 via pyenv — stable, full package support
- Poetry installed via Homebrew on Mac
- SendGrid for email alerts (existing account), not smtplib
- Check interval set to 48 hours to stay within SerpApi free tier (100 calls/month)
- NOTIFY_EMAILS supports multiple recipients (comma-separated)
- Ruff for linting and formatting (dev dependency)
- db.py keeps models + functions in one file for now; split into models/ and repositories/ when it grows
- DB connection uses URL.create() instead of DATABASE_URL string — SQL Server ODBC has parsing quirks
- Local dev uses Azure SQL Edge Docker (ARM/Apple Silicon compatible) on port 1434
- Email from: noreply@tlhuynh.dev (domain authenticated in SendGrid via Cloudflare DNS)
- SendGrid API key: use restricted (Mail Send permission only), not full access

---

## SerpApi — how it works for this project
SerpApi wraps Google Flights and returns structured JSON.
Filter results to only the 5 watched airlines after fetching.

```python
# Example call pattern
import httpx

params = {
    "engine": "google_flights",
    "departure_id": "IAH",
    "arrival_id": "NRT",
    "outbound_date": "2026-05-01",
    "currency": "USD",
    "hl": "en",
    "api_key": SERPAPI_KEY
}
response = httpx.get("https://serpapi.com/search", params=params)
flights = response.json().get("best_flights", [])

WATCH_AIRLINES = {"United Airlines", "ANA", "Japan Airlines", "Delta", "American Airlines"}
filtered = [f for f in flights if f["flights"][0]["airline"] in WATCH_AIRLINES]
```

---

## Notes for Claude Code in VS Code
- Always use poetry run prefix or activate shell with poetry shell before running Python
- Virtual env path: /Users/tlhuynh/Library/Caches/pypoetry/virtualenvs/flight-tracker-python-w0Eadt9m-py3.12
- Python interpreter to select in VS Code: the executable inside that virtualenv path above
- Do not use pip install directly — always use poetry add to keep pyproject.toml in sync
- The app/ folder is the main package (renamed from default flight_tracker_python/)
