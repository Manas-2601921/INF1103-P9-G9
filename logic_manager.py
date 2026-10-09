from datetime import datetime, timedelta
from difflib import SequenceMatcher

severity_levels = {"low", "medium", "high"}

hazard_categories = {
    "electrical", "fire", "chemical", "slip trip fall",
    "mechanical", "other",
}

incident_types = {
    "injury", "property damage", "complaint",
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


def validate_ai_output(ai_output):
    """Validate that an AI output dict has all required fields with allowed values.

    Checks that ``ai_output`` is a dict, that every field in
    ``required_ai_fields`` is present and non-empty, that fields covered by
    ``field_value_rules`` contain one of their allowed values, and that
    ``indicators`` (if present) is a dict.

    Args:
        ai_output: The AI-generated output to validate.

    Returns:
        tuple[bool, list[str]]: A pair of ``(is_valid, problems)`` where
        ``is_valid`` is ``True`` when no problems were found, and
        ``problems`` is a list of human-readable descriptions of each
        validation issue encountered.
    """
    problems = []

    if not isinstance(ai_output, dict):
        return False, ["ai_output is not a dict"]
    for field in required_ai_fields:
        if field not in ai_output or ai_output[field] in (None, ""):
            problems.append(f"missing field: {field}")
            continue

        for rule_field, allowed_values in field_value_rules:
            if field == rule_field and ai_output[field] not in allowed_values:
                problems.append(f"invalid {field}: {ai_output[field]}")

    indicators = ai_output.get("indicators")
    if indicators is not None and not isinstance(indicators, dict):
        problems.append("indicators must be a dict")

    return len(problems) == 0, problems


def has_injury_or_immediate_danger(ai_output):
    """Determine whether the AI output signals injury or an unsafe situation.

    Treated as true when the ``indicators`` dict flags ``injury``,
    ``immediate_danger`` or ``uncontrolled_hazard``, or when
    ``incident_type`` is ``"injury"``.

    Args:
        ai_output: The AI-generated output to inspect.

    Returns:
        bool: True if any injury or immediate-danger indicator is present.
    """
    indicators = ai_output.get("indicators", {}) or {}
    return bool(
        indicators.get("injury")
        or indicators.get("immediate_danger")
        or indicators.get("uncontrolled_hazard")
        or ai_output.get("incident_type") == "injury"
    )


def has_reporter_ai_contradiction(record, ai_output):
    """Check whether a reporter-flagged injury is unsupported by the AI output.

    Args:
        record: The original incident record, expected to contain the
            ``injury_reported`` field.
        ai_output: The AI-generated output for the same incident.

    Returns:
        bool: True if the reporter indicated an injury occurred but the AI
        output does not reflect an injury or immediate danger; False if no
        injury was reported, or if the AI output agrees with the report.
    """
    if not record.get("injury_reported"):
        return False
    return not has_injury_or_immediate_danger(ai_output)


def is_fire_or_electrical_hazard(ai_output):
    """Check whether the AI-classified hazard category requires escalation.

    Args:
        ai_output: The AI-generated output to inspect.

    Returns:
        bool: True if ``hazard_category`` is one of ``escalation_hazards``
        (fire or electrical).
    """
    return ai_output.get("hazard_category") in escalation_hazards


def _parse_date(date_str):
    """Parse a date string into a ``datetime`` using the supported formats.

    Tries ``"%d-%m-%Y %H:%M"`` first, then falls back to ``"%d-%m-%Y"``.

    Args:
        date_str: The date string to parse, or any non-string value.

    Returns:
        datetime | None: The parsed ``datetime``, or ``None`` if
        ``date_str`` is not a string or does not match a supported format.
    """
    if not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str, "%d-%m-%Y %H:%M")
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        return None


def _incident_datetime(record):
    """Return the raw incident datetime value stored on a record.

    Args:
        record: The incident record to read from.

    Returns:
        The value of ``record["incident_datetime"]``, or ``None`` if absent.
    """
    return record.get("incident_datetime")


def is_similar_incident(record, ai_output, past_record, past_ai_output):
    """Determine whether two incidents represent a recurring pattern.

    Two incidents are considered similar when they share the same hazard
    category, incident type, location, and a non-empty matching activity,
    using the ``repeat_pattern_indicators`` hints when available and
    falling back to the record/AI-output fields otherwise.

    Args:
        record: The current incident record.
        ai_output: The AI-generated output for the current incident.
        past_record: A previously logged incident record.
        past_ai_output: The AI-generated output for ``past_record``.

    Returns:
        bool: True if the two incidents match on hazard category, incident
        type, location, and a shared non-empty activity.
    """
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


