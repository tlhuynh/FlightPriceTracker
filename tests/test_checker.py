# Tests for checker.py — verifies price comparison, alert logic, dedup, and filtering.
#
# Strategy: check_prices() calls the DB and SerpApi internally, so every external
# call is replaced with a mock. This lets us feed in exactly the data we want and
# assert on the findings returned — no real database or network required.
#
# The key mocking rule in Python: patch the name where it's *used*, not where it's
# defined. checker.py does `from app.serpapi import fetch_flights`, so the live
# function now lives at app.checker.fetch_flights. Patching app.serpapi.fetch_flights
# would have no effect — checker.py already holds its own reference.

from unittest.mock import patch, MagicMock
from app.checker import check_prices


# --- Helpers ---

def make_flight(airline="United", flight_number="UA837", price=800):
    """
    Build a minimal flight dict that matches the shape fetch_flights() returns.
    Tests override only the fields they care about (e.g. price or flight_number).
    """
    return {
        "airline": airline,
        "flight_number": flight_number,
        "price": price,
        "departure": "IAH",
        "arrival": "NRT",
        "outbound_date": "2026-06-01",
        "return_date": "2026-06-15",
        "departure_time": "10:00",
        "arrival_time": "14:00",
        "stops": 0,
        "total_duration": 840,
    }


def make_record(price):
    """
    Build a mock FlightRecord object. checker.py only reads `.price` from it,
    so a MagicMock with just that attribute set is enough.
    """
    record = MagicMock()
    record.price = price
    return record


# A single route and a single date pair — enough to exercise all logic paths
# without the noise of looping over every real route and date in config.
SINGLE_ROUTE = [{"departure": "IAH", "arrival": "NRT", "trip_lengths": [14]}]
SINGLE_DATE = [{"outbound_date": "2026-06-01", "return_date": "2026-06-15"}]


def run_check(
    fetched_flights,
    latest_record=None,
    previous_flights=None,
    db_ok=True,
    usage=None,
    alert_threshold=50,
):
    """
    Run check_prices() with all external dependencies mocked.
    Each parameter controls one specific variable; everything else is a safe no-op.

    - fetched_flights:  what SerpApi returns for this route/date
    - latest_record:    the most recent DB row for a flight (None = never seen before)
    - previous_flights: flight numbers from the last check (for disappeared-flight detection)
    - db_ok:            whether the DB connection check passes
    - usage:            SerpApi quota response
    - alert_threshold:  min price change (USD) before an alert fires
    """
    if previous_flights is None:
        previous_flights = []
    if usage is None:
        usage = {"plan_searches_left": 100, "this_month_usage": 0}

    with (
        # Replace ROUTES so the loop runs exactly once with our test route
        patch("app.checker.ROUTES", SINGLE_ROUTE),
        # Replace get_travel_dates so it returns one date pair, not real computed dates
        patch("app.checker.get_travel_dates", return_value=SINGLE_DATE),
        # Pin the threshold so tests don't depend on the .env value
        patch("app.checker.ALERT_THRESHOLD_USD", alert_threshold),
        # Control whether the DB connection check passes
        patch("app.checker.check_db_connection", return_value=db_ok),
        # Control the SerpApi quota response
        patch("app.checker.get_account_usage", return_value=usage),
        # Control what SerpApi returns for flights this run
        patch("app.checker.fetch_flights", return_value=fetched_flights),
        # Control the previous price record from the DB (or None if first-ever record)
        patch("app.checker.get_latest_record", return_value=latest_record),
        # Control which flight numbers were seen in the last check
        patch("app.checker.get_previous_flight_numbers", return_value=previous_flights),
        # Silence the DB write — we don't want tests to hit a real database
        patch("app.checker.save_flight_records"),
        # Silence the API call log write
        patch("app.checker.log_api_call"),
    ):
        return check_prices()


# --- Tests ---

