# Notifier — sends email alerts when a price change is detected.
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import SENDGRID_API_KEY, EMAIL_FROM, NOTIFY_EMAILS

logger = logging.getLogger(__name__)


# TODO update the layout of the email body to be more readable and include more details about the flight and price change.
# Build an email notification with the given alerts.
def build_email_body(alerts: list[dict]) -> str:
    sections = {
        "new_flight": [],
        "price_change": [],
        "disappeared_flight": [],
        "untracked_flight": [],
        "error": [],
    }

    for alert in alerts:
        alert_type = alert.get("type", "error")
        if alert_type in sections:
            sections[alert_type].append(alert)
        else:
            sections["error"].append(alert)

    lines = []

    if sections["new_flight"]:
        lines.append("--- New Flights Found ---")
        for a in sections["new_flight"]:
            lines.append(
                f"  {a['airline']} {a['flight_number']} | {a['route']} | {a['outbound_date']} | ${a['price']}"
            )
        lines.append("")

    if sections["price_change"]:
        lines.append("--- Price Changes ---")
        for a in sections["price_change"]:
            direction = "\u2193" if a["change"] < 0 else "\u2191"
            lines.append(
                f"  {a['airline']} | {a['route']} | {a['outbound_date']} | ${a['old_price']} \u2192 ${a['new_price']} ({direction}${abs(a['change'])})"
            )
        lines.append("")

    if sections["disappeared_flight"]:
        lines.append("--- Disappeared Flights ---")
        for a in sections["disappeared_flight"]:
            lines.append(
                f"  {a['airline']} {a['flight_number']} | {a['route']} | {a['outbound_date']} | was ${a['last_price']}"
            )
        lines.append("")

    if sections["untracked_flight"]:
        lines.append("--- Untracked Flights (no flight number) ---")
        for a in sections["untracked_flight"]:
            lines.append(
                f"  {a['airline']} | {a['route']} | {a['outbound_date']} | ${a['price']} | dep {a.get('departure_time', 'N/A')} | arr {a.get('arrival_time', 'N/A')} | {a.get('stops', '?')} stops"
            )
        lines.append("")

    if sections["error"]:
        lines.append("--- Errors ---")
        for a in sections["error"]:
            lines.append(f"  {a.get('error', str(a))}")
        lines.append("")

    return "\n".join(lines)


# Send email alerts for the given list of alerts. Each alert is a dict with details about the flight and price change.
def send_alerts(alerts: list[dict]):
    if not alerts:
        logger.info("No alerts to send.")
        return

    body = build_email_body(alerts)

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=NOTIFY_EMAILS,
        subject="Flights Alert",
        plain_text_content=body,
    )

    try:
        client = SendGridAPIClient(SENDGRID_API_KEY)
        response = client.send(message)
        logger.info("Alert email sent. Status code: %d.", response.status_code)
    except Exception as e:
        logger.error("Failed to send alert email: %s", str(e))
