# Flight Prices Tracker

A background job that monitors flight prices for a specific route, saves price history to a SQL Server database, and outputs an HTML report — either as a local file or via email when deployed.

---

## What it does

Runs once per execution, then exits:

1. Checks SerpApi quota — skips the run if not enough searches remain
2. Fetches current flights and price insights from Google Flights via SerpApi for each configured trip
3. Compares the current lowest price against the last saved price in the database
4. Saves route insights and individual flight snapshots to the database
5. Outputs an HTML report — written to a local file or emailed via SendGrid (when deployed)

---

## What the report shows

One section per trip:

- **Lowest price** — cheapest available right now
- **Price level** — Google's verdict: LOW / TYPICAL / HIGH vs historical norms
- **Typical price range** — what Google considers normal for this route and date
- **Price change** — how the lowest price moved since the last run
- **Flight table** — all watched airline flights sorted by price, with flight number, stops, times, and duration

---

## Routes and trips

Route and trip dates are configured in `trips.json` (gitignored — copy from `trips.example.json`).
Airlines to watch are configured in `app/config.py`.

---

## Tech stack

| Layer | Technology |
|---|---|
| Price data | SerpApi (Google Flights) |
| Database | SQL Server (Azure SQL / local Docker) |
| Python DB driver | pyodbc + SQLAlchemy |
| Local output | HTML file |
| Deployed output | SendGrid email |
| Container | Docker |
| Scheduling | Azure Container Apps Job (external cron) |

---

## Project structure

```
app/
├── main.py        — entry point: init DB → quota check → check prices → output report → exit
├── config.py      — airlines, env var loading, trips.json loader
├── checker.py     — fetch price insights + flights, compare against DB, build findings
├── serpapi.py     — SerpApi API client
├── reporter.py    — HTML report builder and file writer
└── db.py          — SQLAlchemy models and DB access functions

tests/
├── test_checker.py   — price comparison logic and error handling
├── test_serpapi.py   — API response parsing and filtering
└── test_reporter.py  — HTML formatting and file output
```

---

## Local setup

**Prerequisites:** Python 3.12, pyenv, Poetry, ODBC Driver 18 for SQL Server, Docker Desktop

```bash
# Clone and set Python version
pyenv local 3.12.11

# Install dependencies
poetry install

# Copy and fill in environment variables
cp .env.example .env

# Copy and fill in trip configuration
cp trips.example.json trips.json
```

Start a local SQL Server instance (Azure SQL Edge — ARM compatible):

```bash
docker run -e "ACCEPT_EULA=1" -e "MSSQL_SA_PASSWORD=<your_password>" \
  -p 1434:1433 \
  mcr.microsoft.com/azure-sql-edge
```

Create the `FlightTracker` database in Azure Data Studio or via `sqlcmd`, then run:

```bash
poetry run python -m app.main
```

The app creates tables automatically on first run. The HTML report is saved to `REPORT_OUTPUT_DIR`.

---

## Environment variables

Copy `.env.example` to `.env` and fill in your values. All variables are documented in that file.

---

## Running tests

```bash
poetry run pytest tests/ -v
```

No real database or API key needed — all external calls are mocked.