# SerpApi client — calls Google Flights API and returns prices filtered to watched airlines.
import httpx

from app.config import SERPAPI_KEY, WATCHED_AIRLINES


def fetch_flights(departure: str, arrival: str, outbound_date: str) -> list[dict]:
    params = {
        "engine": "google_flights",
        "departure_id": departure,
        "arrival_id": arrival,
        "outbound_date": outbound_date,
        "currency": "USD",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }

    response = httpx.get(
        "https://serpapi.com/search", params=params
    )  # Make the API request to SerpApi with the specified parameters
    response.raise_for_status()  # Raise an exception for HTTP errors (e.g., 4xx or 5xx responses)
    data = response.json()

    all_flights = data.get("best_flights", []) + data.get("other_flights", [])

    results = []
    for flight in all_flights:
        airline = flight["flights"][0]["airline"]
        if airline in WATCHED_AIRLINES:
            results.append(
                {
                    "airline": airline,
                    "flight_number": flight["flights"][0].get("flight_number"),
                    "price": flight.get("price"),
                    "departure": departure,
                    "arrival": arrival,
                    "outbound_date": outbound_date,
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

    return results
