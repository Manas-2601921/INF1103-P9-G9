"""End-to-end test script: full pipeline without the AI manager.

Drives main_app.report_new_incident() through the real io->logic->data chain
with the terminal prompts and the AI manager stubbed: fake AI sample
responses feed the logic manager, and every incident is persisted to a
temporary database so the real data/incidents.json is never touched.

Every case is one row in the CASES table: the input (fake AI response,
optional report overrides, optional seeded history) and the expected
output (queue, flags, stored fields). The runner prints the input, the
expected output and the actual output for every case, so each row reads
as input -> expected -> got.

Fully offline (no API key, no network):

    .venv/bin/python test_end_to_end.py
"""

import contextlib
import io as io_stream
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import data_manager as dm
import main as main_app  # aliased: this file defines its own main()

passed = 0
failed = 0

INCIDENT_AT = datetime(2026, 10, 11, 9, 0)   # fixed incident time for every case
AI_REFUSED = "AI output failed schema validation after 3 attempts"

REPORT = {
    "incident_name": "Forklift near-miss",
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "injury_reported": False,
    "immediate_action": "Supervisor stopped the forklift",
}


# ---------------------------------------------------------------------------
# input builders
# ---------------------------------------------------------------------------

def make_ai_response(severity=0.5, hazard_category="mechanical",
                     incident_type="near-miss", indicators=None,
                     datetime_str="2026-10-11T09:00:00",
                     activity="forklift reversing", drop=(),
                     explanation="Sample explanation.",
                     supporting_phrase="sample phrase"):
    """Build one fake validated AI analysis with selected fields overridden."""
    reply = {
        "severity": severity,
        "confidence": 0.8,
        "severity_explanation": explanation,
        "hazard_category": hazard_category,
        "incident_type": incident_type,
        "indicators": dict({
            "injury": False, "immediate_danger": False, "exposure": True,
            "equipment_involvement": False, "work_stoppage": False,
            "uncontrolled_hazard": False,
        }, **(indicators or {})),
        "repeat_pattern_indicators": {
            "hazard_category": hazard_category,
            "location": REPORT["location"],
            "datetime": datetime_str,
            "activity": activity,
        },
        "recommended_immediate_action": "Secure the area.",
        "supporting_phrase": supporting_phrase,
    }
    for field in drop:
        reply.pop(field, None)
    return reply


def history_entry(description="Forklift nearly hit a worker while reversing.",
                  incident_datetime="2026-09-28T09:00:00",
                  activity="forklift reversing", record_id="INC-9001"):
    """Build one stored history record for seeding the temp database."""
    return {
        "record_id": record_id,
        "input": {"description": description, "location": REPORT["location"],
                  "incident_datetime": incident_datetime},
        "ai": make_ai_response(activity=activity, datetime_str=incident_datetime),
        "logic": {}, "metadata": {},
    }


def case(name, ai=None, ai_fails_with=None, report=None, history=(), **expect):
    """Declare one case: inputs on the left, expected outputs in **expect."""
    return {"name": name, "ai": ai, "ai_error": ai_fails_with,
            "report": report or {}, "history": list(history), "expect": expect}


# ---------------------------------------------------------------------------
# the case table: input -> expected output
# ---------------------------------------------------------------------------

