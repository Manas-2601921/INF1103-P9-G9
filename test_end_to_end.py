"""End-to-end test script: full pipeline without the AI manager.

Drives main_app.report_new_incident() through the real io->logic->data chain
with the terminal prompts and the AI manager stubbed: fake AI sample
responses feed the logic manager, and every incident is persisted to a
temporary database so the real data/incidents.json is never touched.

Covers three groups:
  [1] actual cases  - realistic incidents routed to the right queues
  [2] deny cases    - AI failures and contradictions land in Manual Review
  [3] edge cases    - band boundaries, the 30-day window boundary,
                      duplicates, unicode, unparseable history, first run

Fully offline (no API key, no network):

    .venv/bin/python test_end_to_end.py
"""

import contextlib
import io as io_stream
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import data_manager as dm
import main as main_app  # aliased: this file defines its own main()

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
# Fake AI sample responses (the shape ai_manager returns on success)
# ---------------------------------------------------------------------------

def make_ai_response(severity=0.5, hazard_category="mechanical",
                     incident_type="near-miss", indicators=None, pattern=None,
                     explanation="Sample explanation.",
                     supporting_phrase="sample phrase"):
    """Build one fake validated AI analysis with selected fields overridden."""
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
            "datetime": "2026-10-11T09:00:00",
            "activity": "forklift reversing",
        }, **(pattern or {})),
        "recommended_immediate_action": "Secure the area.",
        "supporting_phrase": supporting_phrase,
    }


REPORT = {
    "incident_name": "Forklift near-miss",
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "injury_reported": False,
    "immediate_action": "Supervisor stopped the forklift",
}


def run_report(ai_response, report_overrides=None, history_entries=None):
    """Run one full report_new_incident with stubs; return (records, printed).

    ai_response: the fake AI analysis dict, or (False, reason) to simulate
        the AI manager giving up after its 3 attempts.
    history_entries: stored-record dicts written to the temp database first.
    """
    report = dict(REPORT, **(report_overrides or {}))
    tmp_dir = tempfile.mkdtemp()
    dm.incidents_file = Path(tmp_dir) / "incidents.json"

    for entry in history_entries or []:
        with open(dm.incidents_file, "a", encoding="utf-8") as f:
            f.write(json.dumps([entry], ensure_ascii=False))

    def fake_ai_manager(record):
        return (True, ai_response) if not isinstance(ai_response, tuple) else ai_response

    printed = io_stream.StringIO()
    with contextlib.redirect_stdout(printed), \
            patch.object(main_app.ai_manager, "ai_manager", fake_ai_manager), \
            patch.object(main_app.io, "prompt_incident_name",
                         lambda: report["incident_name"]), \
            patch.object(main_app.io, "prompt_description",
                         lambda: report["description"]), \
            patch.object(main_app.io, "prompt_location", lambda: report["location"]), \
            patch.object(main_app.io, "prompt_reporter_role",
                         lambda: report["reporter_role"]), \
            patch.object(main_app.io, "prompt_incident_date_time",
                         lambda: datetime(2026, 10, 11, 9, 0)), \
            patch.object(main_app.io, "prompt_injury_reported",
                         lambda: report["injury_reported"]), \
            patch.object(main_app.io, "prompt_immediate_action",
                         lambda: report["immediate_action"]):
        main_app.report_new_incident()

    records = []
    if dm.incidents_file.exists():
        records = json.loads(dm.incidents_file.read_text(encoding="utf-8"))
    return records, printed.getvalue()


def history_entry(description="Forklift nearly hit a worker while reversing.",
                  location="Warehouse", incident_datetime="2026-09-28T09:00:00",
                  hazard_category="mechanical", activity="forklift reversing",
                  incident_type="near-miss", record_id="INC-9001"):
    """Build one stored history record for seeding the temp database."""
    return {
        "record_id": record_id,
        "input": {"description": description, "location": location,
                  "incident_datetime": incident_datetime},
        "ai": make_ai_response(pattern={
            "hazard_category": hazard_category, "location": location,
            "datetime": incident_datetime, "activity": activity},
            incident_type=incident_type),
        "logic": {}, "metadata": {},
    }


