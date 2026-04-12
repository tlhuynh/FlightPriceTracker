# Entry point — initializes the database and runs a single price check with alerts.
import logging

from app.db import init_db
from app.config import ROUTES, get_travel_dates
from app.serpapi import get_account_usage
from app.checker import check_prices
from app.notifier import send_alerts


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)


def run():
    logger.info("Starting Flight Tracker price check...")
    init_db()

    calls_needed = sum(len(get_travel_dates(r["trip_lengths"])) for r in ROUTES)
    usage = get_account_usage()

    if usage is None:
        logger.warning(
            "SerpApi usage check failed — proceeding without rate limit validation."
        )

    if usage is None or usage["plan_searches_left"] >= calls_needed + 10:
        alerts = check_prices()
        send_alerts(alerts)
        if usage is not None:
            logger.info(
                "Price check complete. Approximately %d SerpApi calls remaining this month.",
                usage["plan_searches_left"] - calls_needed,
            )
    else:
        logger.warning(
            "Skipping price check — only %d SerpApi searches left this month, need %d plus 10 call buffer.",
            usage["plan_searches_left"],
            calls_needed,
        )

    logger.info("Flight Tracker finished.")


if __name__ == "__main__":
    run()
