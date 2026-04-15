# Configuration — route, trips to track, and env var loading.
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# SerpApi
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1434"))
DB_NAME = os.getenv("DB_NAME", "FlightTracker")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Single route to track
ROUTE = {"departure": "IAH", "arrival": "NRT"}

# Fixed trips to track — set outbound and return dates manually.
# Maximum 8 trips to stay within SerpApi free tier (250 calls/month at daily runs).
TRIPS = [
    {"outbound_date": "2026-06-07", "return_date": "2026-06-21"},
    {"outbound_date": "2026-06-14", "return_date": "2026-06-28"},
    {"outbound_date": "2026-06-21", "return_date": "2026-07-05"},
    {"outbound_date": "2026-07-04", "return_date": "2026-07-18"},
]