CASES = [
    # ---- [1] actual cases: realistic incidents, correct queues ----
    case("low severity isolated incident",
         ai=dict(severity=0.2),
         queue="Routine Log", escalation=False, band="low", score=0.2,
         record_id="INC-0001"),
    case("medium severity isolated incident",
         ai=dict(severity=0.55),
         queue="Routine Log", escalation=False, band="medium", score=0.55),
    case("high severity + fire hazard",
         ai=dict(severity=0.9, hazard_category="fire"),
         queue="Immediate Action", escalation=True, band="high", score=0.9),
    case("high severity + electrical hazard",
         ai=dict(severity=0.85, hazard_category="electrical"),
         queue="Immediate Action", escalation=True, band="high", score=0.85),
    case("low severity but injury reported by the AI",
         ai=dict(severity=0.3, incident_type="injury",
                 indicators={"injury": True}),
         queue="Priority Review", escalation=False),
    case("low severity, similar incident 13 days ago",
         ai=dict(severity=0.2),
         history=[dict(incident_datetime="2026-09-28T09:00:00")],
         queue="Recurring Review", recurring=True),
    case("AI explanation and evidence carried into the saved decision",
         ai=dict(severity=0.75, explanation="Live wire exposed.",
                 supporting_phrase="exposed electrical cable"),
         band="high", score=0.75,
         ai_explanation="Live wire exposed.",
         supporting_phrase="exposed electrical cable"),

    # ---- [2] deny cases: failures are quarantined, never dropped ----
    case("AI gave up after 3 validation attempts",
         ai_fails_with=AI_REFUSED + ": severity out of range",
         queue="Manual Review", ai_error=AI_REFUSED, saved_records=1),
    case("reporter reports an injury the AI missed (contradiction)",
         ai=dict(severity=0.2),
         report={"injury_reported": True},
         queue="Manual Review"),
    case("AI analysis missing required fields",
         ai=dict(severity=0.4, drop=("severity", "hazard_category",
                                     "indicators", "supporting_phrase")),
         queue="Manual Review"),
    case("AI analysis with unknown categories",
         ai=dict(hazard_category="volcano", incident_type="collision"),
         queue="Manual Review"),

    # ---- [3] edge cases: boundaries and awkward data ----
    case("banding boundary 0.39 -> low",    ai=dict(severity=0.39), band="low",    score=0.39),
    case("banding boundary 0.40 -> medium", ai=dict(severity=0.40), band="medium", score=0.40),
    case("banding boundary 0.70 -> medium", ai=dict(severity=0.70), band="medium", score=0.70),
    case("banding boundary 0.71 -> high",   ai=dict(severity=0.71), band="high",   score=0.71),
    case("banding boundary integer 1 -> high", ai=dict(severity=1), band="high",   score=1),
    case("banding boundary 0.0 -> low",     ai=dict(severity=0.0), band="low",     score=0.0),
    case("similar incident exactly 30 days earlier is still recurring",
         ai=dict(severity=0.2),
         history=[dict(incident_datetime="2026-09-11T09:00:00")],
         queue="Recurring Review", recurring=True),
    case("similar incident 31 days earlier is not recurring",
         ai=dict(severity=0.2),
         history=[dict(incident_datetime="2026-09-10T09:00:00")],
         queue="Routine Log", recurring=False),
    case("same location and category but different activity is not recurring",
         ai=dict(severity=0.2),
         history=[dict(activity="welding")],
         queue="Routine Log", recurring=False),
    case("history with an unparseable date is skipped, not crashed on",
         ai=dict(severity=0.2),
         history=[dict(incident_datetime="not a date")],
         queue="Routine Log", recurring=False),
    case("near-identical resubmission flagged as possible duplicate, still saved",
         ai=dict(severity=0.2),
         history=[dict(incident_datetime="2026-10-11T09:00:00",
                       description=REPORT["description"] + "!")],
         duplicate=True, saved_records=2),
    case("unicode, emoji and a very long description survive the round trip",
         ai=dict(severity=0.45),
         report={"description": "铲车🚜 in the 厂房 nearly hit a worker ⚠️ " + "leak. " * 60,
                 "immediate_action": "No immediate action was taken"},
         description="铲车🚜 in the 厂房 nearly hit a worker ⚠️ " + "leak. " * 60),
]


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def run_pipeline(ai_reply, report):
    """Run one report_new_incident with stubs against dm.incidents_file."""
    answers = dict(REPORT, **report)

    def fake_ai_manager(record):
        return (True, ai_reply) if not isinstance(ai_reply, tuple) else ai_reply

    with contextlib.redirect_stdout(io_stream.StringIO()), \
            patch.object(main_app.ai_manager, "ai_manager", fake_ai_manager), \
            patch.multiple(main_app.io,
                           prompt_incident_name=lambda: answers["incident_name"],
                           prompt_description=lambda: answers["description"],
                           prompt_location=lambda: answers["location"],
                           prompt_reporter_role=lambda: answers["reporter_role"],
                           prompt_incident_date_time=lambda: INCIDENT_AT,
                           prompt_injury_reported=lambda: answers["injury_reported"],
                           prompt_immediate_action=lambda: answers["immediate_action"]):
        main_app.report_new_incident()