def last_decision(records):
    """Return the logic section of the most recently stored record."""
    return records[-1]["logic"]


# ---------------------------------------------------------------------------
# [1] actual cases
# ---------------------------------------------------------------------------

def test_actual_cases():
    print("\n--- [1] actual cases ---")

    records, printed = run_report(make_ai_response(severity=0.2))
    d = last_decision(records)
    check("low severity isolated incident is a Routine Log",
          d["final_queue"] == "Routine Log" and not d["escalation_required"],
          f"got: {d}")

    records, printed = run_report(make_ai_response(severity=0.55))
    d = last_decision(records)
    check("medium severity isolated incident is a Routine Log",
          d["final_queue"] == "Routine Log", f"got: {d}")

    for hazard in ("fire", "electrical"):
        records, printed = run_report(make_ai_response(severity=0.9,
                                                       hazard_category=hazard))
        d = last_decision(records)
        check(f"high severity + {hazard} hazard routes to Immediate Action with escalation",
              d["final_queue"] == "Immediate Action" and d["escalation_required"],
              f"got: {d}")

    records, printed = run_report(make_ai_response(
        severity=0.3, incident_type="injury", indicators={"injury": True}))
    d = last_decision(records)
    check("low severity with reported injury is overridden to Priority Review",
          d["final_queue"] == "Priority Review" and not d["escalation_required"],
          f"got: {d}")

    records, printed = run_report(
        make_ai_response(severity=0.2),
        history_entries=[history_entry()])
    d = last_decision(records)
    check("low severity with a similar incident in the last 30 days is Recurring Review",
          d["final_queue"] == "Recurring Review" and d["recurring"],
          f"got: {d}")

    record = records[-1]
    check("stored record carries the full lineage (input, ai, logic, metadata)",
          all(k in record for k in ("record_id", "input", "ai", "logic", "metadata"))
          and record["input"]["incident_datetime"] == "2026-10-11T09:00:00",
          f"got: {sorted(record)}")

    records2, _ = run_report(make_ai_response(severity=0.2))
    check("record ids increment across saves in one database",
          records2[0]["record_id"].endswith("0001")
          and int(records2[-1]["record_id"].split("-")[1])
          == int(records2[0]["record_id"].split("-")[1]) + len(records2) - 1,
          f"got: {[r['record_id'] for r in records2]}")


# ---------------------------------------------------------------------------
# [2] deny cases
# ---------------------------------------------------------------------------

def test_deny_cases():
    print("\n--- [2] deny cases ---")

    reason = ("AI output failed schema validation after 3 attempts: "
              "['severity must be between 0.0 and 1.0, got 9.5 instead']")
    records, printed = run_report((False, reason))
    record, d = records[-1], last_decision(records)
    check("AI giving up after 3 attempts stores the report in Manual Review with the reason",
          d["final_queue"] == "Manual Review"
          and record["ai"].get("ai_error") == reason
          and "queued for manual review" in printed,
          f"got: {d}, ai_error={record['ai'].get('ai_error')}")

    check("the failed-AI record keeps the reporter input intact",
          record["input"]["description"] == REPORT["description"]
          and record["input"]["location"] == REPORT["location"],
          f"got: {record['input']}")

    records, printed = run_report(
        make_ai_response(severity=0.2),
        report_overrides={"injury_reported": True})
    d = last_decision(records)
    check("reporter reports an injury the AI missed -> Manual Review (contradiction)",
          d["final_queue"] == "Manual Review"
          and "contradictory" in d["rule_applied"].lower(),
          f"got: {d}")

    broken = make_ai_response()
    for field in ("severity", "hazard_category", "indicators", "supporting_phrase"):
        broken.pop(field, None)
    records, printed = run_report(broken)
    d = last_decision(records)
    check("AI analysis missing required fields is quarantined in Manual Review",
          d["final_queue"] == "Manual Review"
          and "invalid AI output" in d["rule_applied"],
          f"got: {d}")

    records, printed = run_report(
        make_ai_response(hazard_category="volcano", incident_type="collision"))
    d = last_decision(records)
    check("AI analysis with unknown categories is quarantined in Manual Review",
          d["final_queue"] == "Manual Review"
          and "invalid hazard_category" in d["rule_applied"],
          f"got: {d}")


