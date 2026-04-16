import os
import tempfile
from app.reporter import (
    build_html,
    write_html_file,
    _fmt_price,
    _fmt_duration,
    _fmt_stops,
)


# --- Formatter tests ---


def test_fmt_price_normal():
    assert _fmt_price(870) == "$870"


def test_fmt_price_thousands():
    assert _fmt_price(1172) == "$1,172"


def test_fmt_price_none():
    assert _fmt_price(None) == "—"


def test_fmt_duration_normal():
    assert _fmt_duration(125) == "2h 5m"


def test_fmt_duration_none():
    assert _fmt_duration(None) == "—"


def test_fmt_stops_direct():
    assert _fmt_stops(0) == "Direct"


def test_fmt_stops_one():
    assert _fmt_stops(1) == "1 stop"


def test_fmt_stops_multiple():
    assert _fmt_stops(2) == "2 stops"


def test_fmt_stops_none():
    assert _fmt_stops(None) == "—"


# --- build_html tests ---

SAMPLE_FINDINGS = [
    {
        "type": "first_check",
        "route": "IAH ↔ NRT",
        "outbound_date": "2026-06-07",
        "return_date": "2026-06-21",
        "lowest_price": 870,
        "previous_price": None,
        "price_level": "low",
        "typical_low": 870,
        "typical_high": 1150,
        "flights": [
            {
                "airline": "EVA Air",
                "flight_number": "BR 51",
                "price": 870,
                "stops": 1,
                "departure_time": "2026-10-12 01:00",
                "arrival_time": "2026-10-13 09:55",
                "total_duration": 1255,
                "departure": "IAH",
                "arrival": "NRT",
                "outbound_date": "2026-06-07",
                "return_date": "2026-06-21",
            }
        ],
    }
]


def test_build_html_returns_string():
    html = build_html(SAMPLE_FINDINGS, "2026-06-07 08:00")
    assert isinstance(html, str)


def test_build_html_contains_route():
    html = build_html(SAMPLE_FINDINGS, "2026-06-07 08:00")
    assert "IAH" in html
    assert "NRT" in html


def test_build_html_contains_price():
    html = build_html(SAMPLE_FINDINGS, "2026-06-07 08:00")
    assert "$870" in html


def test_build_html_contains_airline():
    html = build_html(SAMPLE_FINDINGS, "2026-06-07 08:00")
    assert "EVA Air" in html


def test_build_html_error_finding():
    findings = [
        {
            "type": "error",
            "route": "IAH ↔ NRT",
            "outbound_date": "2026-06-07",
            "error": "API failed",
        }
    ]
    html = build_html(findings, "2026-06-07 08:00")
    assert "API failed" in html


def test_build_html_price_change():
    findings = [
        {
            **SAMPLE_FINDINGS[0],
            "type": "update",
            "previous_price": 950,
            "price_change": -80,
        }
    ]
    html = build_html(findings, "2026-06-07 08:00")
    assert "$80" in html


def test_build_html_no_flights():
    findings = [{**SAMPLE_FINDINGS[0], "flights": []}]
    html = build_html(findings, "2026-06-07 08:00")
    assert "No watched airline flights found" in html


# --- write_html_file tests ---


def test_write_html_file_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_html_file("<html></html>", tmpdir)
        assert os.path.exists(path)
        assert path.endswith(".html")


def test_write_html_file_creates_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        nested = os.path.join(tmpdir, "reports", "sub")
        path = write_html_file("<html></html>", nested)
        assert os.path.exists(path)


def test_write_html_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = write_html_file("<html><body>hello</body></html>", tmpdir)
        with open(path) as f:
            assert "hello" in f.read()
