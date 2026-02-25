from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import gzip
import zlib
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class FetchDiagnostics:
    requested_url: str
    final_url: str
    status_code: int | None
    content_type: str
    content_encoding: str
    raw_bytes_len: int
    decoded_chars_len: int


@dataclass(frozen=True)
class LectioWeek:
    week: int
    year: int

    @property
    def week_param(self) -> str:
        # Observed Lectio format: WWYYYY (e.g. 062026)
        return f"{self.week:02d}{self.year}"


def iter_weeks_for_window(*, timezone_name: str, days_past: int, days_future: int) -> list[LectioWeek]:
    """Return ISO weeks (week/year pairs) that overlap the date window.

    We use ISO week numbering because Lectio URLs in the captured HTML look like:
      week=062026
    which matches ISO week 6 in year 2026.
    """

    try:
        from zoneinfo import ZoneInfo

        tzinfo = ZoneInfo(timezone_name)
        today = datetime.now(tzinfo).date()
    except Exception:
        # Fallback: local time; should not happen on Python 3.11+.
        today = date.today()

    window_start = today - timedelta(days=days_past)
    window_end = today + timedelta(days=days_future)

    weeks: list[LectioWeek] = []
    seen: set[tuple[int, int]] = set()

    d = window_start
    while d <= window_end:
        iso_year, iso_week, _ = d.isocalendar()
        key = (iso_week, iso_year)
        if key not in seen:
            seen.add(key)
            weeks.append(LectioWeek(week=iso_week, year=iso_year))
        d += timedelta(days=7)

    # Ensure the end week is included even if the window is < 7 days
    iso_year, iso_week, _ = window_end.isocalendar()
    key = (iso_week, iso_year)
    if key not in seen:
        weeks.append(LectioWeek(week=iso_week, year=iso_year))

    return weeks


def build_week_url(schedule_url: str, week: LectioWeek) -> str:
    """Return schedule_url with its querystring's week= set/overwritten."""

    parsed = urlparse(schedule_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["week"] = [week.week_param]

    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _normalize_cookie_header(cookie_header: str) -> str:
    v = (cookie_header or "").strip()
    if not v:
        return ""

    # Common mistake: user pastes the full header line.
    # GitHub Secret should contain only the value part.
    if v.lower().startswith("cookie:"):
        v = v.split(":", 1)[1].strip()

    # Another common mistake: secrets wrapped in quotes.
    if (len(v) >= 2) and ((v[0] == v[-1]) and v[0] in {"\"", "'"}):
        v = v[1:-1].strip()

    return v


def fetch_html_with_diagnostics(*, url: str, cookie_header: str, timeout_seconds: int = 30) -> tuple[str, FetchDiagnostics]:
    """Fetch a Lectio HTML page and return both HTML and non-sensitive response diagnostics."""

    cookie_value = _normalize_cookie_header(cookie_header)
    if not cookie_value:
        raise ValueError("cookie_header is required")

    headers = {
        # Make it look like a normal browser request.
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "da,en-US;q=0.9,en;q=0.8",
        # Avoid Brotli (br) which we do not decode without extra deps.
        "Accept-Encoding": "identity",
        "Cookie": cookie_value,
    }

    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()

            content_type = (resp.headers.get("Content-Type") or "").strip()
            content_encoding = (resp.headers.get("Content-Encoding") or "").strip().lower()
            status_code = getattr(resp, "status", None)
            if status_code is None:
                try:
                    status_code = resp.getcode()
                except Exception:
                    status_code = None
            final_url = ""
            try:
                final_url = resp.geturl() or ""
            except Exception:
                final_url = ""

            if "br" in content_encoding:
                raise RuntimeError(
                    "Server returned Content-Encoding=br (Brotli), which this tool does not decode. "
                    "Try again; if it persists, we need to add Brotli decoding or adjust request headers."
                )

            # Some servers send compressed responses even when clients don't
            # explicitly ask. urllib does not automatically decompress.
            if "gzip" in content_encoding:
                raw = gzip.decompress(raw)
            elif "deflate" in content_encoding:
                try:
                    raw = zlib.decompress(raw)
                except zlib.error:
                    # Raw DEFLATE stream (no zlib header)
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            elif raw[:2] == b"\x1f\x8b":
                # Heuristic: gzip magic bytes.
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass

            # lectio.dk pages are typically UTF-8
            charset = "utf-8"
            try:
                content_charset = resp.headers.get_content_charset()
                if content_charset:
                    charset = content_charset
            except Exception:
                pass

            html = raw.decode(charset, errors="replace")
            diag = FetchDiagnostics(
                requested_url=url,
                final_url=final_url or url,
                status_code=status_code,
                content_type=content_type,
                content_encoding=content_encoding,
                raw_bytes_len=len(raw),
                decoded_chars_len=len(html),
            )
            return html, diag
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error fetching Lectio HTML: {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error fetching Lectio HTML: {exc.reason}") from exc


def fetch_html(*, url: str, cookie_header: str, timeout_seconds: int = 30) -> str:
    """Fetch a Lectio HTML page using an existing authenticated session cookie.

    This does NOT perform MitID login. It relies on you providing a valid cookie header.
    """

    html, _diag = fetch_html_with_diagnostics(url=url, cookie_header=cookie_header, timeout_seconds=timeout_seconds)
    return html


def fetch_weeks_html(
    *,
    schedule_url: str,
    cookie_header: str,
    weeks: Iterable[LectioWeek],
    timeout_seconds: int = 30,
) -> list[tuple[LectioWeek, str]]:
    out: list[tuple[LectioWeek, str]] = []
    for wk in weeks:
        url = build_week_url(schedule_url, wk)
        html = fetch_html(url=url, cookie_header=cookie_header, timeout_seconds=timeout_seconds)
        out.append((wk, html))
    return out


def fetch_weeks_html_with_diagnostics(
    *,
    schedule_url: str,
    cookie_header: str,
    weeks: Iterable[LectioWeek],
    timeout_seconds: int = 30,
) -> list[tuple[LectioWeek, str, FetchDiagnostics]]:
    out: list[tuple[LectioWeek, str, FetchDiagnostics]] = []
    for wk in weeks:
        url = build_week_url(schedule_url, wk)
        html, diag = fetch_html_with_diagnostics(url=url, cookie_header=cookie_header, timeout_seconds=timeout_seconds)
        out.append((wk, html, diag))
    return out
