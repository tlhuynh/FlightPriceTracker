import pytest
from unittest.mock import patch, MagicMock
from app.serpapi import fetch_flights, get_account_usage


MOCK_API_RESPONSE = {
    "best_flights": [
        {
            "flights": [
                {
                    "airline": "EVA Air",
                    "flight_number": "BR 51",
                    "departure_airport": {"time": "2026-06-07 01:00"},
                    "arrival_airport": {"time": "2026-06-08 09:55"},
                }
            ],
            "price": 870,
            "total_duration": 1255,
        },
        {
            "flights": [
                {
                    "airline": "Qatar Airways",  # not in WATCHED_AIRLINES
                    "flight_number": "QR 714",
                    "departure_airport": {"time": "2026-06-07 18:15"},
                    "arrival_airport": {"time": "2026-06-08 16:50"},
                }
            ],
            "price": 950,
            "total_duration": 1525,
        },
    ],
    "other_flights": [],
    "price_insights": {
        "lowest_price": 870,
        "price_level": "low",
        "typical_price_range": [870, 1150],
    },
}


@patch("app.serpapi.httpx.get")
def test_fetch_flights_filters_watched_airlines(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_API_RESPONSE)
    result = fetch_flights("IAH", "NRT", "2026-06-07", "2026-06-21")
    airlines = [f["airline"] for f in result["flights"]]
    assert "EVA Air" in airlines
    assert "Qatar Airways" not in airlines


@patch("app.serpapi.httpx.get")
def test_fetch_flights_returns_price_insights(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_API_RESPONSE)
    result = fetch_flights("IAH", "NRT", "2026-06-07", "2026-06-21")
    assert result["price_insights"]["lowest_price"] == 870
    assert result["price_insights"]["price_level"] == "low"
    assert result["price_insights"]["typical_low"] == 870
    assert result["price_insights"]["typical_high"] == 1150


@patch("app.serpapi.httpx.get")
def test_fetch_flights_missing_price_insights(mock_get):
    response = {**MOCK_API_RESPONSE, "price_insights": {}}
    mock_get.return_value = MagicMock(status_code=200, json=lambda: response)
    result = fetch_flights("IAH", "NRT", "2026-06-07", "2026-06-21")
    assert result["price_insights"]["lowest_price"] is None
    assert result["price_insights"]["typical_low"] is None


@patch("app.serpapi.httpx.get")
def test_fetch_flights_raises_on_error(mock_get):
    mock_get.return_value = MagicMock(status_code=500)
    mock_get.return_value.raise_for_status.side_effect = Exception("API error")
    with pytest.raises(Exception):
        fetch_flights("IAH", "NRT", "2026-06-07", "2026-06-21")


@patch("app.serpapi.httpx.get")
def test_get_account_usage_success(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"this_month_usage": 10, "plan_searches_left": 240},
    )
    result = get_account_usage()
    assert result is not None
    assert result["plan_searches_left"] == 240
    assert result["this_month_usage"] == 10


@patch("app.serpapi.httpx.get", side_effect=Exception("network error"))
def test_get_account_usage_returns_none_on_failure(mock_get):
    result = get_account_usage()
    assert result is None
