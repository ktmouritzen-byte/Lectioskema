from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


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


def fetch_html(*, url: str, cookie_header: str, timeout_seconds: int = 30) -> str:
    """Fetch a Lectio HTML page using an existing authenticated session cookie.

    This does NOT perform MitID login. It relies on you providing a valid cookie header.
    """

    if not cookie_header or cookie_header.strip() == "":
        raise ValueError("cookie_header is required")

    headers = {
        # Make it look like a normal browser request.
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "da,en-US;q=0.9,en;q=0.8",
        "Cookie": cookie_header.strip(),
    }

    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read()
            # lectio.dk pages are typically UTF-8
            charset = "utf-8"
            try:
                content_charset = resp.headers.get_content_charset()
                if content_charset:
                    charset = content_charset
            except Exception:
                pass
            return raw.decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error fetching Lectio HTML: {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error fetching Lectio HTML: {exc.reason}") from exc


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
