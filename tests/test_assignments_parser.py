from __future__ import annotations
# pyright: reportMissingImports=false

import sys
import unittest
from datetime import date
from pathlib import Path
from textwrap import dedent

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lectio_sync.html_parser import parse_lectio_assignments_html_text


# ---------------------------------------------------------------------------
# Minimal OpgaverElev.aspx HTML fixture
# ---------------------------------------------------------------------------
_FIXTURE_HTML = dedent("""\
<!DOCTYPE html>
<html>
<body>
<table id="s_m_Content_Content_ExerciseGV">
  <thead>
    <tr>
      <th>Hold</th>
      <th>Opgavetitel</th>
      <th>Frist</th>
      <th>Elev tid</th>
      <th>Status</th>
      <th>col6</th>
      <th>col7</th>
      <th>Opgavenote</th>
    </tr>
  </thead>
  <tbody>
    <!-- Past assignment: should be filtered out (due 2025-09-10) -->
    <tr>
      <td>L2a MA</td>
      <td><a href="/lectio/681/ElevAflevering.aspx?elevid=123&amp;exerciseid=99990001&amp;prevurl=OpgaverElev.aspx">Gammel opgave</a></td>
      <td>10/9-2025 22:00</td>
      <td>2,00</td>
      <td>Afleveret</td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <!-- Due today: should be included -->
    <tr>
      <td>L2a DA</td>
      <td><a href="/lectio/681/ElevAflevering.aspx?elevid=123&amp;exerciseid=99990002&amp;prevurl=OpgaverElev.aspx">Dagens frist opgave</a></td>
      <td>26/2-2026 23:59</td>
      <td>1,00</td>
      <td>Mangler</td>
      <td></td>
      <td></td>
      <td>Se vedhæftet fil.</td>
    </tr>
    <!-- Future assignment with multi-line note: should be included -->
    <tr>
      <td>L2a EN</td>
      <td><a href="/lectio/681/ElevAflevering.aspx?elevid=123&amp;exerciseid=99990003&amp;prevurl=OpgaverElev.aspx">Essay om Shakespeare</a></td>
      <td>15/3-2026 22:00</td>
      <td>3,00</td>
      <td>Venter</td>
      <td></td>
      <td></td>
      <td>Skriv et essay.
Mind. 800 ord.</td>
    </tr>
  </tbody>
</table>
</body>
</html>
""")


class AssignmentsParserTests(unittest.TestCase):

    def setUp(self) -> None:
        # Fix "today" to 2026-02-26 for deterministic filter behaviour.
        self._today = date(2026, 2, 26)

    def _parse(self) -> list:
        return parse_lectio_assignments_html_text(
            _FIXTURE_HTML,
            "Europe/Copenhagen",
            today=self._today,
        )

    # -- Basic extraction --

    def test_past_assignment_excluded(self) -> None:
        events = self._parse()
        uids = {ev.uid for ev in events}
        self.assertNotIn("99990001@lectio.dk", uids)

    def test_due_today_included(self) -> None:
        events = self._parse()
        uids = {ev.uid for ev in events}
        self.assertIn("99990002@lectio.dk", uids)

    def test_future_assignment_included(self) -> None:
        events = self._parse()
        uids = {ev.uid for ev in events}
        self.assertIn("99990003@lectio.dk", uids)

    def test_count_is_two(self) -> None:
        events = self._parse()
        self.assertEqual(len(events), 2)

    # -- UID stability --

    def test_uid_uses_exerciseid(self) -> None:
        events = self._parse()
        for ev in events:
            self.assertTrue(ev.uid.endswith("@lectio.dk"))
            exercise_part = ev.uid.split("@")[0]
            self.assertTrue(exercise_part.isdigit(), f"UID base {exercise_part!r} is not numeric")

    # -- SUMMARY / title format --

    def test_title_order_status_opgavetitel_hold_elevtid(self) -> None:
        events = self._parse()
        today_ev = next(ev for ev in events if ev.uid == "99990002@lectio.dk")
        # Expected: "Mangler • Dagens frist opgave • L2a DA • 1,00"
        expected = "Mangler \u2022 Dagens frist opgave \u2022 L2a DA \u2022 1,00"
        self.assertEqual(today_ev.title, expected)

    # -- All-day event semantics --

    def test_events_are_all_day(self) -> None:
        events = self._parse()
        for ev in events:
            self.assertTrue(ev.is_all_day, f"{ev.uid} should be all-day")
            self.assertIsNone(ev.start)
            self.assertIsNone(ev.end)

    def test_all_day_date_is_frist_date(self) -> None:
        events = self._parse()
        today_ev = next(ev for ev in events if ev.uid == "99990002@lectio.dk")
        self.assertEqual(today_ev.all_day_date, date(2026, 2, 26))

        future_ev = next(ev for ev in events if ev.uid == "99990003@lectio.dk")
        self.assertEqual(future_ev.all_day_date, date(2026, 3, 15))

    # -- Description / Opgavenote --

    def test_description_contains_opgavenote(self) -> None:
        events = self._parse()
        today_ev = next(ev for ev in events if ev.uid == "99990002@lectio.dk")
        self.assertIn("Se vedhæftet fil.", today_ev.description)

    def test_multiline_note_preserved(self) -> None:
        events = self._parse()
        future_ev = next(ev for ev in events if ev.uid == "99990003@lectio.dk")
        # The _normalize_text helper preserves \n newlines.
        self.assertIn("Skriv et essay", future_ev.description)
        self.assertIn("800 ord", future_ev.description)

    # -- Ordering --

    def test_events_sorted_by_due_date(self) -> None:
        events = self._parse()
        dates = [ev.all_day_date for ev in events]
        self.assertEqual(dates, sorted(dates))

    # -- Missing table raises ValueError --

    def test_missing_table_raises(self) -> None:
        with self.assertRaises(ValueError, msg="Should raise when table is not found"):
            parse_lectio_assignments_html_text(
                "<html><body><p>No table here.</p></body></html>",
                "Europe/Copenhagen",
                today=self._today,
            )


if __name__ == "__main__":
    unittest.main()
