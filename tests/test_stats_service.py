"""Offline tests for StatsService aggregates and the home dashboard."""

from datetime import timedelta
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.analytics.stats_service import StatsService
from data_manager import DataManager
from tests.dashboard_test_case import DashboardTestCase


class StatsServiceTests(DashboardTestCase):
    """Verify Python-side analytics, boundary rules, and home dashboard rendering."""

    # ------------------------------------------------------------------
    # empty database
    # ------------------------------------------------------------------

    def test_empty_database_produces_zeroed_statistics(self):
        self.assertEqual(self.stats.incidents_by_severity(),
                         {"low": 0, "medium": 0, "high": 0})
        self.assertEqual(self.stats.incidents_by_hazard_category(), {})
        self.assertEqual(self.stats.incidents_by_queue(), {})
        self.assertEqual([point.count for point in self.stats.incidents_per_day()], [0] * 14)
        self.assertEqual(len(self.stats.incidents_per_day()), 14)
        self.assertEqual(self.stats.recurrence_hotspots(), [])
        self.assertEqual(self.stats.rising_patterns(), [])

    # ------------------------------------------------------------------
    # severity banding
    # ------------------------------------------------------------------

    def test_severity_scores_are_banded_with_pipeline_thresholds(self):
        cases = [(0.85, "high"), (0.71, "high"), (0.70, "medium"),
                 (0.40, "medium"), (0.39, "low"), (0.05, "low")]
        for score, expected_band in cases:
            self.seed(severity_score=score, severity=score)
        counts = self.stats.incidents_by_severity()
        self.assertEqual(counts, {"low": 2, "medium": 2, "high": 2},
                         "each band boundary must land in its expected band")

    def test_legacy_numeric_severity_is_banded_and_string_bands_count_as_is(self):
        self.seed(severity=0.86)          # legacy row: number directly in severity
        self.seed(severity="medium")      # current row: already banded
        self.assertEqual(self.stats.incidents_by_severity(),
                         {"low": 0, "medium": 1, "high": 1})

    def test_records_without_usable_severity_are_skipped(self):
        self.seed()                                  # one countable incident
        self.seed(severity="Manual review pending")  # unrecognised string
        self.assertEqual(self.stats.incidents_by_severity(),
                         {"low": 0, "medium": 0, "high": 1})

    # ------------------------------------------------------------------
    # time series
    # ------------------------------------------------------------------

    def test_per_day_series_is_zero_filled_and_placed_on_the_right_days(self):
        self.seed(days_ago=0)
        self.seed(days_ago=5)
        self.seed(days_ago=20)  # outside the default 14-day series
        points = self.stats.incidents_per_day()
        by_label = {point.label: point.count for point in points}
        self.assertEqual(len(points), 14)
        self.assertEqual(by_label[self.today.isoformat()], 1)
        self.assertEqual(by_label[(self.today - timedelta(days=5)).isoformat()], 1)
        self.assertEqual(by_label[(self.today - timedelta(days=6)).isoformat()], 0)
        self.assertNotIn((self.today - timedelta(days=20)).isoformat(), by_label)

    # ------------------------------------------------------------------
    # recurrence hotspots
    # ------------------------------------------------------------------

    def test_hotspots_require_repetition_inside_the_30_day_window(self):
        self.seed(days_ago=0, location="Warehouse", hazard_category="mechanical")
        self.seed(days_ago=15, location="Warehouse", hazard_category="mechanical")
        self.seed(days_ago=10, location="Workshop", hazard_category="ergonomic")
        hotspots = self.stats.recurrence_hotspots()
        self.assertEqual([(h.location, h.hazard_category, h.count) for h in hotspots],
                         [("Warehouse", "mechanical", 2)],
                         "a single occurrence is not a hotspot")

    def test_hotspot_window_excludes_incidents_older_than_30_days(self):
        self.seed(days_ago=0, location="Warehouse", hazard_category="mechanical")
        self.seed(days_ago=29, location="Warehouse", hazard_category="mechanical")  # window edge: in
        self.seed(days_ago=30, location="Warehouse", hazard_category="mechanical")  # just outside: out
        self.seed(days_ago=40, location="Warehouse", hazard_category="mechanical")  # long gone: out
        hotspots = self.stats.recurrence_hotspots()
        self.assertEqual(len(hotspots), 1)
        self.assertEqual(hotspots[0].count, 2)
        self.assertEqual(hotspots[0].last_seen, self.today.isoformat())

    # ------------------------------------------------------------------
    # rising patterns (possible incoming incidents)
    # ------------------------------------------------------------------

    def test_rising_patterns_compare_last_week_with_the_prior_week(self):
        self.seed(days_ago=1, location="Warehouse", hazard_category="mechanical")   # recent
        self.seed(days_ago=3, location="Warehouse", hazard_category="mechanical")   # recent
        self.seed(days_ago=10, location="Warehouse", hazard_category="mechanical")  # prior
        self.seed(days_ago=2, location="Office", hazard_category="chemical")        # 1 recent
        self.seed(days_ago=9, location="Office", hazard_category="chemical")        # prior
        self.seed(days_ago=8, location="Office", hazard_category="chemical")        # prior
        rising = self.stats.rising_patterns()
        self.assertEqual([(p.location, p.hazard_category, p.recent_count, p.prior_count)
                          for p in rising],
                         [("Warehouse", "mechanical", 2, 1)],
                         "2-then-1 rises; 1-then-2 falls; and a lone new report "
                         "(0 prior, 1 recent) is not a trend")

    def test_rising_pattern_requires_two_recent_incidents(self):
        self.seed(days_ago=1, location="Laboratory", hazard_category="chemical")
        self.assertEqual(self.stats.rising_patterns(), [])

    # ------------------------------------------------------------------
    # dependency injection and the page
    # ------------------------------------------------------------------

    def test_service_accepts_any_injected_data_manager(self):
        self.seed(days_ago=0)
        independent = StatsService(DataManager(self.app))
        self.assertEqual(independent.incidents_by_severity()["high"], 1)

    def test_dashboard_renders_empty_state(self):
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No incidents are stored yet", response.data)

    def test_dashboard_renders_seeded_statistics(self):
        self.seed(days_ago=0, location="Warehouse", hazard_category="mechanical",
                  severity_score=0.8)
        self.seed(days_ago=2, location="Warehouse", hazard_category="mechanical",
                  severity_score=0.6)
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Incident dashboard &amp; trends", response.data)
        self.assertIn(b"chart.umd.min.js", response.data)
        self.assertIn(b"mechanical", response.data)
        self.assertIn(b'"total": 2', response.data)

    def test_dashboard_counts_partial_incidents_without_severity(self):
        self.seed(severity="Manual review pending", final_queue="Manual Review")
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"No incidents are stored yet", response.data)
        self.assertIn(b'"total": 1', response.data)
        self.assertIn(b'"Manual Review": 1', response.data)

    def test_dashboard_flashes_warning_when_rising_patterns_exist(self):
        self.seed(days_ago=0, location="Warehouse", hazard_category="mechanical")
        self.seed(days_ago=2, location="Warehouse", hazard_category="mechanical")
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"alert-warning", response.data)
        self.assertIn(b"rising hazard pattern(s) detected this week", response.data)
        self.assertNotIn(b'href="/trends"', response.data)

    def test_future_dated_incidents_are_excluded_from_past_windows(self):
        self.seed(days_ago=-2, location="Warehouse", hazard_category="mechanical")
        self.seed(days_ago=-3, location="Warehouse", hazard_category="mechanical")
        self.assertEqual(self.stats.recurrence_hotspots(), [])
        self.assertEqual(self.stats.rising_patterns(), [])


if __name__ == "__main__":
    unittest.main()
