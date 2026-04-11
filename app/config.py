# Configuration — routes to watch, airlines, check interval, and env var loading.
import os
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

# Parsed variables from environment (with defaults where appropriate).
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1434"))
DB_NAME = os.getenv("DB_NAME", "FlightTracker")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
NOTIFY_EMAILS = os.getenv(
    "NOTIFY_EMAILS", ""
).split(
    ","
)  # Split by comma for multiple emails; in Python, this automatically creates a list. If NOTIFY_EMAILS is empty, it will be [''] which is fine for our use case.
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "24"))
ALERT_THRESHOLD_USD = int(os.getenv("ALERT_THRESHOLD_USD", "50"))

# Define routes to watch: list of dicts with departure and arrival airport codes.
# TODO: In the future, consider making this dynamic (e.g., from a database or config file) instead of hardcoding.
ROUTES = [
    {"departure": "IAH", "arrival": "NRT"},
    {"departure": "IAH", "arrival": "HND"},
    {"departure": "IAH", "arrival": "SGN"},
]

WATCHED_AIRLINES = {
    "ANA",
    "Japan Airlines",
    "Eva Air",
    "Delta",
    "United Airlines",
    "American Airlines",
}

TRIP_LENGTH_DAYS = 14  # Default trip length in days for outbound date calculations.


# Calculate outbound dates: 30 days (1 month) and 180 days (6 months) from today, in ISO format (YYYY-MM-DD).
# TODO: In the future, consider making these dynamic to change based on user preferences or to add more date options.
def get_travel_dates() -> list[dict]:
    today = date.today()
    outbound_dates = [
        today + timedelta(days=30),
        today + timedelta(days=180),
    ]
    return [
        {
            "outbound_date": d.isoformat(),
            "return_date": (d + timedelta(days=TRIP_LENGTH_DAYS)).isoformat(),
        }
        for d in outbound_dates
    ]
