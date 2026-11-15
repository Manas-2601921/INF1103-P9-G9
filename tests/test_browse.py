"""Offline integration coverage for Pair B search and incident details."""
from unittest.mock import patch

from dashboard.incident import Incident
from data_manager import DataLoadError
from tests.dashboard_test_case import DashboardTestCase


class BrowseTests(DashboardTestCase):
    def store(self, title="Forklift reversing", occurred="2026-11-11T09:00:30", **overrides):
        record = {
            "input": {"incident_name": title, "description": "A forklift nearly struck a worker.",
                      "location": "Warehouse", "reporter_role": "Employee",
                      "incident_datetime": occurred, "injury_reported": False,
                      "immediate_action": "Work stopped"},
            "ai": {"severity": "high", "severity_score": 0.85, "hazard_category": "mechanical",
                   "incident_type": "near-miss", "severity_explanation": "Moving equipment nearby.",
                   "repeat_pattern_indicators": {"activity": "reversing"},
                   "recommended_immediate_action": "Isolate the loading bay."},
            "logic": {"final_queue": "Priority Review", "recurring": False},
        }
        for section, values in overrides.items():
            record[section].update(values)
        return self.data_manager.save(Incident.from_dict(record))

    def test_empty_page_and_navigation(self):
        response = self.app.test_client().get("/search")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"0 incidents found", response.data)
        self.assertIn(b"All incidents", response.data)
        self.assertIn(b"No incidents match", response.data)
        for path in ("/", "/incidents", "/incidents/add"):
            self.assertIn(b'href="/search"', self.app.test_client().get(path).data)

    def test_combined_filters_and_partial_title(self):
        target = self.store()
        self.store(title="Office trip", input={"location": "Office"}, ai={"hazard_category": "slip/trip/fall"})
        response = self.app.test_client().get("/search", query_string={
            "incident_name": "FORK", "hazard_category": "mechanical", "location": "ware",
            "severity": "high", "final_queue": "Priority Review", "injury_reported": "no",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 incident found", response.data)
        self.assertIn(target.record_id.encode(), response.data)
        self.assertNotIn(b"Office trip", response.data)
        self.assertIn(b"Title: FORK", response.data)

    def test_exact_title_id_and_missing_result(self):
        target = self.store()
        client = self.app.test_client()
        for query, expected in (({"incident_name": "fork", "name_match": "exact"}, b"0 incidents found"),
                                ({"incident_name": "forklift reversing", "name_match": "exact"}, b"1 incident found"),
                                ({"record_id": target.record_id.lower()}, b"1 incident found"),
                                ({"record_id": "INC-999999"}, b"0 incidents found")):
            with self.subTest(query=query):
                response = client.get("/search", query_string=query)
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.data)

    def test_date_range_includes_entire_end_day_and_specific_minute(self):
        self.store(occurred="2026-11-11T23:59:59")
        self.store(title="Legacy date report", occurred="11-11-2026 09:00")
        self.store(title="Following day report", occurred="2026-11-12T00:00:00")
        client = self.app.test_client()
        response = client.get("/search", query_string={"date_mode": "range", "date_from": "2026-11-11", "date_to": "2026-11-11"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2 incidents found", response.data)
        response = client.get("/search", query_string={"date_mode": "exact", "specific_datetime": "2026-11-11T23:59"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 incident found", response.data)
        response = client.get("/search", query_string={"date_mode": "range", "date_from": "2026-11-12"})
        self.assertIn(b"1 incident found", response.data)

    def test_invalid_filters_render_errors_without_searching(self):
        queries = ({"record_id": "oops"}, {"severity": "critical"}, {"date_mode": "oops"},
                   {"date_mode": "range"}, {"date_mode": "range", "date_from": "bad"},
                   {"date_mode": "range", "date_from": "2026-11-12", "date_to": "2026-11-11"},
                   {"date_mode": "exact", "specific_datetime": "2026-11-11"},
                   {"date_mode": "exact", "specific_datetime": "2026-11-11T09:00+08:00"},
                   {"page": "-1"}, {"page": "9999999999999999999"})
        import managers
        with patch.object(managers.io_manager, "search_incidents") as search:
            for query in queries:
                with self.subTest(query=query):
                    response = self.app.test_client().get("/search", query_string=query)
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b"Please correct", response.data)
            search.assert_not_called()

    def test_search_failure_is_friendly_and_does_not_reset_database(self):
        self.store()
        import managers
        with patch.object(managers.io_manager, "search_incidents", side_effect=DataLoadError("broken")):
            response = self.app.test_client().get("/search")
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Incidents could not be loaded", response.data)
        self.assertNotIn(b"0 incidents found", response.data)
        self.assertEqual(len(self.data_manager.load()), 1)

    def test_pagination_preserves_filters_and_clamps_page(self):
        for i in range(21):
            self.store(title=f"Forklift report {i}")
        client = self.app.test_client()
        response = client.get("/search?incident_name=Forklift&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Showing 21", response.data)
        self.assertIn(b"Page 2 of 2", response.data)
        self.assertIn(b"Forklift report 20", response.data)
        self.assertNotIn(b">Forklift report 0<", response.data)
        self.assertIn(b"incident_name=Forklift", response.data)
        response = client.get("/search?page=999")
        self.assertIn(b"Page 2 of 2", response.data)

    def test_detail_sections_and_safe_back_link(self):
        incident = self.store()
        response = self.app.test_client().get(f"/incidents/{incident.record_id}", query_string={"search": "incident_name=Forklift&page=2"})
        self.assertEqual(response.status_code, 200)
        for heading in (b"Inputs", b"Review", b"Repeating unsafe practices", b"Recommendation"):
            self.assertIn(b"<h2>" + heading + b"</h2>", response.data)
        for value in (b"Priority Review", b"Moving equipment nearby.", b"mechanical", b"near-miss", b"reversing", b"Isolate the loading bay."):
            self.assertIn(value, response.data)
        self.assertIn(b"Back to search results", response.data)
        self.assertIn(b'/search?incident_name=Forklift&amp;page=2#results-heading', response.data)
        self.assertEqual(self.app.test_client().get("/incidents/INC-999999").status_code, 302)

    def test_search_text_is_escaped_and_sql_wildcards_are_literal(self):
        self.store(title="100% safety review")
        self.store(title="1000 safety review")
        response = self.app.test_client().get("/search", query_string={"incident_name": "100%"})
        self.assertIn(b"1 incident found", response.data)
        response = self.app.test_client().get("/search", query_string={"incident_name": "<script>alert(1)</script>"})
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertIn(b"&lt;script&gt;", response.data)

    def test_manual_review_and_legacy_severity_remain_searchable(self):
        self.store(title="Unassessed report", ai={"severity": None, "severity_score": None, "ai_error": "offline"},
                   logic={"final_queue": "Manual Review"})
        self.store(title="Legacy numeric report", ai={"severity": "0.86", "severity_score": None})
        for severity, expected in (("unassessed", b"Unassessed report"), ("high", b"Legacy numeric report")):
            response = self.app.test_client().get("/search", query_string={"severity": severity})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"1 incident found", response.data)
            self.assertIn(expected, response.data)
