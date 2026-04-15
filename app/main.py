# Entry point — initializes the database, runs a price check, and prints or exports results.
import sys
import logging

from app.db import init_db, check_db_connection
from app.config import TRIPS
from app.serpapi import get_account_usage
from app.checker import check_prices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)

dry_run = "--dry-run" in sys.argv


def run():
    logger.info("Starting Flight Tracker price check...")

    if not check_db_connection():
        logger.error("Database connection failed. Exiting.")
        return

    init_db()

    calls_needed = len(TRIPS)
    usage = get_account_usage()

    if usage is None:
        logger.warning("SerpApi usage check failed — proceeding without rate limit validation.")
    elif usage["plan_searches_left"] < calls_needed + 10:
        logger.warning(
            "Skipping price check — only %d SerpApi searches left this month, need %d plus 10 call buffer.",
            usage["plan_searches_left"],
            calls_needed,
        )
        return
    else:
        logger.info(
            "SerpApi searches left: %d. Calls needed: %d.",
            usage["plan_searches_left"],
            calls_needed,
        )

    findings = check_prices()

    if dry_run:
        print("\n=== Dry Run Results ===")
        for f in findings:
            print(f)
    else:
        # TODO: print summary or export to file
        for f in findings:
            print(f)

    logger.info("Flight Tracker finished. %d finding(s) this run.", len(findings))


if __name__ == "__main__":
    run()
