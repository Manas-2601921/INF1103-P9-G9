from datetime import datetime, timedelta
from difflib import SequenceMatcher

severity_levels = {"low", "medium", "high"}

hazard_categories = {
    "electrical", "fire", "chemical", "ergonomic", "slip_trip_fall",
    "mechanical", "other",
}

incident_types = {
    "injury", "unsafe_condition", "property_damage", "complaint",
}

escalation_hazards = {"fire", "electrical"}

required_ai_fields = (
    "severity", "hazard_category", "incident_type",
    "indicators", "recommended_immediate_action", "supporting_phrase",
)

recurrence_window_days = 30
duplicate_text_similarity_threshold = 0.85

status_immediate_action = "Immediate Action"
status_priority_review = "Priority Review"
status_routine_log = "Routine Log"
status_recurring_review = "Recurring Review"
status_manual_review = "Manual Review"


def validate_ai_output(ai_output):
    problems = []

    if not isinstance(ai_output, dict):
        return False, ["ai_output is not a dict"]
    for field in required_ai_fields:
        if field not in ai_output or ai_output[field] in (None, ""):
            problems.append(f"missing field: {field}")
    if "severity" in ai_output and ai_output["severity"] not in severity_levels:
        problems.append(f"invalid severity: {ai_output.get('severity')}")
    if "hazard_category" in ai_output and ai_output["hazard_category"] not in hazard_categories:
        problems.append(f"invalid hazard_category: {ai_output.get('hazard_category')}")
    if "incident_type" in ai_output and ai_output["incident_type"] not in incident_types:
        problems.append(f"invalid incident_type: {ai_output.get('incident_type')}")
    indicators = ai_output.get("indicators")
    if indicators is not None and not isinstance(indicators, dict):
        problems.append("indicators must be a dict")

    return len(problems) == 0, problems


def has_injury_or_immediate_danger(ai_output):
    indicators = ai_output.get("indicators", {}) or {}
    return bool(
        indicators.get("injury")
        or indicators.get("immediate_danger")
        or indicators.get("uncontrolled_hazard")
        or ai_output.get("incident_type") == "injury"
    )


def is_fire_or_electrical_hazard(ai_output):
    return ai_output.get("hazard_category") in escalation_hazards


def _parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def is_similar_incident(record, ai_output, past_record, past_ai_output):
    pattern = ai_output.get("repeat_pattern_indicators", {}) or {}
    past_pattern = past_ai_output.get("repeat_pattern_indicators", {}) or {}
    hazard_category = pattern.get("hazard_category") or ai_output.get("hazard_category")
    past_hazard_category = past_pattern.get("hazard_category") or past_ai_output.get("hazard_category")
    if hazard_category != past_hazard_category:
        return False

    location = (pattern.get("location") or record.get("location") or "").strip().lower()
    past_location = (past_pattern.get("location") or past_record.get("location") or "").strip().lower()
    if location != past_location:
        return False

    activity = pattern.get("activity")
    past_activity = past_pattern.get("activity")
    return bool(activity) and activity == past_activity


def find_recent_similar_incidents(record, ai_output, history, reference_date=None, window_days=recurrence_window_days):
    ref_date = _parse_date(reference_date) or _parse_date(record.get("incident_date")) or datetime.now()
    cutoff = ref_date - timedelta(days=window_days)

    similar = []
    for past_entry in history:
        past_record = past_entry.get("input", {})
        past_ai_output = past_entry.get("ai", {})
        past_date = _parse_date(past_record.get("incident_date"))
        if past_date is None or not (cutoff <= past_date <= ref_date):
            continue

        if is_similar_incident(record, ai_output, past_record, past_ai_output):
            similar.append(past_entry)

    return similar


def _text_similarity(text_a, text_b):
    return SequenceMatcher(None, (text_a or "").strip().lower(), (text_b or "").strip().lower()).ratio()


def find_possible_duplicate(record, ai_output, history):
    for past_entry in history:
        past_record = past_entry.get("input", {})
        past_ai_output = past_entry.get("ai", {})
        if past_record.get("incident_date") != record.get("incident_date"):
            continue
        if (past_record.get("location") or "").strip().lower() != (record.get("location") or "").strip().lower():
            continue
        if past_ai_output.get("hazard_category") != ai_output.get("hazard_category"):
            continue

        similarity = _text_similarity(record.get("description"), past_record.get("description"))
        if similarity >= duplicate_text_similarity_threshold:
            return past_entry

    return None


def determine_final_status(record, ai_output, history, reference_date=None):
    is_valid, problems = validate_ai_output(ai_output)
    if not is_valid:
        return {
            "final_queue": status_manual_review,
            "recurring": False,
            "duplicate_possible": False,
            "duplicate_of": None,
            "similar_incidents": [],
            "escalation_required": False,
            "ai_explanation": ai_output.get("severity_explanation") if isinstance(ai_output, dict) else None,
            "supporting_phrase": ai_output.get("supporting_phrase") if isinstance(ai_output, dict) else None,
            "rule_applied": f"invalid AI output: {'; '.join(problems)}",
        }

    duplicate = find_possible_duplicate(record, ai_output, history)
    similar_incidents = find_recent_similar_incidents(record, ai_output, history, reference_date)
    high_severity_escalation = ai_output["severity"] == "high" and is_fire_or_electrical_hazard(ai_output)
    unsafe_override = has_injury_or_immediate_danger(ai_output)
    recurring = ai_output["severity"] == "low" and len(similar_incidents) > 0

    if high_severity_escalation:
        final_queue = status_immediate_action
        rule_applied = "high severity fire/electrical hazard requires immediate escalation"
    elif unsafe_override:
        final_queue = status_priority_review
        rule_applied = "injury, immediate danger or uncontrolled hazard cannot be routed to a routine queue"
    elif recurring:
        final_queue = status_recurring_review
        rule_applied = f"low severity but {len(similar_incidents)} similar incident(s) at this location in the last {recurrence_window_days} days"
    else:
        final_queue = status_routine_log
        rule_applied = "no escalation, override or recurrence conditions met"

    return {
        "final_queue": final_queue,
        "recurring": len(similar_incidents) > 0,
        "duplicate_possible": duplicate is not None,
        "duplicate_of": duplicate.get("record_id") if duplicate else None,
        "similar_incidents": [past.get("record_id") for past in similar_incidents],
        "escalation_required": high_severity_escalation,
        "ai_explanation": ai_output.get("severity_explanation"),
        "supporting_phrase": ai_output.get("supporting_phrase"),
        "rule_applied": rule_applied,
    }
