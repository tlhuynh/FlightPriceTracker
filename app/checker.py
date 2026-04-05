# Price checker — fetches new prices, compares against last saved price, triggers alerts on changes.
import logging
from app.config import ROUTES, ALERT_THRESHOLD_USD, get_outbound_dates
from app.serpapi import fetch_flights
from app.db import (
    save_flight_records,
    get_latest_record,
    check_db_connection,
    log_api_call,
    get_monthly_api_call_count,
)

logger = logging.getLogger(__name__)


# Main function to check prices and generate alerts
def check_prices():
    logger.info("Starting price check...")
    if not check_db_connection():
        logger.error(
            "Database connection failed. Please check your DATABASE_URL and ensure the database is running."
        )
        return [
            {
                "error": "Database connection failed. Please check your DATABASE_URL and ensure the database is running."
            }
        ]

    api_call_count = get_monthly_api_call_count()
    outbound_dates = get_outbound_dates()
    calls_needed = len(ROUTES) * len(outbound_dates)
    if api_call_count + calls_needed > 100:
        logger.warning(
            "Rate limit warning: %d/100 API calls used this month. Need %d more but would exceed limit.",
            api_call_count,
            calls_needed,
        )
        return [
            {
                "error": f"Rate limit warning: {api_call_count}/100 API calls used this month. Need {calls_needed} more but would exceed limit."
            }
        ]

    logger.info(
        "API call count this month: %d. Calls needed for this check: %d.",
        api_call_count,
        calls_needed,
    )
    alerts = []

    for route in ROUTES:
        logger.info(
            "Checking flight information for route: %s → %s",
            route["departure"],
            route["arrival"],
        )
        for outbound_date in outbound_dates:
            log_api_call("serpapi", f"{route['departure']}-{route['arrival']}")
            flights = fetch_flights(route["departure"], route["arrival"], outbound_date)
            save_flight_records(flights)

            logger.info(
                "Fetched and saved %d flights for route %s → %s on %s.",
                len(flights),
                route["departure"],
                route["arrival"],
                outbound_date,
            )

            for flight in flights:
                previous = get_latest_record(
                    flight["departure"], flight["arrival"], flight["airline"]
                )

                if (
                    previous is not None
                    and previous.price is not None
                    and flight["price"] is not None
                ):
                    diff = flight["price"] - previous.price
                    if abs(diff) >= ALERT_THRESHOLD_USD:
                        logger.info(
                            "Price change alert for %s on route %s → %s on %s: old price $%s, new price $%s, change $%s.",
                            flight["airline"],
                            flight["departure"],
                            flight["arrival"],
                            flight["outbound_date"],
                            previous.price,
                            flight["price"],
                            diff,
                        )
                        alerts.append(
                            {
                                "airline": flight["airline"],
                                "route": f"{flight['departure']} → {flight['arrival']}",
                                "old_price": previous.price,
                                "new_price": flight["price"],
                                "change": diff,
                                "outbound_date": flight["outbound_date"],
                            }
                        )

    logger.info("Price check completed. Total alerts generated: %d.", len(alerts))
    return alerts
