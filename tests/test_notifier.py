# Tests for notifier.py — verifies email body formatting and send behaviour.
#
# Two things to test:
#   1. build_email_body() — pure function, no mocks needed, just call it and check output
#   2. send_alerts()      — calls SendGrid, so we mock SendGridAPIClient to avoid
#                           needing a real API key or sending actual emails

from unittest.mock import patch, MagicMock
from app.notifier import send_alerts, build_email_body


# --- build_email_body tests (pure function — no mocks needed) ---

def test_email_body_includes_new_flight_section():
    # A new_flight alert should appear under the "New Flights Found" heading.
    alerts = [
        {
            "type": "new_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "price": 800,
        }
    ]

    body = build_email_body(alerts)

    assert "New Flights Found" in body
    assert "UA837" in body
    assert "800" in body


def test_email_body_includes_price_change_section():
    # A price_change alert should appear under "Price Changes" with both old and new price.
    alerts = [
        {
            "type": "price_change",
            "airline": "United",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "old_price": 800,
            "new_price": 700,
            "change": -100,
        }
    ]

    body = build_email_body(alerts)

    assert "Price Changes" in body
    assert "800" in body
    assert "700" in body


def test_email_body_includes_disappeared_flight_section():
    alerts = [
        {
            "type": "disappeared_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "return_date": "2026-06-15",
            "last_price": 800,
        }
    ]

    body = build_email_body(alerts)

    assert "Disappeared Flights" in body
    assert "UA837" in body


def test_email_body_omits_empty_sections():
    # If there are no price_change alerts, the "Price Changes" section shouldn't appear.
    # Only sections with actual alerts should be included to keep the email clean.
    alerts = [
        {
            "type": "new_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "price": 800,
        }
    ]

    body = build_email_body(alerts)

    assert "New Flights Found" in body
    assert "Price Changes" not in body
    assert "Disappeared Flights" not in body


def test_email_body_handles_multiple_alert_types():
    # When multiple alert types exist, all relevant sections should appear.
    alerts = [
        {
            "type": "new_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "price": 800,
        },
        {
            "type": "price_change",
            "airline": "JAL",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "old_price": 900,
            "new_price": 750,
            "change": -150,
        },
    ]

    body = build_email_body(alerts)

    assert "New Flights Found" in body
    assert "Price Changes" in body


# --- send_alerts tests (mocks SendGrid) ---

def test_send_alerts_does_nothing_when_empty():
    # No alerts = no email. We verify SendGrid is never called at all.
    with patch("app.notifier.SendGridAPIClient") as mock_client:
        send_alerts([])

    # The SendGrid client should not have been instantiated at all
    mock_client.assert_not_called()


def test_send_alerts_calls_sendgrid_with_alerts():
    # When there are alerts, send_alerts() should instantiate the SendGrid client
    # and call .send() exactly once.
    alerts = [
        {
            "type": "new_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "price": 800,
        }
    ]

    # Mock the SendGrid client so no real email is sent
    mock_instance = MagicMock()
    mock_instance.send.return_value = MagicMock(status_code=202)

    with patch("app.notifier.SendGridAPIClient", return_value=mock_instance):
        send_alerts(alerts)

    # Verify .send() was called exactly once
    mock_instance.send.assert_called_once()


def test_send_alerts_does_not_raise_on_sendgrid_failure():
    # If SendGrid fails (bad key, network issue), send_alerts() should log the error
    # but not crash the whole job. A failed email is not worth taking down the run.
    alerts = [
        {
            "type": "new_flight",
            "airline": "United",
            "flight_number": "UA837",
            "route": "IAH → NRT",
            "outbound_date": "2026-06-01",
            "price": 800,
        }
    ]

    mock_instance = MagicMock()
    mock_instance.send.side_effect = Exception("SendGrid API error")

    with patch("app.notifier.SendGridAPIClient", return_value=mock_instance):
        # Should complete without raising
        send_alerts(alerts)
