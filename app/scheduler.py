# Scheduler — configures APScheduler to run the price checker on a recurring interval.
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import CHECK_INTERVAL_HOURS
from app.checker import check_prices
from app.notifier import send_alerts

logger = logging.getLogger(__name__)


# Job function that runs the price check and sends alerts. This is the function that APScheduler will call on the defined interval.
def price_check_job():
    logger.info("Scheduled price check triggered.")
    alerts = check_prices()
    send_alerts(alerts)


# Start the APScheduler to run the price_check_job on a recurring interval defined by CHECK_INTERVAL_HOURS.
# This function should be called when the application starts to initialize the scheduler.
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        price_check_job,
        "interval",
        hours=CHECK_INTERVAL_HOURS,
    )
    scheduler.start()
    logger.info("Scheduler started. Running every %d hours.", CHECK_INTERVAL_HOURS)
    return scheduler
