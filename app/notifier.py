# Notifier — sends a single summary email for all findings from one run.
#
# Email format: HTML (primary) + plain text (fallback).
# HTML uses inline CSS throughout — email clients strip <style> tags, so
# all styling must be on individual elements.
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.config import SENDGRID_API_KEY, EMAIL_FROM, NOTIFY_EMAILS

logger = logging.getLogger(__name__)


# --- Shared formatters ---

def _fmt_price(value) -> str:
    if value is None:
        return "—"
    return f"${int(value):,}"


def _fmt_stops(value) -> str:
    if value is None:
        return "—"
    return "Direct" if value == 0 else str(value)


# --- HTML builder ---

# Inline style constants — reused across table cells and headers.
_TD = "border: 1px solid #ddd; padding: 7px 12px; text-align: left; white-space: nowrap;"
_TH = "border: 1px solid #ccc; padding: 7px 12px; text-align: left; white-space: nowrap; font-weight: 600;"
_TABLE = "border-collapse: collapse; width: 100%; margin-bottom: 28px; font-size: 13px;"
_TR_ALT = "background-color: #f9f9f9;"  # applied to alternating rows for readability


def _html_section(title: str, title_color: str, headers: list[str], rows: list[list[str]]) -> str:
    """Build one titled table section in HTML."""
    header_cells = "".join(
        f'<th style="{_TH} background-color: #f2f2f2;">{h}</th>' for h in headers
    )
    body_rows = ""
    for i, row in enumerate(rows):
        row_style = f'style="{_TR_ALT}"' if i % 2 == 1 else ""
        cells = "".join(f'<td style="{_TD}">{cell}</td>' for cell in row)
        body_rows += f"<tr {row_style}>{cells}</tr>"

    return (
        f'<h3 style="margin: 24px 0 8px; color: {title_color}; font-size: 15px;">{title}</h3>'
        f'<table style="{_TABLE}">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        f"</table>"
    )


def build_email_html(findings: list[dict]) -> str:
    sections: dict[str, list] = {
        "new_flight": [],
        "price_change": [],
        "disappeared_flight": [],
        "untracked_flight": [],
        "error": [],
    }
    for f in findings:
        t = f.get("type", "error")
        sections[t if t in sections else "error"].append(f)

    content = ""

    if sections["new_flight"]:
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
        content += _html_section(
            "New Flights Found", "#1a6b2e",
            ["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price"],
            rows,
        )

    if sections["price_change"]:
        rows = []
        for a in sections["price_change"]:
            change = a["change"]
            direction = "↑" if change > 0 else "↓"
            change_color = "#b91c1c" if change > 0 else "#15803d"
            price_cell = (
                f'{_fmt_price(a["old_price"])} → '
                f'<strong style="color: {change_color};">{_fmt_price(a["new_price"])}</strong>'
            )
            change_cell = (
                f'<span style="color: {change_color}; font-weight: 600;">'
                f'{direction}${abs(int(change)):,}</span>'
            )
            rows.append([
                a["airline"],
                a.get("flight_number", "—"),
                a["route"],
                a["outbound_date"],
                a.get("return_date", "—"),
                _fmt_stops(a.get("stops")),
                price_cell,
                change_cell,
            ])
        content += _html_section(
            "Price Changes", "#92400e",
            ["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price", "Change"],
            rows,
        )

    if sections["disappeared_flight"]:
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
        content += _html_section(
            "Disappeared Flights", "#991b1b",
            ["Airline", "Flight", "Route", "Departs", "Returns", "Last Price"],
            rows,
        )

    if sections["untracked_flight"]:
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
        content += _html_section(
            "Untracked Flights (no flight number)", "#555",
            ["Airline", "Route", "Departs", "Returns", "Stops", "Price"],
            rows,
        )

    if sections["error"]:
        error_lines = "".join(
            f'<li style="margin-bottom: 4px;">{a.get("error", str(a))}</li>'
            for a in sections["error"]
        )
        content += (
            f'<h3 style="margin: 24px 0 8px; color: #991b1b; font-size: 15px;">Errors</h3>'
            f'<ul style="color: #991b1b; padding-left: 20px;">{error_lines}</ul>'
        )

    return (
        '<html><body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px;'
        ' color: #333; max-width: 860px; margin: 0 auto; padding: 16px;">'
        f"{content}"
        "</body></html>"
    )


# --- Plain text fallback ---

def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt_row(cells):
        return " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    separator = "-+-".join("-" * w for w in widths)
    return "\n".join([fmt_row(headers), separator, *[fmt_row(row) for row in rows]])


def build_email_body(findings: list[dict]) -> str:
    sections: dict[str, list] = {
        "new_flight": [], "price_change": [], "disappeared_flight": [],
        "untracked_flight": [], "error": [],
    }
    for f in findings:
        t = f.get("type", "error")
        sections[t if t in sections else "error"].append(f)

    lines = []

    if sections["new_flight"]:
        lines.append("=== New Flights Found ===")
        rows = [[a["airline"], a.get("flight_number", "—"), a["route"],
                 a["outbound_date"], a.get("return_date", "—"),
                 _fmt_stops(a.get("stops")), _fmt_price(a.get("price"))]
                for a in sections["new_flight"]]
        lines.append(_format_table(["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price"], rows))
        lines.append("")

    if sections["price_change"]:
        lines.append("=== Price Changes ===")
        rows = [[a["airline"], a.get("flight_number", "—"), a["route"],
                 a["outbound_date"], a.get("return_date", "—"),
                 _fmt_stops(a.get("stops")),
                 f"{_fmt_price(a['old_price'])} -> {_fmt_price(a['new_price'])}",
                 f"{'↑' if a['change'] > 0 else '↓'}${abs(int(a['change'])):,}"]
                for a in sections["price_change"]]
        lines.append(_format_table(["Airline", "Flight", "Route", "Departs", "Returns", "Stops", "Price", "Change"], rows))
        lines.append("")

    if sections["disappeared_flight"]:
        lines.append("=== Disappeared Flights ===")
        rows = [[a["airline"], a.get("flight_number", "—"), a["route"],
                 a["outbound_date"], a.get("return_date", "—"), _fmt_price(a.get("last_price"))]
                for a in sections["disappeared_flight"]]
        lines.append(_format_table(["Airline", "Flight", "Route", "Departs", "Returns", "Last Price"], rows))
        lines.append("")

    if sections["untracked_flight"]:
        lines.append("=== Untracked Flights (no flight number) ===")
        rows = [[a["airline"], a["route"], a["outbound_date"], a.get("return_date", "—"),
                 _fmt_stops(a.get("stops")), _fmt_price(a.get("price"))]
                for a in sections["untracked_flight"]]
        lines.append(_format_table(["Airline", "Route", "Departs", "Returns", "Stops", "Price"], rows))
        lines.append("")

    if sections["error"]:
        lines.append("=== Errors ===")
        for a in sections["error"]:
            lines.append(f"  {a.get('error', str(a))}")
        lines.append("")

    return "\n".join(lines)


# --- Send ---

def send_alert(findings: list[dict]):
    if not findings:
        logger.info("No findings to report.")
        return

    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=NOTIFY_EMAILS,
        subject="Flight Tracker Alert",
        plain_text_content=build_email_body(findings),
        html_content=build_email_html(findings),
    )

    try:
        client = SendGridAPIClient(SENDGRID_API_KEY)
        response = client.send(message)
        logger.info("Alert email sent. Status code: %d.", response.status_code)
    except Exception as e:
        logger.error("Failed to send alert email: %s", str(e))
