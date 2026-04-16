# Configuration — loads route and trips from trips.json, env vars from .env.
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

# SerpApi
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Email (deployed only)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
NOTIFY_EMAILS = os.getenv("NOTIFY_EMAILS", "").split(",")

# Local output (local only)
REPORT_OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "")

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1434"))
DB_NAME = os.getenv("DB_NAME", "FlightTracker")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Airlines to track — only flights from these airlines will be stored and compared.
WATCHED_AIRLINES = {
    "ANA",
    "JAL",
    "EVA Air",
    "Delta",
    "United",
    "American",
}

# Load route and trips from trips.json (gitignored — copy trips.example.json to get started).
try:
    with open("trips.json") as f:
        _trips_config = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(
        "trips.json not found. Copy trips.example.json to trips.json and fill in your route and dates."
    )

ROUTE: dict = _trips_config["route"]
TRIPS: list[dict] = _trips_config["trips"]
