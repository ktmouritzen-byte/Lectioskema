from __future__ import annotations
# pyright: reportMissingImports=false

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_sync.html_parser import parse_lectio_advanced_schedule_html


class HtmlParserTests(unittest.TestCase):
    def setUp(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self.html_path = repo_root / "Avanceret skema - Lectio - TEC.html"

    def test_parses_fixture_without_window_filter(self) -> None:
        events = parse_lectio_advanced_schedule_html(
            self.html_path,
            "Europe/Copenhagen",
            sync_days_past=None,
            sync_days_future=None,
            debug=False,
        )
        self.assertGreater(len(events), 0)

    def test_cancelled_dropped_by_default(self) -> None:
        events = parse_lectio_advanced_schedule_html(
            self.html_path,
            "Europe/Copenhagen",
            sync_days_past=None,
            sync_days_future=None,
            emit_cancelled_events=False,
            debug=False,
        )
        self.assertTrue(all(e.status == "CONFIRMED" for e in events))

    def test_cancelled_can_be_emitted(self) -> None:
        events = parse_lectio_advanced_schedule_html(
            self.html_path,
            "Europe/Copenhagen",
            sync_days_past=None,
            sync_days_future=None,
            emit_cancelled_events=True,
            debug=False,
        )
        self.assertTrue(any(e.status == "CANCELLED" for e in events))


if __name__ == "__main__":
    unittest.main()
