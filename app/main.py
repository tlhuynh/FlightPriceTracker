# Entry point — initializes the database, runs a price check, and outputs the report.
import logging
from datetime import datetime

from app.db import init_db, check_db_connection
from app.config import TRIPS, REPORT_OUTPUT_DIR, SENDGRID_API_KEY
from app.serpapi import get_account_usage
from app.checker import check_prices
from app.reporter import build_html, write_html_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

logger = logging.getLogger(__name__)


def run():
    logger.info("Starting Flight Tracker price check...")

    if not check_db_connection():
        logger.error("Database connection failed. Exiting.")
        return

    init_db()

    calls_needed = len(TRIPS)
    usage = get_account_usage()

    if usage is None:
        logger.warning(
            "SerpApi usage check failed — proceeding without rate limit validation."
        )
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
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build_html(findings, checked_at)

    if REPORT_OUTPUT_DIR:
        path = write_html_file(html, REPORT_OUTPUT_DIR)
        logger.info("Report saved to %s", path)
    elif SENDGRID_API_KEY:
        # TODO: implement email sending when deploying
        logger.warning("Email output not yet implemented.")
    else:
        logger.warning(
            "No output configured — set REPORT_OUTPUT_DIR in .env for local use."
        )

    logger.info("Flight Tracker finished. %d trip(s) in report.", len(findings))


if __name__ == "__main__":
    run()
