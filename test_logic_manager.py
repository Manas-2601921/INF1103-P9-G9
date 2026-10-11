"""Test script for logic_manager.

Uses hardcoded AI output dicts instead of calling ai_manager / the real
API, so this runs fine with no API key and no network - needed since we
have to be able to run this inside Docker too.

run with: python test_logic_manager.py
"""

import logic_manager as lm

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name} - {detail}")


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


print("logic_manager tests")
print("-" * 40)

# --- [1] validate_ai_output ---

ok, problems = lm.validate_ai_output(dummy_ai())
check("valid ai output -> no problems", ok and problems == [])

ok, problems = lm.validate_ai_output("not a dict")
check("non-dict ai_output rejected", not ok)

bad = dummy_ai()
del bad["hazard_category"]
ok, problems = lm.validate_ai_output(bad)
check("missing field caught", not ok and any("hazard_category" in p for p in problems), problems)

ok, problems = lm.validate_ai_output(dummy_ai(severity="extremely bad"))
check("bad severity value caught", not ok, problems)

ok, problems = lm.validate_ai_output(dummy_ai(indicators="nope"))
check("indicators not a dict caught", not ok, problems)

# --- [2] has_injury_or_immediate_danger ---

check("injury flag detected", lm.has_injury_or_immediate_danger(dummy_ai(indicators={"injury": True})))
check("immediate_danger flag detected", lm.has_injury_or_immediate_danger(dummy_ai(indicators={"immediate_danger": True})))
check("uncontrolled_hazard flag detected", lm.has_injury_or_immediate_danger(dummy_ai(indicators={"uncontrolled_hazard": True})))
check("incident_type injury also counts", lm.has_injury_or_immediate_danger(dummy_ai(incident_type="injury")))
check("nothing flagged -> False", lm.has_injury_or_immediate_danger(dummy_ai()) == False)

# --- [3] has_reporter_ai_contradiction ---

check("no injury reported -> never a contradiction", lm.has_reporter_ai_contradiction(dummy_record(injury_reported=False), dummy_ai()) == False)
check("injury reported but ai disagrees -> contradiction", lm.has_reporter_ai_contradiction(dummy_record(injury_reported=True), dummy_ai()) == True)
check(
    "injury reported and ai agrees -> no contradiction",
    lm.has_reporter_ai_contradiction(dummy_record(injury_reported=True), dummy_ai(indicators={"injury": True})) == False,
)

# --- [4] is_fire_or_electrical_hazard ---

check("fire counts as escalation hazard", lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="fire")))
check("electrical counts as escalation hazard", lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="electrical")))
check("ergonomic does not", lm.is_fire_or_electrical_hazard(dummy_ai(hazard_category="ergonomic")) == False)

# --- [5] find_recent_similar_incidents (recurrence) ---

