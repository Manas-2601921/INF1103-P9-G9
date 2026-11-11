"""Tests for logic_manager.

Uses hardcoded AI output dicts instead of calling ai_manager / the real
API, so this runs fine with no API key and no network - needed since we
have to be able to run this inside Docker too.

Run with: python test_logic_manager.py
"""

import unittest

from logic_manager import LogicManager


def dummy_ai(**kw):
    """Default ai output that satisfies the schema; tests override
    whatever fields they care about."""
    out = {
        "severity": "low",
        "confidence": 0.9,
        "severity_explanation": "A minor hazard with no immediate danger.",
        "hazard_category": "ergonomic",
        "incident_type": "unsafe condition",
        "indicators": {
            "injury": False,
            "immediate_danger": False,
            "exposure": False,
            "equipment_involvement": False,
            "work_stoppage": False,
            "uncontrolled_hazard": False,
        },
        "repeat_pattern_indicators": {
            "hazard_category": "ergonomic",
            "location": "Office",
            "datetime": "2026-09-21T10:00:00",
            "activity": "lifting",
        },
        "recommended_immediate_action": "Review the workstation setup.",
        "supporting_phrase": "a minor hazard",
    }
    out.update(kw)
    return out


def dummy_record(**kw):
    """Default incident record; tests override whatever fields they
    care about."""
    rec = {
        "description": "An employee reported minor back strain after lifting a box.",
        "location": "Office",
        "reporter_role": "Employee",
        "incident_datetime": "2026-09-21T10:00:00",
        "injury_reported": False,
        "immediate_action": "No immediate action was taken",
    }
    rec.update(kw)
    return rec


class LogicManagerValidationTests(unittest.TestCase):
    """validate_ai_output: schema checks on the AI's reply."""

    def setUp(self):
        self.lm = LogicManager()

    def test_valid_ai_output_has_no_problems(self):
        ok, problems = self.lm.validate_ai_output(dummy_ai())
        self.assertTrue(ok)
        self.assertEqual(problems, [])

    def test_non_dict_ai_output_is_rejected(self):
        ok, problems = self.lm.validate_ai_output("not a dict")
        self.assertFalse(ok)

    def test_missing_field_is_caught(self):
        bad = dummy_ai()
        del bad["hazard_category"]
        ok, problems = self.lm.validate_ai_output(bad)
        self.assertFalse(ok)
        self.assertTrue(any("hazard_category" in p for p in problems), problems)

    def test_bad_severity_value_is_caught(self):
        ok, problems = self.lm.validate_ai_output(dummy_ai(severity="extremely bad"))
        self.assertFalse(ok, problems)

    def test_indicators_not_a_dict_is_caught(self):
        ok, problems = self.lm.validate_ai_output(dummy_ai(indicators="nope"))
        self.assertFalse(ok, problems)


class LogicManagerIndicatorTests(unittest.TestCase):
    """has_injury_or_immediate_danger and has_reporter_ai_contradiction."""

    def setUp(self):
        self.lm = LogicManager()

    def test_injury_flag_is_detected(self):
        self.assertTrue(self.lm.has_injury_or_immediate_danger(dummy_ai(indicators={"injury": True})))

    def test_immediate_danger_flag_is_detected(self):
        self.assertTrue(self.lm.has_injury_or_immediate_danger(dummy_ai(indicators={"immediate_danger": True})))

    def test_uncontrolled_hazard_flag_is_detected(self):
        self.assertTrue(self.lm.has_injury_or_immediate_danger(dummy_ai(indicators={"uncontrolled_hazard": True})))

    def test_incident_type_injury_also_counts(self):
        self.assertTrue(self.lm.has_injury_or_immediate_danger(dummy_ai(incident_type="injury")))

    def test_nothing_flagged_is_false(self):
        self.assertFalse(self.lm.has_injury_or_immediate_danger(dummy_ai()))

    def test_no_injury_reported_is_never_a_contradiction(self):
        self.assertFalse(self.lm.has_reporter_ai_contradiction(dummy_record(injury_reported=False), dummy_ai()))

    def test_injury_reported_but_ai_disagrees_is_a_contradiction(self):
        self.assertTrue(self.lm.has_reporter_ai_contradiction(dummy_record(injury_reported=True), dummy_ai()))

    def test_injury_reported_and_ai_agrees_is_not_a_contradiction(self):
        self.assertFalse(self.lm.has_reporter_ai_contradiction(
            dummy_record(injury_reported=True), dummy_ai(indicators={"injury": True})
        ))


class LogicManagerHazardTests(unittest.TestCase):
    """is_fire_or_electrical_hazard."""

    def setUp(self):
        self.lm = LogicManager()

    def test_fire_counts_as_escalation_hazard(self):
        self.assertTrue(self.lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="fire")))

    def test_electrical_counts_as_escalation_hazard(self):
        self.assertTrue(self.lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="electrical")))

    def test_ergonomic_does_not_count_as_escalation_hazard(self):
        self.assertFalse(self.lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="ergonomic")))


