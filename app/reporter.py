# Reporter — builds the HTML report from findings and handles output (file or email).
import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

# --- Inline style constants ---
_TABLE = "border-collapse: collapse; width: 100%; margin-bottom: 12px; font-size: 13px;"
_TH = "border: 1px solid #ccc; padding: 7px 12px; text-align: left; background-color: #f2f2f2; font-weight: 600; white-space: nowrap;"
_TD = (
    "border: 1px solid #ddd; padding: 7px 12px; text-align: left; white-space: nowrap;"
)
_TD_ALT = "border: 1px solid #ddd; padding: 7px 12px; text-align: left; white-space: nowrap; background-color: #f9f9f9;"

_LEVEL_STYLE = {
    "low": "background-color: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: 600;",
    "typical": "background-color: #fef9c3; color: #854d0e; padding: 2px 8px; border-radius: 4px; font-weight: 600;",
    "high": "background-color: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-weight: 600;",
}


def _fmt_price(value) -> str:
    if value is None:
        return "—"
    return f"${int(value):,}"


def _fmt_duration(minutes) -> str:
    if minutes is None:
        return "—"
    return f"{minutes // 60}h {minutes % 60}m"


def _fmt_stops(value) -> str:
    if value is None:
        return "—"
    return "Direct" if value == 0 else f"{value} stop{'s' if value > 1 else ''}"


def _price_level_badge(level: str) -> str:
    style = _LEVEL_STYLE.get(level.lower(), "") if level else ""
    return f'<span style="{style}">{level.upper() if level else "—"}</span>'


def _price_change_html(change) -> str:
    if change is None:
        return '<span style="color: #888;">No change</span>'
    color = "#166534" if change < 0 else "#991b1b"
    arrow = "↓" if change < 0 else "↑"
    return f'<span style="color: {color}; font-weight: 600;">{arrow} ${abs(int(change)):,}</span>'


def build_html(findings: list[dict], checked_at: str) -> str:
    body = ""

    for finding in findings:
        if finding["type"] == "error":
            body += (
                f'<div style="background:#fee2e2; border-left: 4px solid #991b1b; padding: 12px 16px; margin-bottom: 24px; border-radius: 4px;">'
                f'<strong style="color:#991b1b;">Error — {finding.get("route", "")}'
                f"{' on ' + finding['outbound_date'] if 'outbound_date' in finding else ''}</strong><br>"
                f'<span style="color:#991b1b;">{finding.get("error", "Unknown error")}</span>'
                f"</div>"
            )
            continue

        outbound = finding["outbound_date"]
        return_d = finding["return_date"]
        lowest = finding.get("lowest_price")
        previous = finding.get("previous_price")
        level = finding.get("price_level", "")
        typical_low = finding.get("typical_low")
        typical_high = finding.get("typical_high")
        change = finding.get("price_change")
        flights = finding.get("flights", [])
        is_first = finding["type"] == "first_check"

        # Section header
        body += (
            f'<div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px;">'
            f'<h2 style="margin: 0 0 12px; font-size: 16px; color: #111;">'
            f"{finding['route']} &nbsp;|&nbsp; {outbound} → {return_d}"
            f"</h2>"
        )

        # Price summary row
        body += (
            f'<div style="display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 14px; font-size: 14px;">'
            f'<div><span style="color:#555;">Lowest price:</span> <strong>{_fmt_price(lowest)}</strong></div>'
            f'<div><span style="color:#555;">Level:</span> {_price_level_badge(level)}</div>'
            f'<div><span style="color:#555;">Typical range:</span> {_fmt_price(typical_low)} – {_fmt_price(typical_high)}</div>'
            f'<div><span style="color:#555;">vs last check:</span> '
            f"{'<em>First check</em>' if is_first else _price_change_html(change)}</div>"
        )
        if not is_first and previous is not None:
            body += f'<div><span style="color:#555;">Previous:</span> {_fmt_price(previous)}</div>'
        body += "</div>"

        # Flights table
        if flights:
            header_cells = "".join(
                f'<th style="{_TH}">{h}</th>'
                for h in [
                    "Airline",
                    "Flight",
                    "Price",
                    "Stops",
                    "Departs",
                    "Arrives",
                    "Duration",
                ]
            )
            rows = ""
            for i, f in enumerate(
                sorted(flights, key=lambda x: x.get("price") or 999999)
            ):
                td = _TD_ALT if i % 2 == 1 else _TD
                rows += (
                    f"<tr>"
                    f'<td style="{td}">{f.get("airline", "—")}</td>'
                    f'<td style="{td}">{f.get("flight_number", "—")}</td>'
                    f'<td style="{td}"><strong>{_fmt_price(f.get("price"))}</strong></td>'
                    f'<td style="{td}">{_fmt_stops(f.get("stops"))}</td>'
                    f'<td style="{td}">{f.get("departure_time", "—")}</td>'
                    f'<td style="{td}">{f.get("arrival_time", "—")}</td>'
                    f'<td style="{td}">{_fmt_duration(f.get("total_duration"))}</td>'
                    f"</tr>"
                )
            body += (
                f'<table style="{_TABLE}">'
                f"<thead><tr>{header_cells}</tr></thead>"
                f"<tbody>{rows}</tbody>"
                f"</table>"
            )
        else:
            body += '<p style="color: #888; font-size: 13px;">No watched airline flights found for this trip.</p>'

        body += "</div>"

    return (
        '<html><body style="font-family: Arial, Helvetica, sans-serif; font-size: 14px;'
        ' color: #333; max-width: 900px; margin: 0 auto; padding: 24px;">'
        f'<h1 style="font-size: 20px; margin-bottom: 4px;">Flight Tracker Report</h1>'
        f'<p style="color: #666; font-size: 13px; margin-bottom: 28px;">Checked: {checked_at}</p>'
        f"{body}"
        "</body></html>"
    )


def write_html_file(html: str, output_dir: str) -> str:
    """Write HTML report to output_dir. Returns the file path written."""
    expanded = os.path.expanduser(output_dir)
    os.makedirs(expanded, exist_ok=True)
    filename = f"flight-report-{date.today().isoformat()}.html"
    path = os.path.join(expanded, filename)
    with open(path, "w") as f:
        f.write(html)
    logger.info("HTML report written to %s", path)
    return path
