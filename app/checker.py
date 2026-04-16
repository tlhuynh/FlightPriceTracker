# Price checker — fetches price insights and flights per trip, compares against last run, returns findings.
import logging
from app.config import ROUTE, TRIPS
from app.serpapi import fetch_flights, get_account_usage
from app.db import (
    save_route_insight,
    get_latest_route_insight,
    save_flight_snapshots,
    log_api_call,
    check_db_connection,
)

logger = logging.getLogger(__name__)


def check_prices() -> list[dict]:
    logger.info("Starting price check...")

    if not check_db_connection():
        logger.error("Database connection failed.")
        return [{"type": "error", "error": "Database connection failed."}]

    usage = get_account_usage()
    calls_needed = len(TRIPS)

    if usage is not None and usage["plan_searches_left"] < calls_needed + 10:
        logger.warning(
            "Rate limit warning: only %d SerpApi searches left, need %d. Skipping check.",
            usage["plan_searches_left"],
            calls_needed,
        )
        return [
            {
                "type": "error",
                "error": f"Only {usage['plan_searches_left']} SerpApi searches left, need {calls_needed}.",
            }
        ]

    findings = []
    departure = ROUTE["departure"]
    arrival = ROUTE["arrival"]

    for trip in TRIPS:
        outbound_date = trip["outbound_date"]
        return_date = trip["return_date"]

        try:
            log_api_call("serpapi", f"{departure}-{arrival}")
            result = fetch_flights(departure, arrival, outbound_date, return_date)

            price_insights = result["price_insights"]
            flights = result["flights"]
            lowest_price = price_insights.get("lowest_price")
            price_level = price_insights.get("price_level")
            typical_low = price_insights.get("typical_low")
            typical_high = price_insights.get("typical_high")

            # Compare against last run
            previous = get_latest_route_insight(
                departure, arrival, outbound_date, return_date
            )

            finding = {
                "type": "first_check" if previous is None else "update",
                "route": f"{departure} → {arrival}",
                "outbound_date": outbound_date,
                "return_date": return_date,
                "lowest_price": lowest_price,
                "previous_price": previous.lowest_price if previous else None,
                "price_level": price_level,
                "typical_low": typical_low,
                "typical_high": typical_high,
                "flights": flights,
            }

            # Add price change only if price moved
            if (
                previous
                and previous.lowest_price is not None
                and lowest_price is not None
            ):
                diff = lowest_price - previous.lowest_price
                if diff != 0:
                    finding["price_change"] = diff

            logger.info(
                "%s → %s on %s: $%s (%s)%s",
                departure,
                arrival,
                outbound_date,
                lowest_price,
                price_level,
                f" — change: {finding['price_change']:+.0f}"
                if "price_change" in finding
                else "",
            )

            # Save to DB
            save_route_insight(
                {
                    "departure": departure,
                    "arrival": arrival,
                    "outbound_date": outbound_date,
                    "return_date": return_date,
                    "lowest_price": lowest_price,
                    "price_level": price_level,
                    "typical_low": typical_low,
                    "typical_high": typical_high,
                }
            )
            save_flight_snapshots(flights)
            findings.append(finding)

        except Exception as e:
            logger.error(
                "Error checking %s → %s on %s: %s",
                departure,
                arrival,
                outbound_date,
                str(e),
            )
            findings.append(
                {
                    "type": "error",
                    "route": f"{departure} → {arrival}",
                    "outbound_date": outbound_date,
                    "return_date": return_date,
                    "error": str(e),
                }
            )

    logger.info("Price check complete. %d trip(s) checked.", len(TRIPS))
    return findings
