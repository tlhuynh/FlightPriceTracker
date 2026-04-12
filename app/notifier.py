# Notifier — sends a single summary email for all findings from one run.
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import SENDGRID_API_KEY, EMAIL_FROM, NOTIFY_EMAILS

logger = logging.getLogger(__name__)


def _fmt_price(value) -> str:
    """Format a numeric price as a dollar string with comma separator (e.g. $1,495)."""
    if value is None:
        return "—"
    return f"${int(value):,}"


def _fmt_stops(value) -> str:
    """Format stop count as a readable string."""
    if value is None:
        return "—"
    return "Direct" if value == 0 else str(value)


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    """
    Render a plain-text table from a list of headers and rows.
    Column widths are computed dynamically from the widest value in each column.
    """
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt_row(cells):
        return " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    separator = "-+-".join("-" * w for w in widths)
    lines = [fmt_row(headers), separator, *[fmt_row(row) for row in rows]]
    return "\n".join(lines)


def build_email_body(findings: list[dict]) -> str:
    sections = {
        "new_flight": [],
        "price_change": [],
        "disappeared_flight": [],
        "untracked_flight": [],
        "error": [],
    }

    for alert in findings:
        alert_type = alert.get("type", "error")
        if alert_type in sections:
            sections[alert_type].append(alert)
        else:
            sections["error"].append(alert)

    lines = []

    if sections["new_flight"]:
        lines.append("=== New Flights Found ===")
        rows = [
            [
                a["airline"],
                a.get("flight_number", "—"),
                a["route"],
                a["outbound_date"],
                a.get("return_date", "—"),
                _fmt_stops(a.get("stops")),
                _fmt_price(a.get("price")),
            ]
            for a in sections["new_flight"]
        ]
        lines.append(_format_table(
            ["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price"],
            rows,
        ))
        lines.append("")

    if sections["price_change"]:
        lines.append("=== Price Changes ===")
        rows = [
            [
                a["airline"],
                a.get("flight_number", "—"),
                a["route"],
                a["outbound_date"],
                a.get("return_date", "—"),
                _fmt_stops(a.get("stops")),
                f"{_fmt_price(a['old_price'])} → {_fmt_price(a['new_price'])}",
                f"{'↑' if a['change'] > 0 else '↓'}${abs(int(a['change'])):,}",
            ]
            for a in sections["price_change"]
        ]
        lines.append(_format_table(
            ["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price", "Change"],
            rows,
        ))
        lines.append("")

    if sections["disappeared_flight"]:
        lines.append("=== Disappeared Flights ===")
        rows = [
            [
                a["airline"],
                a.get("flight_number", "—"),
                a["route"],
                a["outbound_date"],
                a.get("return_date", "—"),
                _fmt_price(a.get("last_price")),
            ]
            for a in sections["disappeared_flight"]
        ]
        lines.append(_format_table(
            ["Airline", "Flight", "Route", "Departs", "Returns", "Last Price"],
            rows,
        ))
        lines.append("")

    if sections["untracked_flight"]:
        lines.append("=== Untracked Flights (no flight number) ===")
        rows = [
            [
                a["airline"],
                a["route"],
                a["outbound_date"],
                a.get("return_date", "—"),
                _fmt_stops(a.get("stops")),
                _fmt_price(a.get("price")),
            ]
            for a in sections["untracked_flight"]
        ]
        lines.append(_format_table(
            ["Airline", "Route", "Departs", "Returns", "Stops", "Price"],
            rows,
        ))
        lines.append("")

    if sections["error"]:
        lines.append("=== Errors ===")
        for a in sections["error"]:
            lines.append(f"  {a.get('error', str(a))}")
        lines.append("")

    return "\n".join(lines)


# Send one summary email for all findings from a single run.
def send_alert(findings: list[dict]):
    if not findings:
        logger.info("No findings to report.")
        return

    body = build_email_body(findings)

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=NOTIFY_EMAILS,
        subject="Flight Tracker Alert",
        plain_text_content=body,
    )

    try:
        client = SendGridAPIClient(SENDGRID_API_KEY)
        response = client.send(message)
        logger.info("Alert email sent. Status code: %d.", response.status_code)
    except Exception as e:
        logger.error("Failed to send alert email: %s", str(e))