class LogicManagerRecurrenceTests(unittest.TestCase):
    """find_recent_similar_incidents and is_similar_incident."""

    def setUp(self):
        self.lm = LogicManager()
        self.record = dummy_record(incident_datetime="2026-09-25T10:00:00", location="Warehouse A")
        self.ai_out = dummy_ai(
            hazard_category="mechanical",
            incident_type="near-miss",
            repeat_pattern_indicators={
                "hazard_category": "mechanical",
                "location": "Warehouse A",
                "datetime": "2026-09-25T10:00:00",
                "activity": "forklift operation",
            },
        )
        self.past_entry = {
            "input": dummy_record(incident_datetime="2026-09-20T10:00:00", location="Warehouse A"),
            "ai": dummy_ai(
                hazard_category="mechanical",
                incident_type="near-miss",
                repeat_pattern_indicators={
                    "hazard_category": "mechanical",
                    "location": "Warehouse A",
                    "datetime": "2026-09-20T10:00:00",
                    "activity": "forklift operation",
                },
            ),
        }

    def test_iso_datetime_gets_parsed_and_similar_incident_found(self):
        """logic_manager used to only understand DD-MM-YYYY dates, so real
        ISO datetimes never matched and recurrence never fired. Make sure
        that's actually fixed."""
        similar = self.lm.find_recent_similar_incidents(self.record, self.ai_out, [self.past_entry])
        self.assertEqual(similar, [self.past_entry])

    def test_incident_outside_the_30_day_window_is_ignored(self):
        old_entry = {
            "input": dummy_record(incident_datetime="2026-01-01T10:00:00", location="Warehouse A"),
            "ai": self.past_entry["ai"],
        }
        self.assertEqual(self.lm.find_recent_similar_incidents(self.record, self.ai_out, [old_entry]), [])

    def test_same_hazard_but_different_location_does_not_count(self):
        diff_loc_entry = {
            "input": dummy_record(incident_datetime="2026-09-20T10:00:00", location="Office"),
            "ai": dummy_ai(
                hazard_category="mechanical",
                incident_type="near-miss",
                repeat_pattern_indicators={
                    "hazard_category": "mechanical",
                    "location": "Office",
                    "datetime": "2026-09-20T10:00:00",
                    "activity": "forklift operation",
                },
            ),
        }
        self.assertEqual(self.lm.find_recent_similar_incidents(self.record, self.ai_out, [diff_loc_entry]), [])

    def test_same_hazard_type_location_and_activity_is_similar(self):
        matching_past_ai = dummy_ai(
            hazard_category="mechanical",
            incident_type="near-miss",
            repeat_pattern_indicators={
                "hazard_category": "mechanical",
                "location": "Warehouse A",
                "datetime": "2026-09-20T10:00:00",
                "activity": "forklift operation",
            },
        )
        self.assertTrue(
            self.lm.is_similar_incident(self.record, self.ai_out, self.past_entry["input"], matching_past_ai)
        )

    def test_different_activity_is_not_similar(self):
        diff_activity_ai = dummy_ai(
            hazard_category="mechanical",
            incident_type="near-miss",
            repeat_pattern_indicators={
                "hazard_category": "mechanical",
                "location": "Warehouse A",
                "datetime": "2026-09-20T10:00:00",
                "activity": "pallet stacking",
            },
        )
        self.assertFalse(
            self.lm.is_similar_incident(self.record, self.ai_out, self.past_entry["input"], diff_activity_ai)
        )


class LogicManagerDuplicateTests(unittest.TestCase):
    """find_possible_duplicate, and duplicate_possible via determine_final_status."""

    def setUp(self):
        self.lm = LogicManager()
        self.dup_record = dummy_record(
            incident_datetime="2026-09-21T20:30:00",
            location="Warehouse A",
            description="Exposed electrical cable with damaged insulation found near the maintenance bay.",
        )
        self.dup_ai = dummy_ai(hazard_category="electrical", incident_type="unsafe condition")
        self.dup_past = {
            "input": dummy_record(
                incident_datetime="2026-09-21T20:30:00",
                location="Warehouse A",
                description="Exposed electrical cable with damaged insulation spotted near the maintenance bay.",
            ),
            "ai": dummy_ai(hazard_category="electrical", incident_type="unsafe condition"),
        }

    def test_near_identical_report_is_flagged_as_duplicate(self):
        found = self.lm.find_possible_duplicate(self.dup_record, self.dup_ai, [self.dup_past])
        self.assertEqual(found, self.dup_past)

    def test_different_description_same_time_and_place_is_not_a_duplicate(self):
        unrelated = {
            "input": dummy_record(
                incident_datetime="2026-09-21T20:30:00",
                location="Warehouse A",
                description="A completely unrelated incident about a spilled drink in the break room.",
            ),
            "ai": dummy_ai(hazard_category="electrical", incident_type="unsafe condition"),
        }
        self.assertIsNone(self.lm.find_possible_duplicate(self.dup_record, self.dup_ai, [unrelated]))

    def test_near_duplicate_incident_sets_duplicate_possible_true(self):
        """duplicate_possible needs to be checked end-to-end too, not just
        via find_possible_duplicate() directly - this is what actually
        reaches main.py's print_triage_summary()."""
        r = self.lm.determine_final_status(self.dup_record, self.dup_ai, [self.dup_past])
        self.assertTrue(r["duplicate_possible"])

    def test_no_matching_history_sets_duplicate_possible_false(self):
        r = self.lm.determine_final_status(dummy_record(), dummy_ai(), [])
        self.assertFalse(r["duplicate_possible"])


