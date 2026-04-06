# Entry point — starts the APScheduler and FastAPI web server together.
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.db import init_db
from app.scheduler import start_scheduler

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
    logger.info("Flight Tracker started successfully.")
    yield
    # Shutdown (runs when the app stops)
    logger.info("Shutting down Flight Tracker...")


app = FastAPI(title="Flight Tracker API", lifespan=lifespan)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
