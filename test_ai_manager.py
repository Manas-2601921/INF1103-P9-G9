"""Test script for ai_manager: valid inputs, invalid inputs and edge cases.

Default run stubs the AI connector, so no API key or network is needed:

    .venv/bin/python test_ai_manager.py

Add --live to run the AI-backed cases against the real Z.ai API
(requires ZAI_KEY in .env):

    .venv/bin/python test_ai_manager.py --live
"""

import json
import os
import sys
from unittest.mock import patch

from ai_modules import openai_connector

LIVE = "--live" in sys.argv

# A canned AI reply that passes validate_ai_output, returned by the stub
VALID_AI_REPLY = json.dumps({
    "severity": 0.75,
    "confidence": 0.9,
    "severity_explanation": "A forklift nearly struck a worker.",
    "hazard_category": "mechanical",
    "incident_type": "near-miss",
    "indicators": {
        "injury": False,
        "immediate_danger": True,
        "exposure": True,
        "equipment_involvement": True,
        "work_stoppage": True,
        "uncontrolled_hazard": False,
    },
    "repeat_pattern_indicators": {
        "hazard_category": "mechanical",
        "location": "Warehouse",
        "datetime": "22-01-2026 13:10",
        "activity": "forklift reversing",
    },
    "recommended_immediate_action": "Barricade the reversing lane.",
    "supporting_phrase": "Forklift nearly hit a worker while reversing.",
})

passed = 0
failed = 0
fake_state = {"replies": [], "calls": 0}


def fake_zai_connector(prompt):
    """Stub for zai_connector: hands back the next queued reply."""
    fake_state["calls"] += 1
    if fake_state["replies"]:
        return fake_state["replies"].pop(0)
    return "STUB ERROR: no canned AI reply was queued for this test case"


def queue_reply(*replies):
    """Queue the replies the stubbed connector returns and reset its call count."""
    fake_state["replies"] = list(replies)
    fake_state["calls"] = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}")
    else:
        failed += 1
        print(f"[FAIL] {name}\n       {detail}")


def is_success(result):
    """True when ai_manager returned (True, parsed analysis dict)."""
    return (
        isinstance(result, tuple)
        and len(result) == 2
        and result[0] is True
        and isinstance(result[1], dict)
    )


def is_error(result, *substrings):
    """True when ai_manager returned (None, message) containing the substrings."""
    return (
        isinstance(result, tuple)
        and len(result) == 2
        and result[0] is None
        and isinstance(result[1], str)
        and all(text in result[1] for text in substrings)
    )


BASE_INPUT = {
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "incident_datetime": "22-01-2026 13:10",
    "injury_reported": False,
    "immediate_action": "Supervisor stopped the forklift",
}


def make_record(input_overrides=None):
    """Build a valid record_json with selected input fields overridden."""
    return {"record_id": "T1", "input": dict(BASE_INPUT, **(input_overrides or {}))}


def test_valid_inputs(run):
    print("\n--- [1] valid inputs ---")
    queue_reply(VALID_AI_REPLY)
    result = run(make_record())
    ok = is_success(result) and (LIVE or result[1].get("severity") == 0.75)
    check("complete valid record returns the parsed analysis", ok, f"got: {result}")

    queue_reply(VALID_AI_REPLY)
    result = run(make_record({
        "description": "Worker slipped on wet floor near the loading bay.",
        "location": "Loading bay",
        "reporter_role": "Supervisor",
        "incident_datetime": "01-10-2026 08:45",
        "injury_reported": True,
        "immediate_action": "Area cordoned off and warning sign posted",
    }))
    check("second valid record returns the parsed analysis", is_success(result), f"got: {result}")


def test_invalid_inputs(run):
    print("\n--- [2] invalid inputs (rejected before any AI call) ---")
    cases = [
        ("record_json is a string", "this is not a record",
         ("record_json is not a dictionary",)),
        ("record_json is a list", [1, 2, 3],
         ("record_json is not a dictionary",)),
        ("record_json missing the input section", {"record_id": "T2"},
         ("input section is missing",)),
        ("input section is not a dictionary", {"record_id": "T3", "input": "oops"},
         ("incident_json is not a dictionary",)),
        ("input section completely empty", {"record_id": "T4", "input": {}},
         ("incident_json is missing",)),
        ("input section missing several required fields",
         {"record_id": "T5", "input": {"description": "Forklift nearly hit a worker."}},
         ("incident_json is missing", "location", "reporter_role")),
    ]
    for name, record, substrings in cases:
        queue_reply()
        result = run(record)
        ok = is_error(result, *substrings) and (LIVE or fake_state["calls"] == 0)
        check(name, ok, f"got: {result}")


def test_edge_inputs(run):
    print("\n--- [3] edge case inputs ---")
    cases = [
        ("empty description", {"description": ""}),
        ("whitespace only description", {"description": "   "}),
        ("None valued fields", {"immediate_action": None, "injury_reported": None}),
        ("extra unknown fields", {"weather": "raining", "witness_count": 2}),
        ("unicode and emoji in description",
         {"description": "铲车🚜 in the 厂房 nearly reversed into a worker ⚠️"}),
        ("very long description", {"description": "water leak on the floor. " * 200}),
    ]
    for name, overrides in cases:
        queue_reply(VALID_AI_REPLY)
        result = run(make_record(overrides))
        check(name, is_success(result), f"got: {result}")


def test_ai_output_edge_cases(run):
    """Only meaningful with the stubbed connector: scripted AI behaviour."""
    print("\n--- [4] AI output edge cases (stubbed connector only) ---")

    queue_reply("```json\n" + VALID_AI_REPLY + "\n```")
    result = run(make_record())
    check("markdown fenced AI reply is accepted", is_success(result), f"got: {result}")

    queue_reply("I analysed it and it seems pretty bad honestly.", VALID_AI_REPLY)
    result = run(make_record())
    check("invalid AI reply is rejected and reprompted, then succeeds",
          is_success(result) and fake_state["calls"] == 2,
          f"got: {result} after {fake_state['calls']} AI call(s)")

    queue_reply("garbage", '{"severity": 0.5, "confidence": 2.0}', VALID_AI_REPLY)
    result = run(make_record())
    check("valid reply on the final attempt still succeeds",
          is_success(result) and fake_state["calls"] == 3,
          f"got: {result} after {fake_state['calls']} AI call(s)")

    queue_reply("garbage", "still garbage", '{"severity": "way too high"}')
    result = run(make_record())
    check("persistent invalid AI replies fail after 3 attempts",
          is_error(result, "after 3 attempts") and fake_state["calls"] == 3,
          f"got: {result} after {fake_state['calls']} AI call(s)")


def main():
    print("=" * 64)
    print(f"ai_manager tests ({'LIVE Z.ai API' if LIVE else 'stubbed AI connector'})")
    print("=" * 64)

    if not LIVE:
        patch.object(openai_connector, "zai_connector", fake_zai_connector).start()

    import ai_manager

    if LIVE and not os.getenv("ZAI_KEY"):
        print("\nZAI_KEY is not set (add it to .env); cannot run the live tests")
        sys.exit(1)

    run = ai_manager.ai_manager
    test_valid_inputs(run)
    test_invalid_inputs(run)
    test_edge_inputs(run)
    if not LIVE:
        test_ai_output_edge_cases(run)

    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
