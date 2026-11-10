from datetime import datetime, timedelta
from difflib import SequenceMatcher


class LogicManager:
    """Takes an incident + the AI's classification of it and decides what
    queue it should land in (escalation, recurrence, duplicates, etc)."""

    severity_levels = {"low", "medium", "high"}

    hazard_categories = {
        "electrical", "fire", "chemical", "ergonomic", "slip/trip/fall",
        "mechanical", "biological", "psychosocial", "other",
    }

    incident_types = {
        "near-miss", "injury", "unsafe condition", "property damage", "complaint",
    }

    escalation_hazards = {"fire", "electrical"}

    required_ai_fields = (
        "severity", "hazard_category", "incident_type",
        "indicators", "recommended_immediate_action", "supporting_phrase",
    )

    field_value_rules = (
        ("severity", severity_levels),
        ("hazard_category", hazard_categories),
        ("incident_type", incident_types),
    )

    recurrence_window_days = 30
    duplicate_text_similarity_threshold = 0.85

    status_immediate_action = "Immediate Action"
    status_priority_review = "Priority Review"
    status_routine_log = "Routine Log"
    status_recurring_review = "Recurring Review"
    status_manual_review = "Manual Review"

    def validate_ai_output(self, ai_output):
        """Checks ai_output has every required field, with an allowed value
        where one applies. Returns (True, []) if it's fine, otherwise
        (False, [list of problems])."""
        problems = []

        if not isinstance(ai_output, dict):
            return False, ["ai_output is not a dict"]
        for field in self.required_ai_fields:
            if field not in ai_output or ai_output[field] in (None, ""):
                problems.append(f"missing field: {field}")
                continue

            for rule_field, allowed_values in self.field_value_rules:
                if field == rule_field and ai_output[field] not in allowed_values:
                    problems.append(f"invalid {field}: {ai_output[field]}")

        indicators = ai_output.get("indicators")
        if indicators is not None and not isinstance(indicators, dict):
            problems.append("indicators must be a dict")

        return len(problems) == 0, problems

    def has_injury_or_immediate_danger(self, ai_output):
        """True if the AI flagged injury, immediate_danger or
        uncontrolled_hazard, or classified the incident_type as injury."""
        indicators = ai_output.get("indicators", {}) or {}
        return bool(
            indicators.get("injury")
            or indicators.get("immediate_danger")
            or indicators.get("uncontrolled_hazard")
            or ai_output.get("incident_type") == "injury"
        )

    def has_reporter_ai_contradiction(self, record, ai_output):
        """The reporter said someone was injured but the AI's output doesn't
        agree - this should go to a human instead of being auto-routed."""
        if not record.get("injury_reported"):
            return False
        return not self.has_injury_or_immediate_danger(ai_output)

    def is_fire_or_electrical_hazard(self, ai_output):
        return ai_output.get("hazard_category") in self.escalation_hazards

    @staticmethod
    def _parse_date(date_str):
        """Our records store ISO datetimes (main.py uses
        datetime.isoformat()), but we also try the old DD-MM-YYYY formats
        in case some older records are still around. Returns None if
        nothing matches so callers don't have to worry about exceptions."""
        if not isinstance(date_str, str):
            return None
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass
        try:
            return datetime.strptime(date_str, "%d-%m-%Y %H:%M")
        except ValueError:
            pass
        try:
            return datetime.strptime(date_str, "%d-%m-%Y")
        except ValueError:
            return None

    @staticmethod
    def _incident_datetime(record):
        return record.get("incident_datetime")

    def is_similar_incident(self, record, ai_output, past_record, past_ai_output):
        """Two incidents count as the "same kind of thing happening again"
        if they match on hazard category, incident type, location, and
        activity. Prefers the repeat_pattern_indicators hints from the AI
        but falls back to the plain record/ai fields when they're missing."""
        pattern = ai_output.get("repeat_pattern_indicators", {}) or {}
        past_pattern = past_ai_output.get("repeat_pattern_indicators", {}) or {}
        hazard_category = pattern.get("hazard_category") or ai_output.get("hazard_category")
        past_hazard_category = past_pattern.get("hazard_category") or past_ai_output.get("hazard_category")
        if hazard_category != past_hazard_category:
            return False

        if ai_output.get("incident_type") != past_ai_output.get("incident_type"):
            return False

        location = (pattern.get("location") or record.get("location") or "").strip().lower()
        past_location = (past_pattern.get("location") or past_record.get("location") or "").strip().lower()
        if location != past_location:
            return False

        activity = pattern.get("activity")
        past_activity = past_pattern.get("activity")
        return bool(activity) and activity == past_activity

    def find_recent_similar_incidents(self, record, ai_output, history, reference_date=None, window_days=None):
        """Looks back through history for similar incidents within
        window_days of reference_date (defaults to this incident's own
        datetime, or now() if that can't be parsed)."""
        if window_days is None:
            window_days = self.recurrence_window_days

        ref_date = (
            self._parse_date(reference_date)
            or self._parse_date(self._incident_datetime(record))
            or datetime.now()
        )
        cutoff = ref_date - timedelta(days=window_days)

        similar = []
        for past_entry in history:
            past_record = past_entry.get("input", {})
            past_ai_output = past_entry.get("ai", {})
            past_date = self._parse_date(self._incident_datetime(past_record))
            if past_date is None or not (cutoff <= past_date <= ref_date):
                continue

            if self.is_similar_incident(record, ai_output, past_record, past_ai_output):
                similar.append(past_entry)

        return similar

    @staticmethod
    def _text_similarity(text_a, text_b):
        """0.0-1.0 similarity ratio between two strings, case/whitespace
        insensitive. Used to catch near-duplicate descriptions."""
        return SequenceMatcher(None, (text_a or "").strip().lower(), (text_b or "").strip().lower()).ratio()

    def find_possible_duplicate(self, record, ai_output, history):
        """Same datetime + location + hazard category + incident type, and
        the description text is similar enough -> probably the same report
        got submitted twice. Returns the first match in history, or None."""
        for past_entry in history:
            past_record = past_entry.get("input", {})
            past_ai_output = past_entry.get("ai", {})
            if past_record.get("incident_datetime") != record.get("incident_datetime"):
                continue
            if (past_record.get("location") or "").strip().lower() != (record.get("location") or "").strip().lower():
                continue
            if past_ai_output.get("hazard_category") != ai_output.get("hazard_category"):
                continue
            if past_ai_output.get("incident_type") != ai_output.get("incident_type"):
                continue

            similarity = self._text_similarity(record.get("description"), past_record.get("description"))
            if similarity >= self.duplicate_text_similarity_threshold:
                return past_entry

        return None

    def score(self, ai_output):
        """low/medium/high -> 1/2/3, +1 if fire/electrical, +1 if
        injury/immediate danger. Just a rough risk number, not used for
        routing directly."""
        base = {"low": 1, "medium": 2, "high": 3}.get(ai_output.get("severity"), 0)
        if self.is_fire_or_electrical_hazard(ai_output):
            base += 1
        if self.has_injury_or_immediate_danger(ai_output):
            base += 1
        return base

    def evaluate(self, record, ai_output, history, reference_date=None):
        """The main triage call. Checks the rules in order - invalid AI
        output, reporter/AI contradiction, high severity fire/electrical,
        injury/danger override, then recurrence - and routes to the first
        one that applies, otherwise Routine Log. Also checks for duplicates
        on the side (that doesn't change the queue, just gets flagged).

        Returns a dict: final_queue, recurring, duplicate_possible,
        escalation_required, rule_applied (why), ai_explanation and
        supporting_phrase (carried over from the AI output for the report).
        """
        is_valid, problems = self.validate_ai_output(ai_output)
        if not is_valid:
            return {
                "final_queue": self.status_manual_review,
                "recurring": False,
                "duplicate_possible": False,
                "escalation_required": False,
                "rule_applied": f"invalid AI output: {'; '.join(problems)}",
                "risk_score": self.score(ai_output) if isinstance(ai_output, dict) else 0,
                "ai_explanation": ai_output.get("severity_explanation") if isinstance(ai_output, dict) else None,
                "supporting_phrase": ai_output.get("supporting_phrase") if isinstance(ai_output, dict) else None,
            }

        if self.has_reporter_ai_contradiction(record, ai_output):
            return {
                "final_queue": self.status_manual_review,
                "recurring": False,
                "duplicate_possible": False,
                "escalation_required": False,
                "rule_applied": "reporter flagged an injury but AI output did not reflect it: contradictory AI output",
                "risk_score": self.score(ai_output),
                "ai_explanation": ai_output.get("severity_explanation"),
                "supporting_phrase": ai_output.get("supporting_phrase"),
            }

        duplicate = self.find_possible_duplicate(record, ai_output, history)
        similar_incidents = self.find_recent_similar_incidents(record, ai_output, history, reference_date)
        high_severity_escalation = ai_output["severity"] == "high" and self.is_fire_or_electrical_hazard(ai_output)
        unsafe_override = self.has_injury_or_immediate_danger(ai_output)
        recurring = ai_output["severity"] == "low" and len(similar_incidents) > 0

        if high_severity_escalation:
            final_queue = self.status_immediate_action
            rule_applied = "high severity fire/electrical hazard requires immediate escalation"
        elif unsafe_override:
            final_queue = self.status_priority_review
            rule_applied = "injury, immediate danger or uncontrolled hazard cannot be routed to a routine queue"
        elif recurring:
            final_queue = self.status_recurring_review
            rule_applied = f"low severity but {len(similar_incidents)} similar incident(s) at this location in the last {self.recurrence_window_days} days"
        else:
            final_queue = self.status_routine_log
            rule_applied = "no escalation, override or recurrence conditions met"

        return {
            "final_queue": final_queue,
            "recurring": len(similar_incidents) > 0,
            "duplicate_possible": duplicate is not None,
            "escalation_required": high_severity_escalation,
            "rule_applied": rule_applied,
            "risk_score": self.score(ai_output),
            "ai_explanation": ai_output.get("severity_explanation"),
            "supporting_phrase": ai_output.get("supporting_phrase"),
        }

    def route(self, record, ai_output, history, reference_date=None):
        """Same as evaluate() but just gives back the queue name."""
        return self.evaluate(record, ai_output, history, reference_date)["final_queue"]

    determine_final_status = evaluate