def actual_of(records):
    """Flatten the newest stored record into the keys a case can expect."""
    record = records[-1]
    logic, ai, inp = record["logic"], record["ai"], record["input"]
    return {
        "queue": logic.get("final_queue"),
        "escalation": logic.get("escalation_required"),
        "recurring": logic.get("recurring"),
        "duplicate": logic.get("duplicate_possible"),
        "band": ai.get("severity"),
        "score": ai.get("severity_score"),
        "ai_error": ai.get("ai_error"),
        "ai_explanation": logic.get("ai_explanation"),
        "supporting_phrase": logic.get("supporting_phrase"),
        "record_id": record.get("record_id"),
        "description": inp.get("description"),
        "saved_records": len(records),
    }


def describe_input(one_case):
    """One readable line summarising what the case feeds the pipeline."""
    parts = []
    if one_case["ai"] is not None:
        parts.append("ai(" + ", ".join(f"{k}={v!r}" for k, v in one_case["ai"].items()) + ")")
    if one_case["ai_error"]:
        parts.append(f"ai_manager -> (False, {one_case['ai_error']!r})")
    if one_case["report"]:
        parts.append("report(" + ", ".join(one_case["report"]) + " changed)")
    if one_case["history"]:
        parts.append("history=[" + ", ".join(
            h.get("incident_datetime", h.get("activity", "default")) for h in one_case["history"]) + "]")
    return "; ".join(parts) if parts else "defaults only"


def short(value):
    return value if not isinstance(value, str) or len(value) <= 48 else value[:45] + "..."


def run_case(one_case):
    """Run one case; print input, expected vs actual; return True on match."""
    global passed, failed
    expect = one_case["expect"]

    # fresh temp database per case, optionally seeded with history
    db = Path(tempfile.mkdtemp()) / "incidents.json"
    dm.incidents_file = db
    if one_case["history"]:
        db.write_text(json.dumps([history_entry(**h) for h in one_case["history"]],
                                 ensure_ascii=False), "utf-8")

    ai_reply = ((False, one_case["ai_error"]) if one_case["ai_error"]
                else make_ai_response(**(one_case["ai"] or {})))
    run_pipeline(ai_reply, one_case["report"])

    records = json.loads(db.read_text(encoding="utf-8")) if db.exists() else []
    actual = actual_of(records) if records else {}

    mismatches = [
        (key, want, actual.get(key))
        for key, want in expect.items()
        if not ((want in actual.get(key)) if key == "ai_error" and isinstance(actual.get(key), str)
                else actual.get(key) == want)
    ]

    if mismatches:
        failed += 1
        print(f"[FAIL] {one_case['name']}")
    else:
        passed += 1
        print(f"[PASS] {one_case['name']}")
    print(f"      in : {short(describe_input(one_case))}")
    print(f"      exp: " + str({k: short(v) for k, v in expect.items()}))
    print(f"      got: " + str({k: short(actual.get(k)) for k in expect}))
    return not mismatches


def main():
    print("=" * 72)
    print("end-to-end tests (fake AI responses, offline)")
    print("=" * 72)
    for one_case in CASES:
        run_case(one_case)
    print("\n" + "=" * 72)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
