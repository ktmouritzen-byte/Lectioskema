from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from lectio_sync.event_model import LectioEvent


def _dtstamp_utc(now: datetime | None = None) -> str:
    ts = now or datetime.now(timezone.utc)
    ts = ts.astimezone(timezone.utc)
    return ts.strftime("%Y%m%dT%H%M%SZ")


def _format_local(dt: datetime) -> str:
    # Output as "floating" local time (no Z). Seconds included.
    return dt.strftime("%Y%m%dT%H%M%S")


def _format_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def _escape_ical_value(value: str) -> str:
    # RFC5545 escaping for TEXT values.
    # Must escape: backslash, semicolon, comma, newline.
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\n", "\\n")
    return value


def _fold_75_octets(line: str) -> str:
    # RFC5545: lines are limited to 75 octets, folded with CRLF + single space.
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line

    out_lines: list[str] = []
    current = bytearray()
    max_first = 75
    max_cont = 74  # + leading space on continuation makes 75
    limit = max_first
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > limit:
            out_lines.append(current.decode("utf-8"))
            current = bytearray()
            limit = max_cont
        current.extend(b)
    if current:
        out_lines.append(current.decode("utf-8"))

    if not out_lines:
        return line

    return "\r\n ".join(out_lines)


def _prop(name: str, value: str) -> str:
    return _fold_75_octets(f"{name}:{value}")


def _prop_param(name: str, param: str, value: str) -> str:
    return _fold_75_octets(f"{name};{param}:{value}")


def _single_line(text: str) -> str:
    return " ".join((text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


def build_icalendar(events: Iterable[LectioEvent], dtstamp: datetime | None = None) -> str:
    stamp = _dtstamp_utc(dtstamp)

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LectioParser//Custom//EN",
    ]

    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(_prop("UID", _single_line(ev.uid)))
        lines.append(_prop("DTSTAMP", stamp))

        summary = _escape_ical_value(_single_line(ev.title))
        lines.append(_prop("SUMMARY", summary))

        status = _single_line(ev.status or "CONFIRMED").upper()
        if status == "CANCELLED":
            lines.append(_prop("STATUS", "CANCELLED"))

        if ev.is_all_day:
            if ev.all_day_date is None:
                # Fault-tolerant: skip invalid date events
                lines.append("END:VEVENT")
                continue
            d = _format_date(ev.all_day_date)
            lines.append(_prop_param("DTSTART", "VALUE=DATE", d))
            lines.append(_prop_param("DTEND", "VALUE=DATE", d))
        else:
            if ev.start is None or ev.end is None:
                lines.append("END:VEVENT")
                continue
            lines.append(_prop("DTSTART", _format_local(ev.start)))
            lines.append(_prop("DTEND", _format_local(ev.end)))

        location = _escape_ical_value(_single_line(ev.location))
        if location:
            lines.append(_prop("LOCATION", location))

        description = _escape_ical_value((ev.description or "").strip())
        lines.append(_prop("DESCRIPTION", description))

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write_icalendar(events: Iterable[LectioEvent], output_path: Path) -> None:
    ics = build_icalendar(events)
    output_path.write_text(ics, encoding="utf-8", newline="")
