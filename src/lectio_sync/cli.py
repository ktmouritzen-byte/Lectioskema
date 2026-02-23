from __future__ import annotations

import argparse
import os
from pathlib import Path

from lectio_sync.config import load_config_from_env_with_overrides
from lectio_sync.html_parser import (
    parse_lectio_advanced_schedule_html,
    parse_lectio_advanced_schedule_html_text,
)
from lectio_sync.ical_writer import write_icalendar
from lectio_sync.lectio_fetch import fetch_weeks_html, iter_weeks_for_window


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert Lectio Advanced Schedule HTML to .ics")
    parser.add_argument("--html", type=Path, help="Path to Lectio HTML file (overrides LECTIO_HTML_PATH)")
    parser.add_argument("--out", type=Path, help="Output .ics path (overrides OUTPUT_ICS_PATH)")
    parser.add_argument("--tz", type=str, help="Timezone (overrides LECTIO_TIMEZONE)")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help=(
            "Fetch schedule HTML from Lectio using an existing session cookie instead of reading a local HTML file. "
            "Requires --schedule-url (or LECTIO_SCHEDULE_URL) and LECTIO_COOKIE_HEADER."
        ),
    )
    parser.add_argument(
        "--schedule-url",
        type=str,
        help=(
            "Base Lectio schedule URL (SkemaAvanceret.aspx). The 'week' query parameter will be overwritten. "
            "You can also set LECTIO_SCHEDULE_URL."
        ),
    )
    parser.add_argument(
        "--cookie-header",
        type=str,
        help=(
            "Cookie header to use for fetching (advanced). Prefer setting LECTIO_COOKIE_HEADER as an environment variable "
            "or GitHub Secret so it is not visible in process lists/logs."
        ),
    )
    parser.add_argument(
        "--fetch-timeout-seconds",
        type=int,
        default=30,
        help="Timeout in seconds for each Lectio fetch request (default: 30)",
    )
    parser.add_argument(
        "--days-past",
        type=int,
        help="Include events from N days in the past (overrides SYNC_DAYS_PAST)",
    )
    parser.add_argument(
        "--days-future",
        type=int,
        help="Include events up to N days in the future (overrides SYNC_DAYS_FUTURE)",
    )
    parser.add_argument(
        "--delete-missing",
        dest="delete_missing",
        action="store_true",
        help="Enable full-feed replacement behavior (default; can also be set with DELETE_MISSING=true)",
    )
    parser.add_argument(
        "--keep-missing",
        dest="delete_missing",
        action="store_false",
        help="Keep missing events policy flag for compatibility (currently informational only)",
    )
    parser.set_defaults(delete_missing=None)
    parser.add_argument(
        "--emit-cancelled-events",
        action="store_true",
        help="Emit cancelled activities as VEVENT with STATUS:CANCELLED instead of dropping them",
    )
    parser.add_argument("--debug", action="store_true", help="Print parser diagnostics")
    args = parser.parse_args()

    if args.days_past is not None and args.days_past < 0:
        parser.error("--days-past must be >= 0")
    if args.days_future is not None and args.days_future < 0:
        parser.error("--days-future must be >= 0")
    if args.fetch_timeout_seconds is not None and args.fetch_timeout_seconds <= 0:
        parser.error("--fetch-timeout-seconds must be > 0")

    if args.fetch:
        timezone_name = args.tz or os.environ.get("LECTIO_TIMEZONE", "Europe/Copenhagen")
        days_past = 7 if args.days_past is None else args.days_past
        days_future = 90 if args.days_future is None else args.days_future

        schedule_url = args.schedule_url or os.environ.get("LECTIO_SCHEDULE_URL", "")
        if not schedule_url.strip():
            parser.error("--schedule-url is required for --fetch (or set LECTIO_SCHEDULE_URL)")

        cookie_header = args.cookie_header or os.environ.get("LECTIO_COOKIE_HEADER", "")
        if not cookie_header.strip():
            parser.error("LECTIO_COOKIE_HEADER is required for --fetch (prefer GitHub Secret / env var)")

        weeks = iter_weeks_for_window(timezone_name=timezone_name, days_past=days_past, days_future=days_future)
        fetched = fetch_weeks_html(
            schedule_url=schedule_url,
            cookie_header=cookie_header,
            weeks=weeks,
            timeout_seconds=args.fetch_timeout_seconds,
        )

        events = []
        seen_uids: set[str] = set()
        for wk, html in fetched:
            try:
                week_events = parse_lectio_advanced_schedule_html_text(
                    html,
                    timezone_name,
                    sync_days_past=days_past,
                    sync_days_future=days_future,
                    emit_cancelled_events=args.emit_cancelled_events,
                    debug=args.debug,
                )
            except Exception as exc:
                raise RuntimeError(
                    "Failed to parse fetched Lectio HTML. This often means the cookie is invalid/expired, "
                    "or the URL did not return the schedule page."
                ) from exc

            for ev in week_events:
                if ev.uid in seen_uids:
                    continue
                seen_uids.add(ev.uid)
                events.append(ev)

        # Keep deterministic ordering across all weeks
        from datetime import datetime
        from dateutil import tz

        def _sort_key(ev):
            if ev.is_all_day:
                return (0, ev.all_day_date, ev.title, ev.uid)
            return (1, ev.start or datetime.min.replace(tzinfo=tz.UTC), ev.title, ev.uid)

        events.sort(key=_sort_key)

        out_path = args.out or Path(os.environ.get("OUTPUT_ICS_PATH", "docs/calendar.ics"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_icalendar(events, out_path)

        print(f"Wrote {len(events)} events to {out_path}")
        return 0

    config = load_config_from_env_with_overrides(
        lectio_html_path=args.html,
        output_ics_path=args.out,
        timezone=args.tz,
        sync_days_past=args.days_past,
        sync_days_future=args.days_future,
        delete_missing=args.delete_missing,
        emit_cancelled_events=args.emit_cancelled_events,
    )

    events = parse_lectio_advanced_schedule_html(
        config.lectio_html_path,
        config.timezone,
        sync_days_past=config.sync_days_past,
        sync_days_future=config.sync_days_future,
        emit_cancelled_events=config.emit_cancelled_events,
        debug=args.debug,
    )

    if args.debug and not config.delete_missing:
        print(
            "Delete missing policy: keep-missing requested, but current implementation regenerates a full feed each run."
        )
    out_path = config.output_ics_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_icalendar(events, out_path)

    print(f"Wrote {len(events)} events to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
