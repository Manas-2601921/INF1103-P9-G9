"""Test script for ai_manager: AI JSON validation and reprompting verified
with valid, invalid and edge payloads.

By default the AI manager is driven with an injected StubLLMClient, so the
script is fully offline (no API key, no network). Add --live to run the
payload cases against the real Z.ai API instead (requires ZAI_KEY in .env);
the reprompt section is skipped live because the AI's replies cannot be
scripted.

Run with:

    .venv/Scripts/python test_ai_manager.py
"""

import json
import os
import sys

from ai_manager import AIManager
from ai_modules.llm_client import StubLLMClient
from ai_modules.response_validator import ResponseValidator

LIVE = "--live" in sys.argv

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


def is_success(result):
    """True when the AI manager returned (True, parsed analysis dict)."""
    return (
        isinstance(result, tuple)
        and len(result) == 2
        and result[0] is True
        and isinstance(result[1], dict)
    )


def is_error(result, *substrings):
    """True when the AI manager returned (None, message) containing the substrings."""
    return (
        isinstance(result, tuple)
        and len(result) == 2
        and result[0] is None
        and isinstance(result[1], str)
        and all(text in result[1] for text in substrings)
    )


# ---------------------------------------------------------------------------
# Hardcoded sample AI reply and shared record (the schema contract)
# ---------------------------------------------------------------------------

def make_ai_reply(**overrides):
    """Build one hardcoded AI reply JSON string that passes validation."""
    reply = {
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
    }
    reply.update(overrides)
    return json.dumps(reply)


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


# ---------------------------------------------------------------------------
# Offline collaborators: a scripted stub client replaces the Z.ai client
# (scripted replies, counted calls, last prompt kept)
# ---------------------------------------------------------------------------

stub = StubLLMClient()
validator = ResponseValidator()


def queue_reply(*replies):
    """Queue the replies the stub client returns and reset its call count."""
    stub.queue(*replies)


def make_manager():
    """Build the AIManager under test: stubbed offline, real Z.ai live."""
    if LIVE:
        return AIManager()
    # backoff_seconds 0 disables the retry waits so the suite stays fast
    return AIManager(client=stub, backoff_seconds=0)


# ---------------------------------------------------------------------------
# [1] AI reply json validation
# ---------------------------------------------------------------------------

def test_reply_validation():
    print("\n--- [1] AI reply json validation ---")
    parsed, problems = validator.validate(make_ai_reply())
    check("valid AI reply passes with no problems",
          parsed != {} and problems == [], f"got: {problems}")

    parsed, problems = validator.validate("```json\n" + make_ai_reply() + "\n```")
    check("markdown fenced reply passes", problems == [], f"got: {problems}")

    parsed, problems = validator.validate(make_ai_reply(severity="high"))
    check("string severity is rejected as a type error",
          any("must be a number" in p for p in problems), f"got: {problems}")

    parsed, problems = validator.validate(make_ai_reply(confidence=1.5))
    check("confidence above 1.0 is rejected as out of range",
          any("between 0.0 and 1.0" in p for p in problems), f"got: {problems}")

    parsed, problems = validator.validate(
        make_ai_reply(hazard_category="volcano", incident_type="collision"))
    check("invalid hazard category and incident type are both reported",
          any("hazard_category" in p for p in problems)
          and any("incident_type" in p for p in problems), f"got: {problems}")

    broken = json.loads(make_ai_reply())
    del broken["supporting_phrase"]
    broken["indicators"]["injury"] = "yes"
    parsed, problems = validator.validate(json.dumps(broken))
    check("missing field and wrong-typed indicator are both reported",
          any("missing required field 'supporting_phrase'" in p for p in problems)
          and any("must be a boolean" in p for p in problems),
          f"got: {problems}")

    for payload in ("sorry, no json here", "[1, 2, 3]", "", None):
        parsed, problems = validator.validate(payload)
        check(f"edge payload {payload!r} is rejected with a single parse error",
              parsed == {} and len(problems) == 1, f"got: {problems}")


# ---------------------------------------------------------------------------
# [2] ai_manager with valid and edge payloads
# ---------------------------------------------------------------------------

def test_valid_payloads(run):
    print("\n--- [2] ai_manager with valid and edge payloads ---")
    queue_reply(make_ai_reply())
    result = run(make_record())
    check("valid record returns the parsed analysis",
          is_success(result) and (LIVE or result[1]["severity"] == 0.75),
          f"got: {result}")

    edge_cases = [
        ("empty description", {"description": ""}),
        ("whitespace only description", {"description": "   "}),
        ("None valued fields", {"immediate_action": None, "injury_reported": None}),
        ("extra unknown fields", {"weather": "raining", "witness_count": 2}),
        ("long mixed-case description",
         {"description": "Forklift nearly reversed into a Worker while the "
                         "supervisor was shouting warnings."}),
        ("very long description", {"description": "water leak on the floor. " * 200}),
    ]
    for name, overrides in edge_cases:
        queue_reply(make_ai_reply())
        result = run(make_record(overrides))
        check(f"edge payload: {name} is still analysed", is_success(result),
              f"got: {result}")


# ---------------------------------------------------------------------------
# [3] ai_manager with invalid payloads (rejected before any AI call)
# ---------------------------------------------------------------------------

def test_invalid_payloads(run):
    print("\n--- [3] ai_manager with invalid payloads ---")
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
        check(name, is_error(result, *substrings) and (LIVE or stub.calls == 0),
              f"got: {result}")


# ---------------------------------------------------------------------------
# [4] reprompting on invalid AI replies (stubbed client only)
# ---------------------------------------------------------------------------

def test_reprompting(run):
    print("\n--- [4] reprompting on invalid AI replies (stubbed client only) ---")

    queue_reply(make_ai_reply(severity="high"), make_ai_reply())
    result = run(make_record())
    retry_content = stub.last_messages[1]["content"]
    check("invalid AI reply is reprompted with its violations, then succeeds",
          is_success(result) and stub.calls == 2
          and "Your previous reply was rejected" in retry_content
          and "must be a number" in retry_content,
          f"got: {result} after {stub.calls} call(s)")

    queue_reply("garbage", '{"severity": 0.5, "confidence": 2.0}', make_ai_reply())
    result = run(make_record())
    check("valid reply on the final attempt still succeeds",
          is_success(result) and stub.calls == 3,
          f"got: {result} after {stub.calls} call(s)")

    queue_reply("garbage", "still garbage", '{"severity": "way too high"}')
    result = run(make_record())
    check("persistent invalid AI replies fail after 3 attempts",
          is_error(result, "after 3 attempts") and stub.calls == 3,
          f"got: {result} after {stub.calls} call(s)")


def main():
    print("=" * 64)
    print(f"ai_manager tests ({'LIVE Z.ai API' if LIVE else 'stubbed LLM client, offline'})")
    print("=" * 64)

    run = make_manager().analyze

    if LIVE and not os.getenv("ZAI_KEY"):
        print("\nZAI_KEY is not set (add it to .env); cannot run the live tests")
        sys.exit(1)

    test_reply_validation()
    test_valid_payloads(run)
    test_invalid_payloads(run)
    if not LIVE:
        test_reprompting(run)

    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