def test_new_flight_alert():
    # When a flight has no previous DB record, it's the first time we've seen it.
    # checker.py should emit a new_flight alert so we know a new option appeared.
    findings = run_check(
        fetched_flights=[make_flight(price=800)],
        latest_record=None,  # None = get_latest_record returned nothing = first ever record
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "new_flight"
    assert findings[0]["price"] == 800
    assert findings[0]["airline"] == "United"


def test_price_change_alert_fires_at_threshold():
    # Previous price $800, new price $700 → $100 drop, which meets the $50 threshold.
    # A price_change alert should fire with the correct old/new/change values.
    findings = run_check(
        fetched_flights=[make_flight(price=700)],
        latest_record=make_record(price=800),
        alert_threshold=50,
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "price_change"
    assert findings[0]["old_price"] == 800
    assert findings[0]["new_price"] == 700
    assert findings[0]["change"] == -100  # negative = price dropped


def test_price_change_alert_fires_on_increase():
    # Price increases should also trigger alerts — we want to know if prices go up.
    findings = run_check(
        fetched_flights=[make_flight(price=900)],
        latest_record=make_record(price=800),
        alert_threshold=50,
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "price_change"
    assert findings[0]["change"] == 100  # positive = price went up


def test_price_change_alert_silent_below_threshold():
    # $20 change on a $50 threshold — no alert. Small fluctuations are noise.
    findings = run_check(
        fetched_flights=[make_flight(price=820)],
        latest_record=make_record(price=800),
        alert_threshold=50,
    )

    assert findings == []


def test_no_alert_when_price_unchanged():
    # Same price as last check — no alert at all.
    findings = run_check(
        fetched_flights=[make_flight(price=800)],
        latest_record=make_record(price=800),
        alert_threshold=50,
    )

    assert findings == []


def test_disappeared_flight_alert():
    # A flight was in the DB last check but is missing from this run's results.
    # This means the airline stopped offering that flight for those dates.
    findings = run_check(
        fetched_flights=[],  # SerpApi returned nothing this run
        previous_flights=[
            {"flight_number": "UA837", "airline": "United", "price": 800}
        ],
    )

    assert len(findings) == 1
    assert findings[0]["type"] == "disappeared_flight"
    assert findings[0]["flight_number"] == "UA837"
    assert findings[0]["last_price"] == 800


def test_duplicate_flights_deduplicated():
    # SerpApi sometimes returns the same flight twice in best_flights + other_flights.
    # checker.py deduplicates by flight_number before comparing or saving.
    # We should get exactly one new_flight alert, not two.
    duplicate = make_flight(flight_number="UA837", price=800)

    findings = run_check(
        fetched_flights=[duplicate, duplicate],
        latest_record=None,  # first time seeing this flight
    )

    new_flight_findings = [f for f in findings if f["type"] == "new_flight"]
    assert len(new_flight_findings) == 1


def test_zero_price_flights_filtered_out():
    # Flights with price=0 are invalid data from SerpApi and should be ignored entirely.
    # No alerts, nothing saved.
    findings = run_check(fetched_flights=[make_flight(price=0)])

    assert findings == []


def test_none_price_flights_filtered_out():
    # Same as above but when the price field is missing entirely.
    no_price_flight = {**make_flight(), "price": None}
    findings = run_check(fetched_flights=[no_price_flight])

    assert findings == []


def test_untracked_flight_no_flight_number():
    # If SerpApi returns a flight with no flight_number, we can't reliably track its
    # price history across runs (no stable identifier). checker.py flags it as
    # untracked_flight so we still know about it, but skips price comparison.
    flight = make_flight()
    flight["flight_number"] = None

    findings = run_check(fetched_flights=[flight])

    assert len(findings) == 1
    assert findings[0]["type"] == "untracked_flight"


def test_db_connection_failure_aborts_early():
    # If the database is unreachable, there's nothing to compare against or save to.
    # check_prices() should abort immediately and return an error alert.
    findings = run_check(fetched_flights=[make_flight()], db_ok=False)

    assert len(findings) == 1
    assert "error" in findings[0]


def test_rate_limit_guard_skips_run():
    # If SerpApi has fewer searches left than needed, skip the entire run to protect
    # the monthly quota. No price_change or new_flight alerts should be generated.
    findings = run_check(
        fetched_flights=[make_flight()],
        usage={"plan_searches_left": 0, "this_month_usage": 250},
    )

    finding_types = [f.get("type") for f in findings]
    assert "new_flight" not in finding_types
    assert "price_change" not in finding_types
