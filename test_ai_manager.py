"""Tests for ai_manager: AI JSON validation and reprompting verified
with valid, invalid and edge payloads.

By default the AI manager is driven with an injected TestLLMClient, so the
suite is fully offline (no API key, no network). Add --live to run the
payload cases against the real Z.ai API instead (requires ZAI_KEY in .env);
the reprompt cases are skipped live because the AI's replies cannot be
scripted. Each test builds its own fresh client and manager in ``setUp``,
so tests cannot leak queued replies or call counts into each other.

Run with:

    .venv/Scripts/python test_ai_manager.py [--live]
    python -m unittest test_ai_manager
"""

import json
import os
import sys
import unittest

from ai_manager import AIManager
from ai_modules.test_llm_client import TestLLMClient
from ai_modules.response_validator import ResponseValidator

LIVE = "--live" in sys.argv


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


class AIManagerTests(unittest.TestCase):
    """Exercise the AI manager's validation boundary, payload handling and
    reprompting loop through the real ``analyze`` contract."""

    def setUp(self):
        """Fresh collaborators per test: a scripted client replaces the Z.ai
        client offline (backoff_seconds 0 keeps the suite fast); the live
        mode still keeps a client so queued replies and call counts exist
        but are simply ignored by the real manager."""
        self.validator = ResponseValidator()
        self.client = TestLLMClient()
        if LIVE:
            self.manager = AIManager()
        else:
            self.manager = AIManager(client=self.client, backoff_seconds=0)

    def check(self, name, ok, detail=""):
        """Keep the check-style output; unittest records each verdict.

        ``subTest`` lets every check in a test method run and report even
        after an earlier one fails, like the old shared counters did.
        """
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"
              + (f"\n       {detail}" if not ok else ""))
        with self.subTest(name):
            self.assertTrue(ok, f"{name} — {detail}")

    def is_success(self, result):
        """True when the AI manager returned (True, parsed analysis dict)."""
        return (
            isinstance(result, tuple)
            and len(result) == 2
            and result[0] is True
            and isinstance(result[1], dict)
        )

    def is_error(self, result, *substrings):
        """True when the AI manager returned (None, message) containing the substrings."""
        return (
            isinstance(result, tuple)
            and len(result) == 2
            and result[0] is None
            and isinstance(result[1], str)
            and all(text in result[1] for text in substrings)
        )

    def queue_reply(self, *replies):
        """Queue the replies the test client returns and reset its call count."""
        self.client.queue(*replies)

    # ------------------------------------------------------------------
    # [1] AI reply json validation
    # ------------------------------------------------------------------

    def test_reply_validation(self):
        print("\n--- [1] AI reply json validation ---")
        parsed, problems = self.validator.validate(make_ai_reply())
        self.check("valid AI reply passes with no problems",
                   parsed != {} and problems == [], f"got: {problems}")

        parsed, problems = self.validator.validate("```json\n" + make_ai_reply() + "\n```")
        self.check("markdown fenced reply passes", problems == [], f"got: {problems}")

        parsed, problems = self.validator.validate(make_ai_reply(severity="high"))
        self.check("string severity is rejected as a type error",
                   any("must be a number" in p for p in problems), f"got: {problems}")

        parsed, problems = self.validator.validate(make_ai_reply(confidence=1.5))
        self.check("confidence above 1.0 is rejected as out of range",
                   any("between 0.0 and 1.0" in p for p in problems), f"got: {problems}")

        parsed, problems = self.validator.validate(
            make_ai_reply(hazard_category="volcano", incident_type="collision"))
        self.check("invalid hazard category and incident type are both reported",
                   any("hazard_category" in p for p in problems)
                   and any("incident_type" in p for p in problems), f"got: {problems}")

        broken = json.loads(make_ai_reply())
        del broken["supporting_phrase"]
        broken["indicators"]["injury"] = "yes"
        parsed, problems = self.validator.validate(json.dumps(broken))
        self.check("missing field and wrong-typed indicator are both reported",
                   any("missing required field 'supporting_phrase'" in p for p in problems)
                   and any("must be a boolean" in p for p in problems),
                   f"got: {problems}")

        for payload in ("sorry, no json here", "[1, 2, 3]", "", None):
            parsed, problems = self.validator.validate(payload)
            self.check(f"edge payload {payload!r} is rejected with a single parse error",
                       parsed == {} and len(problems) == 1, f"got: {problems}")

    # ------------------------------------------------------------------
    # [2] ai_manager with valid and edge payloads
    # ------------------------------------------------------------------

    def test_valid_payloads(self):
        print("\n--- [2] ai_manager with valid and edge payloads ---")
        self.queue_reply(make_ai_reply())
        result = self.manager.analyze(make_record())
        self.check("valid record returns the parsed analysis",
                   self.is_success(result) and (LIVE or result[1]["severity"] == 0.75),
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
            self.queue_reply(make_ai_reply())
            result = self.manager.analyze(make_record(overrides))
            self.check(f"edge payload: {name} is still analysed", self.is_success(result),
                       f"got: {result}")

    # ------------------------------------------------------------------
    # [3] ai_manager with invalid payloads (rejected before any AI call)
    # ------------------------------------------------------------------

    def test_invalid_payloads(self):
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
            self.queue_reply()
            result = self.manager.analyze(record)
            self.check(name, self.is_error(result, *substrings)
                       and (LIVE or self.client.calls == 0),
                       f"got: {result}")

    # ------------------------------------------------------------------
    # [4] reprompting on invalid AI replies (test client only)
    # ------------------------------------------------------------------

    @unittest.skipIf(LIVE, "AI replies cannot be scripted against the live API")
    def test_reprompting(self):
        print("\n--- [4] reprompting on invalid AI replies (test client only) ---")

        self.queue_reply(make_ai_reply(severity="high"), make_ai_reply())
        result = self.manager.analyze(make_record())
        retry_content = self.client.last_messages[1]["content"]
        self.check("invalid AI reply is reprompted with its violations, then succeeds",
                   self.is_success(result) and self.client.calls == 2
                   and "Your previous reply was rejected" in retry_content
                   and "must be a number" in retry_content,
                   f"got: {result} after {self.client.calls} call(s)")

        self.queue_reply("garbage", '{"severity": 0.5, "confidence": 2.0}', make_ai_reply())
        result = self.manager.analyze(make_record())
        self.check("valid reply on the final attempt still succeeds",
                   self.is_success(result) and self.client.calls == 3,
                   f"got: {result} after {self.client.calls} call(s)")

        self.queue_reply("garbage", "still garbage", '{"severity": "way too high"}')
        result = self.manager.analyze(make_record())
        self.check("persistent invalid AI replies fail after 3 attempts",
                   self.is_error(result, "after 3 attempts") and self.client.calls == 3,
                   f"got: {result} after {self.client.calls} call(s)")


if __name__ == "__main__":
    print("=" * 64)
    print(f"ai_manager tests ({'LIVE Z.ai API' if LIVE else 'test client, offline'})")
    print("=" * 64)
    if LIVE and not os.getenv("ZAI_KEY"):
        print("\nZAI_KEY is not set (add it to .env); cannot run the live tests")
        sys.exit(1)
    unittest.main(argv=[sys.argv[0]])
