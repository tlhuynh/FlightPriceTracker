# Price checker — fetches new prices, compares against last saved price, triggers alerts on changes.
import logging
from app.config import ROUTES, ALERT_THRESHOLD_USD, get_travel_dates
from app.serpapi import fetch_flights
from app.db import (
    save_flight_records,
    get_latest_record,
    get_previous_flight_numbers,
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
    calls_needed = sum(len(get_travel_dates(r["trip_lengths"])) for r in ROUTES)
    if api_call_count + calls_needed > 250:
        logger.warning(
            "Rate limit warning: %d/250 API calls used this month. Need %d more but would exceed limit.",
            api_call_count,
            calls_needed,
        )
        return [
            {
                "error": f"Rate limit warning: {api_call_count}/250 API calls used this month. Need {calls_needed} more but would exceed limit."
            }
        ]

    logger.info(
        "API call count this month: %d. Calls needed for this check: %d.",
        api_call_count,
        calls_needed,
    )
    alerts = []

    for route in ROUTES:
        travel_dates = get_travel_dates(route["trip_lengths"])
        logger.info(
            "Checking flight information for route: %s → %s",
            route["departure"],
            route["arrival"],
        )
        for travel_date in travel_dates:
            outbound_date = travel_date["outbound_date"]
            return_date = travel_date["return_date"]
            try:
                log_api_call("serpapi", f"{route['departure']}-{route['arrival']}")
                flights = fetch_flights(
                    route["departure"], route["arrival"], outbound_date, return_date
                )
                # Check for duplicates based on flight number and remove them, since SerpApi can sometimes return duplicates.
                seen = set()
                unique_flights = []
                for f in flights:
                    key = f.get("flight_number")
                    if key and key not in seen:
                        seen.add(key)
                        unique_flights.append(f)
                    elif key and key in seen:
                        # Log that we're skipping a duplicate flight based on flight number.
                        logger.debug(
                            "Duplicate flight %s skipped for %s → %s on %s – %s.",
                            key,
                            route["departure"],
                            route["arrival"],
                            outbound_date,
                            return_date,
                        )
                    elif not key:
                        # Still include flights without a flight number, but log that we're doing so.
                        logger.warning(
                            "Flight without flight number found for route %s → %s on %s – %s. Including in results but cannot check for duplicates.",
                            route["departure"],
                            route["arrival"],
                            outbound_date,
                            return_date,
                        )
                        unique_flights.append(f)

                if len(unique_flights) < len(flights):
                    logger.warning(
                        "Filtered out %d duplicate flights for route %s → %s on %s – %s.",
                        len(flights) - len(unique_flights),
                        route["departure"],
                        route["arrival"],
                        outbound_date,
                        return_date,
                    )

                # Filter out flights with missing or zero price, since those are likely errors in the data and would cause false alerts.
                valid_flights = [
                    f for f in unique_flights if f.get("price") and f["price"] > 0
                ]

                if len(valid_flights) < len(unique_flights):
                    logger.warning(
                        "Filtered out %d flights with invalid prices for route %s → %s on %s – %s.",
                        len(unique_flights) - len(valid_flights),
                        route["departure"],
                        route["arrival"],
                        outbound_date,
                        return_date,
                    )

                # Get previous flights before saving new ones
                previous_flights = get_previous_flight_numbers(
                    route["departure"], route["arrival"], outbound_date
                )

                # Save all valid flights to the database
                save_flight_records(valid_flights)

                # Check for disappeared flights
                current_flight_numbers = {
                    f["flight_number"] for f in valid_flights if f.get("flight_number")
                }

                for prev in previous_flights:
                    if prev["flight_number"] not in current_flight_numbers:
                        logger.info(
                            "Flight disappeared: %s %s on route %s → %s on %s – %s (was $%s).",
                            prev["airline"],
                            prev["flight_number"],
                            route["departure"],
                            route["arrival"],
                            outbound_date,
                            return_date,
                            prev["price"],
                        )
                        alerts.append(
                            {
                                "type": "disappeared_flight",
                                "airline": prev["airline"],
                                "flight_number": prev["flight_number"],
                                "route": f"{route['departure']} → {route['arrival']}",
                                "last_price": prev["price"],
                                "outbound_date": outbound_date,
                                "return_date": return_date,
                            }
                        )

                logger.info(
                    "Fetched and saved %d flights for route %s → %s on %s – %s.",
                    len(valid_flights),
                    route["departure"],
                    route["arrival"],
                    outbound_date,
                    return_date,
                )

                # Handle per flight checking and alerts
                for flight in valid_flights:
                    # Handle flight without flight number
                    if not flight.get("flight_number"):
                        logger.warning(
                            "Skipping price check for flight without flight number for route %s → %s on %s – %s, since we cannot reliably identify it.",
                            route["departure"],
                            route["arrival"],
                            outbound_date,
                            return_date,
                        )
                        alerts.append(
                            {
                                "type": "untracked_flight",
                                "airline": flight["airline"],
                                "route": f"{flight['departure']} → {flight['arrival']}",
                                "price": flight["price"],
                                "outbound_date": outbound_date,
                                "return_date": return_date,
                                "departure_time": flight.get("departure_time"),
                                "arrival_time": flight.get("arrival_time"),
                                "stops": flight.get("stops"),
                                "note": "Flight has no flight number — saved but cannot track price changes.",
                            }
                        )
                        continue

                    # Flight with flight number

                    # Look up the most recent record for this specific flight
                    # (same route, airline, flight number, and date) to compare prices.
                    previous = get_latest_record(
                        flight["departure"],
                        flight["arrival"],
                        flight["airline"],
                        flight["flight_number"],
                        flight["outbound_date"],
                    )
                    # No previous record -> new flight
                    if previous is None:
                        logger.info(
                            "New flight found: %s %s on route %s → %s on %s – %s at $%s.",
                            flight["airline"],
                            flight["flight_number"],
                            flight["departure"],
                            flight["arrival"],
                            outbound_date,
                            return_date,
                            flight["price"],
                        )
                        alerts.append(
                            {
                                "type": "new_flight",
                                "airline": flight["airline"],
                                "flight_number": flight["flight_number"],
                                "route": f"{flight['departure']} → {flight['arrival']}",
                                "price": flight["price"],
                                "outbound_date": outbound_date,
                                "return_date": return_date,
                            }
                        )
                    elif (  # Found previous record of same flight, check for price change
                        previous.price is not None and flight["price"] is not None
                    ):
                        diff = flight["price"] - previous.price
                        if abs(diff) >= ALERT_THRESHOLD_USD:
                            logger.info(
                                "Price change alert for %s on route %s → %s on %s – %s: old price $%s, new price $%s, change $%s.",
                                flight["airline"],
                                flight["departure"],
                                flight["arrival"],
                                outbound_date,
                                return_date,
                                previous.price,
                                flight["price"],
                                diff,
                            )
                            alerts.append(
                                {
                                    "type": "price_change",
                                    "airline": flight["airline"],
                                    "route": f"{flight['departure']} → {flight['arrival']}",
                                    "old_price": previous.price,
                                    "new_price": flight["price"],
                                    "change": diff,
                                    "outbound_date": outbound_date,
                                    "return_date": return_date,
                                }
                            )
            except Exception as e:
                logger.error(
                    "Error checking prices for route %s → %s on %s – %s: %s",
                    route["departure"],
                    route["arrival"],
                    outbound_date,
                    return_date,
                    str(e),
                )

    logger.info("Price check completed. Total alerts generated: %d.", len(alerts))
    return alerts