# ---------------------------------------------------------------------------
# [3] edge cases
# ---------------------------------------------------------------------------

def test_edge_cases():
    print("\n--- [3] edge cases ---")

    bands = {"0.39 -> low": (0.39, "low"), "0.40 -> medium": (0.40, "medium"),
             "0.70 -> medium": (0.70, "medium"), "0.71 -> high": (0.71, "high"),
             "integer 1 -> high": (1, "high"), "0.0 -> low": (0.0, "low")}
    for name, (score, expected) in bands.items():
        records, _ = run_report(make_ai_response(severity=score))
        record = records[-1]
        check(f"severity banding boundary {name}",
              record["ai"]["severity"] == expected
              and record["ai"]["severity_score"] == score,
              f"got: {record['ai'].get('severity')} / {record['ai'].get('severity_score')}")

    records, _ = run_report(
        make_ai_response(severity=0.2),
        history_entries=[history_entry(incident_datetime="2026-09-11T09:00:00")])
    check("similar incident exactly 30 days earlier is still inside the window",
          last_decision(records)["final_queue"] == "Recurring Review",
          f"got: {last_decision(records)}")

    records, _ = run_report(
        make_ai_response(severity=0.2),
        history_entries=[history_entry(incident_datetime="2026-09-10T09:00:00")])
    check("similar incident 31 days earlier is outside the window (Routine Log)",
          last_decision(records)["final_queue"] == "Routine Log",
          f"got: {last_decision(records)}")

    records, _ = run_report(
        make_ai_response(severity=0.2),
        history_entries=[history_entry(activity="welding")])
    check("same category and location but different activity is not recurring",
          last_decision(records)["final_queue"] == "Routine Log",
          f"got: {last_decision(records)}")

    records, _ = run_report(
        make_ai_response(severity=0.2),
        history_entries=[history_entry(incident_datetime="not a date")])
    check("history with an unparseable date is skipped without crashing",
          last_decision(records)["final_queue"] == "Routine Log",
          f"got: {last_decision(records)}")

    dup = history_entry(incident_datetime="2026-10-11T09:00:00",
                        description=REPORT["description"] + "!")
    records, _ = run_report(make_ai_response(severity=0.2,
                                             pattern={"datetime": "2026-10-11T09:00:00"}),
                            history_entries=[dup])
    d = last_decision(records)
    check("near-identical resubmission is flagged as a possible duplicate but still saved",
          d["duplicate_possible"] and len(records) == 2,
          f"got: {d}, stored {len(records)} records")

    weird = "铲车🚜 in the 厂房 nearly reversed into a worker ⚠️ " + "leak. " * 60
    records, _ = run_report(make_ai_response(severity=0.45),
                            report_overrides={"description": weird,
                                              "immediate_action": "No immediate action was taken"})
    record = records[-1]
    check("unicode, emoji and a very long description survive the round trip",
          record["input"]["description"] == weird
          and record["input"]["immediate_action"] == "No immediate action was taken",
          f"got: {record['input']['description'][:40]}...")

    records, _ = run_report(make_ai_response(severity=0.75,
                                             explanation="Live wire exposed.",
                                             supporting_phrase="exposed electrical cable"))
    record = records[-1]
    check("AI explanation and supporting phrase are carried into the saved decision",
          record["logic"]["ai_explanation"] == "Live wire exposed."
          and record["logic"]["supporting_phrase"] == "exposed electrical cable",
          f"got: {record['logic']}")


def main():
    print("=" * 64)
    print("end-to-end tests (fake AI responses, offline)")
    print("=" * 64)
    test_actual_cases()
    test_deny_cases()
    test_edge_cases()
    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
