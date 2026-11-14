"""Offline tests for IncidentDatetimeParser."""

from datetime import datetime
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.analytics.incident_datetime_parser import IncidentDatetimeParser


class IncidentDatetimeParserTests(unittest.TestCase):
    """Verify supported incident datetime formats and invalid-input handling."""

    def setUp(self):
        self.parser = IncidentDatetimeParser()

    def test_parses_iso_prompt_and_date_only_formats(self):
        self.assertEqual(self.parser.parse("2026-11-11T09:00:00"),
                         datetime(2026, 11, 11, 9, 0, 0))
        self.assertEqual(self.parser.parse("22-01-2026 13:10"),
                         datetime(2026, 1, 22, 13, 10))
        self.assertEqual(self.parser.parse("22-01-2026"),
                         datetime(2026, 1, 22, 0, 0))

    def test_returns_datetime_unchanged_and_none_for_invalid_values(self):
        now = datetime(2026, 11, 13, 10, 30)
        self.assertIs(self.parser.parse(now), now)
        self.assertIsNone(self.parser.parse(None))
        self.assertIsNone(self.parser.parse("   "))
        self.assertIsNone(self.parser.parse("not a date"))


if __name__ == "__main__":
    unittest.main()
