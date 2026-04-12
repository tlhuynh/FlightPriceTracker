# Tests for serpapi.py — verifies filtering logic and safe error handling.
#
# Both functions make real HTTP calls, so we mock httpx.get to return fake
# responses. This keeps tests fast and free — no SerpApi key or quota needed.

from unittest.mock import patch, MagicMock
from app.serpapi import fetch_flights, get_account_usage


def make_api_flight(airline, flight_number="UA837", price=800):
    """
    Build a raw flight dict in the shape SerpApi actually returns.
    This is different from the normalised dict fetch_flights() produces —
    it's the raw JSON structure before we flatten it.
    """
    return {
        "flights": [
            {
                "airline": airline,
                "flight_number": flight_number,
                "departure_airport": {"time": "10:00"},
                "arrival_airport": {"time": "14:00"},
            }
        ],
        "price": price,
        "total_duration": 840,
    }


def make_httpx_response(body: dict, status_code: int = 200):
    """
    Build a mock that looks like an httpx.Response.
    fetch_flights() calls response.raise_for_status() then response.json(),
    so we need both methods on the mock.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = body
    # raise_for_status is a no-op for 200; for error codes we make it raise
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return mock_response


# --- fetch_flights tests ---

def test_filters_out_unwatched_airlines():
    # SerpApi returns flights from many airlines. fetch_flights() should only keep
    # the ones in WATCHED_AIRLINES — everything else is ignored.
    api_response = {
        "best_flights": [
            make_api_flight("United"),       # watched — should be included
            make_api_flight("Lufthansa"),    # not watched — should be excluded
        ],
        "other_flights": [],
    }

    with patch("httpx.get", return_value=make_httpx_response(api_response)):
        results = fetch_flights("IAH", "NRT", "2026-06-01", "2026-06-15")

    assert len(results) == 1
    assert results[0]["airline"] == "United"


def test_combines_best_and_other_flights():
    # SerpApi splits results into best_flights and other_flights. fetch_flights()
    # should include both so we don't miss any watched airline that lands in other_flights.
    api_response = {
        "best_flights": [make_api_flight("United")],
        "other_flights": [make_api_flight("JAL", flight_number="JL61")],
    }

    with patch("httpx.get", return_value=make_httpx_response(api_response)):
        results = fetch_flights("IAH", "NRT", "2026-06-01", "2026-06-15")

    airlines = [r["airline"] for r in results]
    assert "United" in airlines
    assert "JAL" in airlines
    assert len(results) == 2


def test_returns_empty_list_when_no_watched_airlines():
    # If no watched airlines appear in the response, return an empty list — not an error.
    api_response = {
        "best_flights": [make_api_flight("Lufthansa"), make_api_flight("Air France")],
        "other_flights": [],
    }

    with patch("httpx.get", return_value=make_httpx_response(api_response)):
        results = fetch_flights("IAH", "NRT", "2026-06-01", "2026-06-15")

    assert results == []


def test_normalises_flight_fields():
    # fetch_flights() flattens the nested SerpApi structure into a flat dict.
    # Verify the key fields are present and correctly mapped.
    api_response = {
        "best_flights": [make_api_flight("United", flight_number="UA837", price=750)],
        "other_flights": [],
    }

    with patch("httpx.get", return_value=make_httpx_response(api_response)):
        results = fetch_flights("IAH", "NRT", "2026-06-01", "2026-06-15")

    flight = results[0]
    assert flight["airline"] == "United"
    assert flight["flight_number"] == "UA837"
    assert flight["price"] == 750
    assert flight["departure"] == "IAH"
    assert flight["arrival"] == "NRT"
    assert flight["departure_time"] == "10:00"


# --- get_account_usage tests ---

def test_account_usage_returns_counts():
    # Happy path — SerpApi account API returns usage numbers.
    api_response = {"this_month_usage": 10, "plan_searches_left": 240}

    with patch("httpx.get", return_value=make_httpx_response(api_response)):
        result = get_account_usage()

    assert result["this_month_usage"] == 10
    assert result["plan_searches_left"] == 240


def test_account_usage_returns_none_on_failure():
    # If the account API call fails (network error, bad key, etc.), get_account_usage()
    # should return None rather than crashing. The caller handles None gracefully by
    # skipping the rate limit check and proceeding anyway.
    with patch("httpx.get", side_effect=Exception("network error")):
        result = get_account_usage()

    assert result is None
