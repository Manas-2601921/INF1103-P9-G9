"""Test script for logic_manager: business rules verified against hardcoded
sample AI responses, fully offline (no API key, no network).

Run with:

    .venv/bin/python test_logic_manager.py
"""

import logic_manager as logic

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}\n       {detail}")


# ---------------------------------------------------------------------------
# Hardcoded sample AI responses (the schema the AI manager returns)
# ---------------------------------------------------------------------------

def make_ai_response(severity="low", hazard_category="mechanical",
                     incident_type="near-miss", indicators=None,
                     pattern=None, explanation="Sample explanation.",
                     supporting_phrase="sample phrase"):
    """Build one hardcoded AI analysis dict with selected fields overridden."""
    return {
        "severity": severity,
        "confidence": 0.8,
        "severity_explanation": explanation,
        "hazard_category": hazard_category,
        "incident_type": incident_type,
        "indicators": dict({
            "injury": False,
            "immediate_danger": False,
            "exposure": True,
            "equipment_involvement": False,
            "work_stoppage": False,
            "uncontrolled_hazard": False,
        }, **(indicators or {})),
        "repeat_pattern_indicators": dict({
            "hazard_category": hazard_category,
            "location": "Warehouse",
            "datetime": "2026-10-01T10:00:00",
            "activity": "forklift reversing",
        }, **(pattern or {})),
        "recommended_immediate_action": "Secure the area.",
        "supporting_phrase": supporting_phrase,
    }


def make_history_entry(record_id="INC-0001", description="Forklift nearly hit a worker.",
                       location="Warehouse", datetime="2026-10-01T10:00:00",
                       ai_output=None):
    """Build one stored history record shaped like the data file entries."""
    return {
        "record_id": record_id,
        "input": {
            "description": description,
            "location": location,
            "incident_datetime": datetime,
        },
        "ai": ai_output or make_ai_response(pattern={"location": location,
                                                     "datetime": datetime}),
    }


def make_record_input(description="Forklift nearly hit a worker.", location="Warehouse",
                      datetime="2026-10-05T10:00:00"):
    """Build the input section of a new shared record."""
    return {"description": description, "location": location,
            "incident_datetime": datetime}


# ---------------------------------------------------------------------------
# validate_ai_output
# ---------------------------------------------------------------------------

def test_validate_ai_output():
    print("\n--- [1] validate_ai_output ---")
    ok, problems = logic.validate_ai_output(make_ai_response())
    check("fully valid AI response passes", ok and problems == [], f"got: {problems}")

    ok, problems = logic.validate_ai_output(
        make_ai_response(severity="extreme"))
    check("severity outside low/medium/high is rejected",
          not ok and any("invalid severity" in p for p in problems), f"got: {problems}")

    ok, problems = logic.validate_ai_output(
        make_ai_response(hazard_category="volcano"))
    check("hazard category outside the allowed set is rejected",
          not ok and any("invalid hazard_category" in p for p in problems), f"got: {problems}")

    ok, problems = logic.validate_ai_output(
        make_ai_response(incident_type="alien invasion"))
    check("incident type outside the allowed set is rejected",
          not ok and any("invalid incident_type" in p for p in problems), f"got: {problems}")

    broken = make_ai_response()
    del broken["supporting_phrase"]
    del broken["indicators"]
    ok, problems = logic.validate_ai_output(broken)
    check("missing required fields are reported",
          not ok and any("missing field: supporting_phrase" in p for p in problems)
          and any("missing field: indicators" in p for p in problems), f"got: {problems}")

    ok, problems = logic.validate_ai_output("not a dict")
    check("non-dict AI output is rejected", not ok, f"got: {ok}, {problems}")

    broken = make_ai_response()
    broken["indicators"] = []
    ok, problems = logic.validate_ai_output(broken)
    check("indicators that is not a dict is rejected",
          not ok and any("indicators" in p for p in problems), f"got: {problems}")


# ---------------------------------------------------------------------------
# indicator and hazard helpers
# ---------------------------------------------------------------------------

def test_helpers():
    print("\n--- [2] indicator and hazard helpers ---")
    check("injury indicator triggers the safety override",
          logic.has_injury_or_immediate_danger(make_ai_response(indicators={"injury": True})))
    check("immediate danger indicator triggers the safety override",
          logic.has_injury_or_immediate_danger(
              make_ai_response(indicators={"immediate_danger": True})))
    check("uncontrolled hazard indicator triggers the safety override",
          logic.has_injury_or_immediate_danger(
              make_ai_response(indicators={"uncontrolled_hazard": True})))
    check("incident type injury triggers the safety override",
          logic.has_injury_or_immediate_danger(make_ai_response(incident_type="injury")))
    check("safe response does not trigger the override",
          not logic.has_injury_or_immediate_danger(make_ai_response()))

    check("fire hazard is an escalation hazard",
          logic.is_fire_or_electrical_hazard(make_ai_response(hazard_category="fire")))
    check("electrical hazard is an escalation hazard",
          logic.is_fire_or_electrical_hazard(make_ai_response(hazard_category="electrical")))
    check("mechanical hazard is not an escalation hazard",
          not logic.is_fire_or_electrical_hazard(make_ai_response()))


# ---------------------------------------------------------------------------
# is_similar_incident and find_recent_similar_incidents
# ---------------------------------------------------------------------------

