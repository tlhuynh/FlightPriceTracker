# Flight Tracker — Project Context & Progress

## What this project does
Monitors flight prices for specific routes and airlines, saves price history
to a database, and sends email alerts when prices change.

Dashboard is on hold — if built later, it will be a separate project that
reads directly from the SQL Server database.

---

## Architecture

### flight-tracker-python (this project — VS Code)
Scheduled background job — runs once per execution, then exits:
- Fetches flight prices via SerpApi (Google Flights)
- Detects price changes and sends email alerts (SendGrid)
- Saves all price history to SQL Server
- Scheduling handled externally (Azure Container Apps Job cron, or run manually)

### Dashboard (on hold — future separate project)
If built later: a separate repo (e.g. flight-tracker-dotnet) that reads directly
from the SQL Server database. No FastAPI layer needed.

---

## Tech stack

| Layer            | Technology              | Notes                          |
|------------------|-------------------------|--------------------------------|
| Price data       | SerpApi                 | Google Flights, 250 free/mo    |
| Scheduling       | Azure Container Apps Job| external cron, runs job + exits|
| Database         | SQL Server (existing)   | reuse live Azure SQL Server    |
| Python DB driver | pyodbc + SQLAlchemy     | mssql+pyodbc connection string |
| Email alerts     | SendGrid                | 100 emails/day free            |
| Containers       | Docker                  | single image for the job       |
| Cloud            | Azure Container Apps    | Container Apps Job             |
| Image registry   | Azure Container Registry| stores built Docker image      |
| Secrets          | Azure Key Vault         | API keys, connection strings   |

---

## Target routes and airlines
- Routes: IAH → NRT (Tokyo Narita), IAH → HND (Tokyo Haneda)
- Airlines: United, ANA, JAL, Delta, American, EVA Air (exact strings returned by SerpApi)
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

## Docker setup (add before first Azure deploy)
Single container — the Python job:
- Runs `python -m app.main`, exits when done
- Dockerfile needs Microsoft ODBC driver 18 installed for SQL Server
- No ports exposed, no docker-compose needed

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
│   ├── main.py               ← entry point: init DB, run check, send alerts, exit
│   ├── config.py             ← routes, airlines, settings
│   ├── checker.py            ← fetch prices, detect changes
│   ├── serpapi.py            ← SerpApi calls, filter by airline
│   ├── notifier.py           ← email alert logic
│   └── db.py                 ← SQLAlchemy DB access
└── tests/
    ├── __init__.py
    └── test_checker.py
```

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
ALERT_THRESHOLD_USD=50
```

CHECK_INTERVAL_HOURS removed — scheduling is handled externally by Azure Container Apps Job cron.

DB_* vars are used with SQLAlchemy URL.create() — avoids ODBC parsing issues with a single DATABASE_URL string.
Local dev: Azure SQL Edge Docker on port 1434. Production: Azure SQL Server.

---

## Azure deployment flow
1. Build Docker image locally
2. Push to Azure Container Registry (ACR)
3. Azure Container Apps Job pulls image and runs on cron schedule
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
- [x] Write main.py (init DB, quota check, run check + alerts, exit)

- [x] Set up local SQL Server Docker container on Mac (Azure SQL Edge on port 1434)
- [x] Create FlightTracker database
- [x] Test app startup (poetry run python -m app.main)
- [x] Set up SendGrid with domain authentication (tlhuynh.dev)
- [x] Test SendGrid email sending (noreply@tlhuynh.dev)
- [x] Refactored DATABASE_URL to individual DB_* env vars with URL.create()

- [x] Added round-trip flight support (return_date throughout stack)
- [x] Per-route trip lengths (NRT/HND: 14 days, SGN: 14 + 30 days)
- [x] Changed check interval to 36 hours
- [x] Added startup price check with 240-call guard
- [x] Set up SerpApi account and tested real flight data fetch
- [x] Fixed load_dotenv(override=True) bug
- [x] Fixed departure_time/arrival_time/outbound_date/return_date column sizes (String(10) → String(20))
- [x] Replaced DB-based API count with SerpApi Account API (get_account_usage())
- [x] Fixed WATCHED_AIRLINES to match exact SerpApi strings (United, American, JAL, EVA Air)
- [x] Fixed save order bug in checker.py — save_flight_records() must run after get_latest_record() loop
- [x] App fully working end-to-end — alerts firing correctly
- [x] Removed FastAPI, uvicorn, APScheduler — project is now a pure background job
- [x] Simplified main.py: init DB → quota check → check prices → send alerts → exit
- [x] Deployment target decided: Azure Container Apps Job (~$5/month, compute free tier)

### Up next
- [ ] Add Docker (Dockerfile)
- [ ] Set up deployment pipeline (GitHub Actions: build → push to ACR → deploy Container Apps Job)
- [ ] Add unit tests

### Future checker.py enhancements (TODO)
- [ ] #2 — Price trend detection (e.g., "dropped 3 times in a row")
- [ ] #6 — Cheapest flight summary per route
- [ ] #7 — Price per stop comparison
- [ ] #8 — Weekend vs weekday price tracking

---

## Key decisions already made
- Python service is a pure background job — no FastAPI, no APScheduler, no web server
- Dashboard on hold — if built later, it will be a separate project reading DB directly (no FastAPI layer needed)
- Deployment: Azure Container Apps Job — external cron scheduling, scale to zero, ~$5/month (just ACR)
- Two separate repos (Python / .NET+Angular) — not a monorepo
- SQL Server over PostgreSQL — reuse existing Azure instance, zero extra cost
- Docker added before first Azure deployment, not from day one of dev
- SQL Server everywhere — local Docker instance for dev, Azure SQL Server for production
- Poetry over plain pip/venv — cleaner dependency management
- Python 3.12.11 via pyenv — stable, full package support
- Poetry installed via Homebrew on Mac
- SendGrid for email alerts (existing account), not smtplib
- Check interval set to 36 hours — 8 calls/check × ~20 checks/month = 160 calls, leaving 90 buffer from the 250 free tier limit
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

WATCH_AIRLINES = {"United", "ANA", "JAL", "Delta", "American", "EVA Air"}
filtered = [f for f in flights if f["flights"][0]["airline"] in WATCH_AIRLINES]
```

---

## Notes for Claude Code in VS Code
- Always use poetry run prefix or activate shell with poetry shell before running Python
- Virtual env path: /Users/tlhuynh/Library/Caches/pypoetry/virtualenvs/flight-tracker-python-w0Eadt9m-py3.12
- Python interpreter to select in VS Code: the executable inside that virtualenv path above
- Do not use pip install directly — always use poetry add to keep pyproject.toml in sync
- The app/ folder is the main package (renamed from default flight_tracker_python/)