record = dummy_record(incident_datetime="2026-09-25T10:00:00", location="Warehouse A")
ai_out = dummy_ai(
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

similar = lm.find_recent_similar_incidents(record, ai_out, [past_entry])
"""this is the one that actually matters - logic_manager used to only
understand DD-MM-YYYY dates, so real ISO datetimes never matched and
recurrence never fired. make sure that's actually fixed."""
check("iso datetime gets parsed, similar incident found", similar == [past_entry], similar)

old_entry = {
    "input": dummy_record(incident_datetime="2026-01-01T10:00:00", location="Warehouse A"),
    "ai": past_entry["ai"],
}
check("incident outside the 30 day window is ignored", lm.find_recent_similar_incidents(record, ai_out, [old_entry]) == [])

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
check("same hazard but different location doesn't count", lm.find_recent_similar_incidents(record, ai_out, [diff_loc_entry]) == [])

# --- [6] find_possible_duplicate ---

dup_record = dummy_record(
    incident_datetime="2026-09-21T20:30:00",
    location="Warehouse A",
    description="Exposed electrical cable with damaged insulation found near the maintenance bay.",
)
dup_ai = dummy_ai(hazard_category="electrical", incident_type="unsafe condition")
dup_past = {
    "input": dummy_record(
        incident_datetime="2026-09-21T20:30:00",
        location="Warehouse A",
        description="Exposed electrical cable with damaged insulation spotted near the maintenance bay.",
    ),
    "ai": dummy_ai(hazard_category="electrical", incident_type="unsafe condition"),
}
found = lm.find_possible_duplicate(dup_record, dup_ai, [dup_past])
check("near identical report flagged as duplicate", found == dup_past)

unrelated = {
    "input": dummy_record(
        incident_datetime="2026-09-21T20:30:00",
        location="Warehouse A",
        description="A completely unrelated incident about a spilled drink in the break room.",
    ),
    "ai": dummy_ai(hazard_category="electrical", incident_type="unsafe condition"),
}
check("different description, same time/place -> not a duplicate", lm.find_possible_duplicate(dup_record, dup_ai, [unrelated]) is None)

# --- [7] determine_final_status (the actual triage rules) ---

r = lm.determine_final_status(dummy_record(), {"not": "valid"}, [])
check("invalid ai output -> Manual Review", r["final_queue"] == lm.status_manual_review)

r = lm.determine_final_status(dummy_record(injury_reported=True), dummy_ai(), [])
check("reporter/ai contradiction -> Manual Review", r["final_queue"] == lm.status_manual_review)

r = lm.determine_final_status(dummy_record(), dummy_ai(severity="high", hazard_category="fire"), [])
check("high severity fire -> Immediate Action + escalation", r["final_queue"] == lm.status_immediate_action and r["escalation_required"])

r = lm.determine_final_status(dummy_record(), dummy_ai(severity="medium", indicators={"immediate_danger": True}), [])
check("immediate danger -> Priority Review", r["final_queue"] == lm.status_priority_review)

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
r = lm.determine_final_status(recurring_record, recurring_ai, [past_entry])
check("low severity + recent similar incident -> Recurring Review", r["final_queue"] == lm.status_recurring_review and r["recurring"])

r = lm.determine_final_status(dummy_record(), dummy_ai(), [])
check("nothing special -> Routine Log", r["final_queue"] == lm.status_routine_log)

"""duplicate_possible needs to be checked end-to-end too, not just via
find_possible_duplicate() directly in section [6] - this is what actually
reaches main.py's print_triage_summary()."""
r = lm.determine_final_status(dup_record, dup_ai, [dup_past])
check("near-duplicate incident sets duplicate_possible True", r["duplicate_possible"] is True)

r = lm.determine_final_status(dummy_record(), dummy_ai(), [])
check("no matching history sets duplicate_possible False", r["duplicate_possible"] is False)

# --- [8] route ---

"""route() is just a wrapper around determine_final_status that returns the queue name"""
check("route() returns the queue string", lm.route(dummy_record(), dummy_ai(), []) == lm.status_routine_log)

# --- [9] is_similar_incident ---

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
check(
    "same hazard, type, location and activity -> similar",
    lm.is_similar_incident(record, ai_out, past_entry["input"], matching_past_ai),
)

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
check(
    "different activity -> not similar",
    lm.is_similar_incident(record, ai_out, past_entry["input"], diff_activity_ai) is False,
)

# --- [10] score ---

check("low severity, no escalation hazard, no danger -> base score 1", lm.score(dummy_ai(severity="low")) == 1)
check("medium severity scores 2", lm.score(dummy_ai(severity="medium")) == 2)
check("high severity scores 3", lm.score(dummy_ai(severity="high")) == 3)
check(
    "fire hazard adds a point on top of severity",
    lm.score(dummy_ai(severity="low", hazard_category="fire")) == 2,
)
check(
    "injury/danger indicator adds a point on top of severity",
    lm.score(dummy_ai(severity="low", indicators={"injury": True})) == 2,
)
check(
    "fire hazard + injury both add up with high severity",
    lm.score(dummy_ai(severity="high", hazard_category="electrical", indicators={"injury": True})) == 5,
)
check("unrecognised severity scores a base of 0", lm.score(dummy_ai(severity="unknown")) == 0)

print("-" * 40)
print(f"{passed} passed, {failed} failed")

if failed:
    raise SystemExit(1)