def test_similarity():
    print("\n--- [3] recurrence detection ---")
    record = make_record_input()
    ai = make_ai_response()
    past = make_history_entry()

    check("same category, location and activity is similar",
          logic.is_similar_incident(record, ai, past["input"], past["ai"]))
    check("different activity is not similar",
          not logic.is_similar_incident(
              record, ai, past["input"],
              make_ai_response(pattern={"activity": "welding"})))
    check("different location is not similar",
          not logic.is_similar_incident(
              record, ai,
              make_history_entry(location="Office")["input"],
              make_ai_response(pattern={"location": "Office"})))
    check("different hazard category is not similar",
          not logic.is_similar_incident(
              record, ai, past["input"],
              make_ai_response(hazard_category="chemical")))

    # Window tests around a reference date of 2026-10-05
    recent = make_history_entry(datetime="2026-09-20T09:00:00")
    old = make_history_entry(record_id="INC-0002", datetime="2026-01-20T09:00:00")
    found = logic.find_recent_similar_incidents(
        record, ai, [recent, old], reference_date="2026-10-05T10:00:00")
    check("incident inside the 30-day window is found",
          [entry["record_id"] for entry in found] == ["INC-0001"], f"got: {found}")
    check("incident outside the 30-day window is ignored",
          logic.find_recent_similar_incidents(
              record, ai, [old], reference_date="2026-10-05T10:00:00") == [])
    check("history entries with unparseable dates are skipped, not crashed on",
          logic.find_recent_similar_incidents(
              record, ai,
              [make_history_entry(datetime="not a date")],
              reference_date="2026-10-05T10:00:00") == [])


# ---------------------------------------------------------------------------
# find_possible_duplicate
# ---------------------------------------------------------------------------

def test_duplicates():
    print("\n--- [4] duplicate detection ---")
    record = make_record_input(datetime="2026-10-01T10:00:00",
                               description="Forklift nearly hit a worker while reversing.")
    ai = make_ai_response()

    same_again = make_history_entry(description="Forklift nearly hit a worker while reversing!")
    duplicate = logic.find_possible_duplicate(record, ai, [same_again])
    check("same datetime, location, category and near-identical text is a duplicate",
          duplicate is not None, "got: None")

    different_text = make_history_entry(description="Worker forgot to lock the trailer.")
    check("same fields but clearly different text is not a duplicate",
          logic.find_possible_duplicate(record, ai, [different_text]) is None)

    different_location = make_history_entry(location="Office")
    check("same text at a different location is not a duplicate",
          logic.find_possible_duplicate(record, ai, [different_location]) is None)

    different_time = make_history_entry(datetime="2026-10-01T11:00:00")
    check("same text at a different datetime is not a duplicate",
          logic.find_possible_duplicate(record, ai, [different_time]) is None)

    check("empty history yields no duplicate",
          logic.find_possible_duplicate(record, ai, []) is None)


# ---------------------------------------------------------------------------
# determine_final_status: the business rules end to end
# ---------------------------------------------------------------------------

def test_final_status():
    print("\n--- [5] determine_final_status business rules ---")
    empty_history = []

    result = logic.determine_final_status(
        make_record_input(), make_ai_response(severity="high", hazard_category="fire"),
        empty_history)
    check("high severity + fire hazard routes to Immediate Action with escalation",
          result["final_queue"] == "Immediate Action" and result["escalation_required"],
          f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(), make_ai_response(severity="high", hazard_category="electrical"),
        empty_history)
    check("high severity + electrical hazard routes to Immediate Action",
          result["final_queue"] == "Immediate Action" and result["escalation_required"],
          f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(),
        make_ai_response(severity="low", incident_type="injury",
                         indicators={"injury": True}),
        empty_history)
    check("low severity with reported injury is overridden out of the routine queue",
          result["final_queue"] == "Priority Review" and not result["escalation_required"],
          f"got: {result}")

    history = [make_history_entry(datetime="2026-09-28T10:00:00")]
    result = logic.determine_final_status(
        make_record_input(datetime="2026-10-05T10:00:00"),
        make_ai_response(pattern={"datetime": "2026-10-05T10:00:00"}),
        history, reference_date="2026-10-05T10:00:00")
    check("low severity with a similar incident in the last 30 days is Recurring Review",
          result["final_queue"] == "Recurring Review" and result["recurring"],
          f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(), make_ai_response(), empty_history)
    check("low severity isolated incident is a Routine Log",
          result["final_queue"] == "Routine Log", f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(), make_ai_response(severity="medium"), empty_history)
    check("medium severity isolated incident is a Routine Log",
          result["final_queue"] == "Routine Log", f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(), {"severity": "unexpected", "hazard_category": "fire"},
        empty_history)
    check("invalid AI output is quarantined in Manual Review",
          result["final_queue"] == "Manual Review"
          and "invalid AI output" in result["rule_applied"], f"got: {result}")

    result = logic.determine_final_status(
        make_record_input(), make_ai_response(explanation="Hot work sparked a fire."),
        empty_history)
    check("AI explanation and supporting phrase are carried into the decision",
          result["ai_explanation"] == "Hot work sparked a fire."
          and result["supporting_phrase"] == "sample phrase", f"got: {result}")


def main():
    print("=" * 64)
    print("logic_manager tests (hardcoded sample AI responses, offline)")
    print("=" * 64)
    test_validate_ai_output()
    test_helpers()
    test_similarity()
    test_duplicates()
    test_final_status()
    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
