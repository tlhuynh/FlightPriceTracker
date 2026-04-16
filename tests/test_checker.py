from unittest.mock import patch, MagicMock
from app.checker import check_prices


MOCK_FETCH_RESULT = {
    "price_insights": {
        "lowest_price": 870,
        "price_level": "low",
        "typical_low": 870,
        "typical_high": 1150,
    },
    "flights": [
        {
            "airline": "EVA Air",
            "flight_number": "BR 51",
            "price": 870,
            "stops": 1,
            "departure_time": "2026-06-07 01:00",
            "arrival_time": "2026-06-08 09:55",
            "total_duration": 1255,
            "departure": "IAH",
            "arrival": "NRT",
            "outbound_date": "2026-06-07",
            "return_date": "2026-06-21",
        }
    ],
}

MOCK_TRIPS = [{"outbound_date": "2026-06-07", "return_date": "2026-06-21"}]
MOCK_ROUTE = {"departure": "IAH", "arrival": "NRT"}


@patch("app.checker.check_db_connection", return_value=True)
@patch("app.checker.get_account_usage", return_value={"plan_searches_left": 100})
@patch("app.checker.log_api_call")
@patch("app.checker.save_route_insight")
@patch("app.checker.save_flight_snapshots")
@patch("app.checker.fetch_flights", return_value=MOCK_FETCH_RESULT)
@patch("app.checker.get_latest_route_insight", return_value=None)
@patch("app.checker.TRIPS", MOCK_TRIPS)
@patch("app.checker.ROUTE", MOCK_ROUTE)
def test_first_check_finding(
    mock_latest,
    mock_fetch,
    mock_save_flights,
    mock_save_insight,
    mock_log,
    mock_usage,
    mock_db,
):
    findings = check_prices()
    assert len(findings) == 1
    assert findings[0]["type"] == "first_check"
    assert findings[0]["lowest_price"] == 870
    assert findings[0]["price_level"] == "low"


@patch("app.checker.check_db_connection", return_value=True)
@patch("app.checker.get_account_usage", return_value={"plan_searches_left": 100})
@patch("app.checker.log_api_call")
@patch("app.checker.save_route_insight")
@patch("app.checker.save_flight_snapshots")
@patch("app.checker.fetch_flights", return_value=MOCK_FETCH_RESULT)
@patch("app.checker.TRIPS", MOCK_TRIPS)
@patch("app.checker.ROUTE", MOCK_ROUTE)
def test_update_finding_with_price_drop(
    mock_fetch, mock_save_flights, mock_save_insight, mock_log, mock_usage, mock_db
):
    previous = MagicMock()
    previous.lowest_price = 950

    with patch("app.checker.get_latest_route_insight", return_value=previous):
        findings = check_prices()

    assert findings[0]["type"] == "update"
    assert findings[0]["price_change"] == -80


@patch("app.checker.check_db_connection", return_value=True)
@patch("app.checker.get_account_usage", return_value={"plan_searches_left": 100})
@patch("app.checker.log_api_call")
@patch("app.checker.save_route_insight")
@patch("app.checker.save_flight_snapshots")
@patch("app.checker.fetch_flights", return_value=MOCK_FETCH_RESULT)
@patch("app.checker.TRIPS", MOCK_TRIPS)
@patch("app.checker.ROUTE", MOCK_ROUTE)
def test_update_finding_no_price_change(
    mock_fetch, mock_save_flights, mock_save_insight, mock_log, mock_usage, mock_db
):
    previous = MagicMock()
    previous.lowest_price = 870

    with patch("app.checker.get_latest_route_insight", return_value=previous):
        findings = check_prices()

    assert findings[0]["type"] == "update"
    assert "price_change" not in findings[0]


@patch("app.checker.check_db_connection", return_value=False)
def test_db_connection_failure(mock_db):
    findings = check_prices()
    assert len(findings) == 1
    assert findings[0]["type"] == "error"


@patch("app.checker.check_db_connection", return_value=True)
@patch("app.checker.get_account_usage", return_value={"plan_searches_left": 5})
@patch("app.checker.TRIPS", MOCK_TRIPS)
@patch("app.checker.ROUTE", MOCK_ROUTE)
def test_rate_limit_skip(mock_usage, mock_db):
    findings = check_prices()
    assert findings[0]["type"] == "error"
    assert "searches left" in findings[0]["error"]