def find_recent_similar_incidents(record, ai_output, history, reference_date=None, window_days=recurrence_window_days):
    """Find past incidents similar to the current one within a time window.

    Args:
        record: The current incident record.
        ai_output: The AI-generated output for the current incident.
        history: An iterable of past entries, each a dict with ``"input"``
            and ``"ai"`` keys holding the past record and AI output.
        reference_date: Optional date string used as the end of the lookup
            window; defaults to the current record's incident datetime, or
            ``datetime.now()`` if that cannot be parsed.
        window_days: Number of days before ``reference_date`` to search.
            Defaults to ``recurrence_window_days``.

    Returns:
        list: The subset of ``history`` entries whose incident date falls
        within the window and that are similar to ``record``/``ai_output``
        per :func:`is_similar_incident`.
    """
    ref_date = _parse_date(reference_date) or _parse_date(_incident_datetime(record)) or datetime.now()
    cutoff = ref_date - timedelta(days=window_days)

    similar = []
    for past_entry in history:
        past_record = past_entry.get("input", {})
        past_ai_output = past_entry.get("ai", {})
        past_date = _parse_date(_incident_datetime(past_record))
        if past_date is None or not (cutoff <= past_date <= ref_date):
            continue

        if is_similar_incident(record, ai_output, past_record, past_ai_output):
            similar.append(past_entry)

    return similar


def _text_similarity(text_a, text_b):
    """Compute a normalized similarity ratio between two text strings.

    Comparison is case-insensitive and ignores leading/trailing whitespace.

    Args:
        text_a: The first text value (may be ``None``).
        text_b: The second text value (may be ``None``).

    Returns:
        float: A similarity ratio between 0.0 and 1.0, as produced by
        ``difflib.SequenceMatcher``.
    """
    return SequenceMatcher(None, (text_a or "").strip().lower(), (text_b or "").strip().lower()).ratio()


def find_possible_duplicate(record, ai_output, history):
    """Find a past incident entry that is likely a duplicate of this one.

    A past entry is considered a possible duplicate when it shares the same
    incident datetime, location, hazard category and incident type, and its
    description text similarity meets ``duplicate_text_similarity_threshold``.

    Args:
        record: The current incident record.
        ai_output: The AI-generated output for the current incident.
        history: An iterable of past entries, each a dict with ``"input"``
            and ``"ai"`` keys holding the past record and AI output.

    Returns:
        dict | None: The first matching past entry from ``history``, or
        ``None`` if no duplicate is found.
    """
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

        similarity = _text_similarity(record.get("description"), past_record.get("description"))
        if similarity >= duplicate_text_similarity_threshold:
            return past_entry

    return None


def score(ai_output):
    """Compute a numeric risk score for an AI-classified incident.

    Starts from a base score derived from severity (``low``=1, ``medium``=2,
    ``high``=3, unrecognized=0), adding 1 point each if the hazard is
    fire/electrical and if injury or immediate danger is indicated.

    Args:
        ai_output: The AI-generated output to score.

    Returns:
        int: The computed risk score.
    """
    base = {"low": 1, "medium": 2, "high": 3}.get(ai_output.get("severity"), 0)
    if is_fire_or_electrical_hazard(ai_output):
        base += 1
    if has_injury_or_immediate_danger(ai_output):
        base += 1
    return base


def evaluate(record, ai_output, history, reference_date=None):
    """Apply triage rules to decide how an incident should be routed.

    Validates the AI output and checks, in order, for invalid output,
    reporter/AI contradictions, high-severity fire/electrical escalation,
    injury/immediate-danger overrides, and low-severity recurrence, falling
    back to routine logging when no other rule applies. Also flags whether
    the incident is a possible duplicate of a past entry.

    Args:
        record: The current incident record.
        ai_output: The AI-generated output for the current incident.
        history: An iterable of past entries, each a dict with ``"input"``
            and ``"ai"`` keys, used for recurrence and duplicate checks.
        reference_date: Optional date string used as the reference point
            for recurrence checks; defaults to the record's incident
            datetime or the current time.

    Returns:
        dict: A result dict with keys ``final_queue`` (the routing queue
        name), ``recurring`` (bool), ``duplicate_possible`` (bool),
        ``escalation_required`` (bool), and ``rule_applied`` (a
        human-readable explanation of which rule determined the outcome).
    """
    is_valid, problems = validate_ai_output(ai_output)
    if not is_valid:
        return {
            "final_queue": status_manual_review,
            "recurring": False,
            "duplicate_possible": False,
            "escalation_required": False,
            "rule_applied": f"invalid AI output: {'; '.join(problems)}",
        }

    if has_reporter_ai_contradiction(record, ai_output):
        return {
            "final_queue": status_manual_review,
            "recurring": False,
            "duplicate_possible": False,
            "escalation_required": False,
            "rule_applied": "reporter flagged an injury but AI output did not reflect it: contradictory AI output",
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
        "escalation_required": high_severity_escalation,
        "rule_applied": rule_applied,
    }


def route(record, ai_output, history, reference_date=None):
    """Determine only the routing queue for an incident.

    A thin convenience wrapper around :func:`evaluate` that returns just
    the ``final_queue`` value.

    Args:
        record: The current incident record.
        ai_output: The AI-generated output for the current incident.
        history: An iterable of past entries used for recurrence and
            duplicate checks.
        reference_date: Optional date string used as the reference point
            for recurrence checks.

    Returns:
        str: The name of the queue the incident should be routed to.
    """
    return evaluate(record, ai_output, history, reference_date)["final_queue"]


determine_final_status = evaluate