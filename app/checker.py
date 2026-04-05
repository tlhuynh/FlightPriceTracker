# Price checker — fetches new prices, compares against last saved price, triggers alerts on changes.
from app.config import ROUTES, ALERT_THRESHOLD_USD, get_outbound_dates
from app.serpapi import fetch_flights
from app.db import save_flight_records, get_latest_record, check_db_connection, log_api_call, get_monthly_api_call_count


# Main function to check prices and generate alerts
def check_prices():
    if not check_db_connection():
        return [
            {
                "error": "Database connection failed. Please check your DATABASE_URL and ensure the database is running."
            }
        ]
    
    api_call_count = get_monthly_api_call_count()
    outbound_dates = get_outbound_dates()
    calls_needed = len(ROUTES) * len(outbound_dates)
    if api_call_count + calls_needed > 100:
        return [{"error": f"Rate limit warning: {api_call_count}/100 API calls used this month. Need {calls_needed} more but would exceed limit."}]

    alerts = []

    for route in ROUTES:
        for outbound_date in outbound_dates:
            log_api_call("serpapi", f"{route['departure']}-{route['arrival']}")
            flights = fetch_flights(route["departure"], route["arrival"], outbound_date)
            save_flight_records(flights)

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

    return alerts
