# SerpApi client — fetches Google Flights data and returns flights + price insights.
import httpx
import logging
from app.config import SERPAPI_KEY, WATCHED_AIRLINES

logger = logging.getLogger(__name__)


def get_account_usage() -> dict | None:
    """Fetch real monthly usage from SerpApi Account API. Returns None if the call fails.
    This call is free and does not count toward the monthly search quota.
    Ref: https://serpapi.com/account-api
    """
    try:
        response = httpx.get(
            "https://serpapi.com/account", params={"api_key": SERPAPI_KEY}
        )
        response.raise_for_status()
        data = response.json()
        logger.info(
            "SerpApi usage: %d searches used this month, %d searches left.",
            data.get("this_month_usage", 0),
            data.get("plan_searches_left", 0),
        )
        return {
            "this_month_usage": data.get("this_month_usage", 0),
            "plan_searches_left": data.get("plan_searches_left", 0),
        }
    except Exception as e:
        logger.warning(
            "Failed to fetch SerpApi account usage. Rate limit check will be skipped. Error: %s",
            str(e),
        )
        return None


def fetch_flights(
    departure: str, arrival: str, outbound_date: str, return_date: str
) -> dict:
    """Fetch flights and price insights for a given route and trip dates.

    Returns a dict with:
      - flights: list of watched airline flights with details
      - price_insights: lowest_price, price_level, typical_low, typical_high
    """
    params = {
        "engine": "google_flights",
        "departure_id": departure,
        "arrival_id": arrival,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "USD",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    logger.debug("SerpApi request params: %s", params)
    logger.info(
        "Fetching flights from SerpApi: %s → %s on %s, return on %s",
        departure,
        arrival,
        outbound_date,
        return_date,
    )

    response = httpx.get("https://serpapi.com/search", params=params)
    if response.status_code != 200:
        logger.error(
            "SerpApi request failed with status %d for %s → %s",
            response.status_code,
            departure,
            arrival,
        )
    response.raise_for_status()
    data = response.json()

    # Extract price insights
    raw_insights = data.get("price_insights", {})
    typical_range = raw_insights.get("typical_price_range", [None, None])
    price_insights = {
        "lowest_price": raw_insights.get("lowest_price"),
        "price_level": raw_insights.get("price_level"),
        "typical_low": typical_range[0] if typical_range else None,
        "typical_high": typical_range[1] if typical_range else None,
    }

    # Extract watched airline flights
    all_flights = data.get("best_flights", []) + data.get("other_flights", [])
    logger.info(
        "SerpApi returned %d total flights for %s → %s",
        len(all_flights),
        departure,
        arrival,
    )

    flights = []
    for flight in all_flights:
        airline = flight["flights"][0]["airline"]
        if airline in WATCHED_AIRLINES:
            flights.append(
                {
                    "airline": airline,
                    "flight_number": flight["flights"][0].get("flight_number"),
                    "price": flight.get("price"),
                    "departure": departure,
                    "arrival": arrival,
                    "outbound_date": outbound_date,
                    "return_date": return_date,
                    "departure_time": flight["flights"][0]
                    .get("departure_airport", {})
                    .get("time"),
                    "arrival_time": flight["flights"][-1]
                    .get("arrival_airport", {})
                    .get("time"),
                    "stops": len(flight["flights"]) - 1,
                    "total_duration": flight.get("total_duration"),
                }
            )

    logger.info(
        "Filtered to %d watched airline flights for %s → %s",
        len(flights),
        departure,
        arrival,
    )

    return {"flights": flights, "price_insights": price_insights}
