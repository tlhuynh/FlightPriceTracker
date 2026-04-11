# Entry point — starts the APScheduler and FastAPI web server together.
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_db, get_monthly_api_call_count
from app.config import ROUTES, get_travel_dates
from app.scheduler import start_scheduler, price_check_job
from app.api.routes import router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Flight Tracker...")
    init_db()
    start_scheduler()

    # Initial run to check prices immediately on startup (optional, but can be useful to get initial data and alerts without waiting for the first scheduled run).
    calls_needed = sum(len(get_travel_dates(r["trip_lengths"])) for r in ROUTES)
    api_call_count = get_monthly_api_call_count()

    if api_call_count + calls_needed <= 240:
        logger.info("Running initial price check on startup...")
        price_check_job()
        remaining = 250 - api_call_count - calls_needed
        logger.info(
            "Initial price check complete. Approximately %d SerpApi calls remaining this month.",
            remaining,
        )
    else:
        logger.warning(
            "Skipping initial price check — %d/250 API calls used this month, need %d more but would exceed safe threshold.",
            api_call_count,
            calls_needed,
        )

    logger.info("Flight Tracker started successfully.")
    yield
    # Shutdown (runs when the app stops)
    logger.info("Shutting down Flight Tracker...")


app = FastAPI(title="Flight Tracker API", lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