class LogicManagerTriageTests(unittest.TestCase):
    """determine_final_status (the actual triage rules) and route()."""

    def setUp(self):
        self.lm = LogicManager()

    def test_invalid_ai_output_goes_to_manual_review(self):
        r = self.lm.determine_final_status(dummy_record(), {"not": "valid"}, [])
        self.assertEqual(r["final_queue"], self.lm.status_manual_review)

    def test_reporter_ai_contradiction_goes_to_manual_review(self):
        r = self.lm.determine_final_status(dummy_record(injury_reported=True), dummy_ai(), [])
        self.assertEqual(r["final_queue"], self.lm.status_manual_review)

    def test_high_severity_fire_is_immediate_action_with_escalation(self):
        r = self.lm.determine_final_status(dummy_record(), dummy_ai(severity="high", hazard_category="fire"), [])
        self.assertEqual(r["final_queue"], self.lm.status_immediate_action)
        self.assertTrue(r["escalation_required"])

    def test_immediate_danger_is_priority_review(self):
        r = self.lm.determine_final_status(
            dummy_record(), dummy_ai(severity="medium", indicators={"immediate_danger": True}), []
        )
        self.assertEqual(r["final_queue"], self.lm.status_priority_review)

    def test_low_severity_with_recent_similar_incident_is_recurring_review(self):
        recurring_record = dummy_record(incident_datetime="2026-09-25T10:00:00", location="Warehouse A")
        recurring_ai = dummy_ai(
            severity="low",
            hazard_category="mechanical",
            incident_type="near-miss",
            repeat_pattern_indicators={
                "hazard_category": "mechanical",
                "location": "Warehouse A",
                "datetime": "2026-09-25T10:00:00",
                "activity": "forklift operation",
            },
        )
        past_entry = {
            "input": dummy_record(incident_datetime="2026-09-20T10:00:00", location="Warehouse A"),
            "ai": dummy_ai(
                hazard_category="mechanical",
                incident_type="near-miss",
                repeat_pattern_indicators={
                    "hazard_category": "mechanical",
                    "location": "Warehouse A",
                    "datetime": "2026-09-20T10:00:00",
                    "activity": "forklift operation",
                },
            ),
        }
        r = self.lm.determine_final_status(recurring_record, recurring_ai, [past_entry])
        self.assertEqual(r["final_queue"], self.lm.status_recurring_review)
        self.assertTrue(r["recurring"])

    def test_nothing_special_is_routine_log(self):
        r = self.lm.determine_final_status(dummy_record(), dummy_ai(), [])
        self.assertEqual(r["final_queue"], self.lm.status_routine_log)

    def test_route_returns_the_queue_string(self):
        """route() is just a wrapper around determine_final_status that
        returns the queue name - used for main.py's pre-save preview."""
        self.assertEqual(self.lm.route(dummy_record(), dummy_ai(), []), self.lm.status_routine_log)


class LogicManagerScoreTests(unittest.TestCase):
    """score()."""

    def setUp(self):
        self.lm = LogicManager()

    def test_low_severity_no_escalation_hazard_no_danger_scores_1(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="low")), 1)

    def test_medium_severity_scores_2(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="medium")), 2)

    def test_high_severity_scores_3(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="high")), 3)

    def test_fire_hazard_adds_a_point_on_top_of_severity(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="low", hazard_category="fire")), 2)

    def test_injury_or_danger_indicator_adds_a_point_on_top_of_severity(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="low", indicators={"injury": True})), 2)

    def test_fire_hazard_and_injury_both_add_up_with_high_severity(self):
        self.assertEqual(
            self.lm.score(dummy_ai(severity="high", hazard_category="electrical", indicators={"injury": True})), 5
        )

    def test_unrecognised_severity_scores_a_base_of_0(self):
        self.assertEqual(self.lm.score(dummy_ai(severity="unknown")), 0)


if __name__ == "__main__":
    unittest.main()
