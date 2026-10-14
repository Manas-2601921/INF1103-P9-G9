"""End-to-end test script: full pipeline without the AI manager.

Drives main_no_ai.report_new_incident() (a copy of main.py's flow with
the AI manager removed) through the real logic -> data chain: every case
states the full AI response it feeds the pipeline (the exact output the
working AI manager is assumed to produce), and every incident is
persisted to a temporary database so the real data/incidents.json is
never touched.

Every case is one literal dictionary in the CASES list:

    {
        "name": "what is being tested",
        "input": {                       # what goes into the pipeline
            "ai": {...},                 #   the complete AI response
            "ai_refuses": None,          #   or a failure reason string
            "report": {...},             #   overrides on DEFAULT_REPORT
            "history": [{...}],          #   seeded past incidents
        },
        "expected": {                    # what must come out of the pipeline
            "final_queue": "...", ...    #   keys mirror the stored record
        },
    }

The runner prints, for every key of "expected", the expected value next
to the actual value found in the stored record.

Fully offline (no API key, no network):

    .venv/bin/python test_end_to_end.py
"""

import io
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import data_manager as dm
import main_no_ai

passed = 0
failed = 0

INCIDENT_AT = datetime(2026, 10, 11, 9, 0)   # fixed incident time for every case

# ---------------------------------------------------------------------------
# default report (each case overrides only what it needs)
# ---------------------------------------------------------------------------

DEFAULT_REPORT = {
    "incident_name": "Forklift near-miss",
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "injury_reported": False,
    "immediate_action": "Supervisor stopped the forklift",
}

# ---------------------------------------------------------------------------
# the case table: each "input" carries the complete AI response
# ---------------------------------------------------------------------------

CASES = [
    # ---- [1] actual cases: realistic incidents, correct queues ----
    {
        "name": "low severity isolated incident",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Routine Log", "escalation_required": False,
                     "severity_band": "low", "severity_score": 0.2,
                     "record_id": "INC-0001"},
    },
    {
        "name": "medium severity isolated incident",
        "input": {
            "ai": {
                "severity": 0.55,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Routine Log", "escalation_required": False,
                     "severity_band": "medium", "severity_score": 0.55},
    },
    {
        "name": "high severity + fire hazard",
        "input": {
            "ai": {
                "severity": 0.9,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "fire",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "fire",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Immediate Action", "escalation_required": True,
                     "severity_band": "high", "severity_score": 0.9},
    },
    {
        "name": "high severity + electrical hazard",
        "input": {
            "ai": {
                "severity": 0.85,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "electrical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "electrical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Immediate Action", "escalation_required": True,
                     "severity_band": "high", "severity_score": 0.85},
    },
    {
        "name": "low severity but injury reported by the AI",
        "input": {
            "ai": {
                "severity": 0.3,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "injury",
                "indicators": {
                    "injury": True,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Priority Review", "escalation_required": False},
    },
    {
        "name": "low severity, similar incident 13 days ago",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "incident_datetime": "2026-09-28T09:00:00",
            }],
        },
        "expected": {"final_queue": "Recurring Review", "recurring": True},
    },
    {
        "name": "AI explanation and evidence carried into the saved decision",
        "input": {
            "ai": {
                "severity": 0.75,
                "confidence": 0.8,
                "severity_explanation": "Live wire exposed.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "exposed electrical cable",
            },
        },
        "expected": {"severity_band": "high", "severity_score": 0.75,
                     "ai_explanation": "Live wire exposed.",
                     "supporting_phrase": "exposed electrical cable"},
    },

    # ---- [2] deny cases: failures are quarantined, never dropped ----
    {
        "name": "AI gave up after 3 validation attempts",
        "input": {
            "ai_refuses": "AI output failed schema validation after 3 attempts:"
                          " severity out of range",
        },
        "expected": {"final_queue": "Manual Review",
                     "ai_error_contains": "AI output failed schema validation after 3 attempts",
                     "records_saved": 1},
    },
    {
        "name": "reporter reports an injury the AI missed (contradiction)",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "report": {"injury_reported": True},
        },
        "expected": {"final_queue": "Manual Review"},
    },
    {
        "name": "AI analysis missing required fields",
        "input": {
            "ai": {
                # severity, hazard_category, indicators and supporting_phrase
                # are deliberately missing from the AI response
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "incident_type": "near-miss",
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
            },
        },
        "expected": {"final_queue": "Manual Review"},
    },
    {
        "name": "AI analysis with unknown categories",
        "input": {
            "ai": {
                "severity": 0.5,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "volcano",
                "incident_type": "collision",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "volcano",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"final_queue": "Manual Review"},
    },

    # ---- [3] edge cases: boundaries and awkward data ----
    {
        "name": "banding boundary 0.39 -> low",
        "input": {
            "ai": {
                "severity": 0.39,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "low", "severity_score": 0.39},
    },
    {
        "name": "banding boundary 0.40 -> medium",
        "input": {
            "ai": {
                "severity": 0.40,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "medium", "severity_score": 0.40},
    },
    {
        "name": "banding boundary 0.70 -> medium",
        "input": {
            "ai": {
                "severity": 0.70,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "medium", "severity_score": 0.70},
    },
    {
        "name": "banding boundary 0.71 -> high",
        "input": {
            "ai": {
                "severity": 0.71,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "high", "severity_score": 0.71},
    },
    {
        "name": "banding boundary integer 1 -> high",
        "input": {
            "ai": {
                "severity": 1,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "high", "severity_score": 1},
    },
    {
        "name": "banding boundary 0.0 -> low",
        "input": {
            "ai": {
                "severity": 0.0,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
        },
        "expected": {"severity_band": "low", "severity_score": 0.0},
    },
    {
        "name": "similar incident exactly 30 days earlier is still recurring",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "incident_datetime": "2026-09-11T09:00:00",
            }],
        },
        "expected": {"final_queue": "Recurring Review", "recurring": True},
    },
    {
        "name": "similar incident 31 days earlier is not recurring",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "incident_datetime": "2026-09-10T09:00:00",
            }],
        },
        "expected": {"final_queue": "Routine Log", "recurring": False},
    },
    {
        "name": "same location and category but different activity is not recurring",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "activity": "welding",
            }],
        },
        "expected": {"final_queue": "Routine Log", "recurring": False},
    },
    {
        "name": "history with an unparseable date is skipped, not crashed on",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "incident_datetime": "not a date",
            }],
        },
        "expected": {"final_queue": "Routine Log", "recurring": False},
    },
    {
        "name": "near-identical resubmission flagged as possible duplicate, still saved",
        "input": {
            "ai": {
                "severity": 0.2,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "history": [{
                "incident_datetime": "2026-10-11T09:00:00",
                "description": "Forklift nearly hit a worker while reversing.!",
            }],
        },
        "expected": {"duplicate_possible": True, "records_saved": 2},
    },
    {
        "name": "very long description survives the round trip",
        "input": {
            "ai": {
                "severity": 0.45,
                "confidence": 0.8,
                "severity_explanation": "Sample explanation.",
                "hazard_category": "mechanical",
                "incident_type": "near-miss",
                "indicators": {
                    "injury": False,
                    "immediate_danger": False,
                    "exposure": True,
                    "equipment_involvement": False,
                    "work_stoppage": False,
                    "uncontrolled_hazard": False,
                },
                "repeat_pattern_indicators": {
                    "hazard_category": "mechanical",
                    "location": "Warehouse",
                    "datetime": "2026-10-11T09:00:00",
                    "activity": "forklift reversing",
                },
                "recommended_immediate_action": "Secure the area.",
                "supporting_phrase": "sample phrase",
            },
            "report": {
                "description": "Chemical vapour leak detected in the storage room. " * 12,
                "immediate_action": "No immediate action was taken",
            },
        },
        "expected": {"stored_description": "Chemical vapour leak detected in the storage room. " * 12},
    },
]


# ---------------------------------------------------------------------------
# history seeding (builds one stored past incident from a few overrides)
# ---------------------------------------------------------------------------

def build_history_entry(overrides):
    """Expand one history override dict into a stored-record-shaped entry."""
    entry = {
        "record_id": "INC-9001",
        "description": "Forklift nearly hit a worker while reversing.",
        "incident_datetime": "2026-09-28T09:00:00",
        "activity": "forklift reversing",
    }
    entry.update(overrides)
    return {
        "record_id": entry["record_id"],
        "input": {"description": entry["description"],
                  "location": DEFAULT_REPORT["location"],
                  "incident_datetime": entry["incident_datetime"]},
        "ai": {
            "severity": 0.5,
            "confidence": 0.8,
            "severity_explanation": "Sample explanation.",
            "hazard_category": "mechanical",
            "incident_type": "near-miss",
            "indicators": {
                "injury": False,
                "immediate_danger": False,
                "exposure": True,
                "equipment_involvement": False,
                "work_stoppage": False,
                "uncontrolled_hazard": False,
            },
            "repeat_pattern_indicators": {
                "hazard_category": "mechanical",
                "location": "Warehouse",
                "datetime": entry["incident_datetime"],
                "activity": entry["activity"],
            },
            "recommended_immediate_action": "Secure the area.",
            "supporting_phrase": "sample phrase",
        },
        "logic": {}, "metadata": {},
    }


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def run_pipeline(ai_reply, report):
    """Run one report_new_incident with the app's printing silenced so the
    per-case results stay readable. The terminal prompts are not involved:
    the report dictionary is injected directly."""
    record_input = dict(DEFAULT_REPORT, **report,
                        incident_datetime=INCIDENT_AT.isoformat(timespec="seconds"))

    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        main_no_ai.report_new_incident(record_input, ai_reply)
    finally:
        sys.stdout = saved_stdout


def actual_of(records):
    """Flatten the newest stored record into the keys a case can expect."""
    record = records[-1]
    logic, ai, inp = record["logic"], record["ai"], record["input"]
    return {
        "final_queue": logic.get("final_queue"),
        "escalation_required": logic.get("escalation_required"),
        "recurring": logic.get("recurring"),
        "duplicate_possible": logic.get("duplicate_possible"),
        "severity_band": ai.get("severity"),
        "severity_score": ai.get("severity_score"),
        "ai_error_contains": ai.get("ai_error"),
        "ai_explanation": logic.get("ai_explanation"),
        "supporting_phrase": logic.get("supporting_phrase"),
        "record_id": record.get("record_id"),
        "stored_description": inp.get("description"),
        "records_saved": len(records),
    }


def short(value):
    return value if not isinstance(value, str) or len(value) <= 42 else value[:39] + "..."


def run_case(case):
    """Run one case; print input, then expected vs actual for every key."""
    global passed, failed
    case_input, expected = case["input"], case["expected"]

    # fresh temp database per case, seeded with history when requested
    db = Path(tempfile.mkdtemp()) / "incidents.json"
    dm.incidents_file = db
    if case_input.get("history"):
        db.write_text(json.dumps([build_history_entry(h) for h in case_input["history"]],
                                 ensure_ascii=False), "utf-8")

    ai_reply = ((False, case_input["ai_refuses"]) if case_input.get("ai_refuses")
                else case_input["ai"])
    run_pipeline(ai_reply, case_input.get("report") or {})

    records = json.loads(db.read_text(encoding="utf-8")) if db.exists() else []
    actual = actual_of(records) if records else {}

    mismatches = []
    for key, want in expected.items():
        got = actual.get(key)
        ok = (want in got) if key == "ai_error_contains" and isinstance(got, str) else got == want
        if not ok:
            mismatches.append(key)

    if mismatches:
        failed += 1
        print(f"[FAIL] {case['name']}  (mismatched: {', '.join(mismatches)})")
    else:
        passed += 1
        print(f"[PASS] {case['name']}")
    if "ai" in case_input:
        print(f"    input    : ai={{'severity': {case_input['ai'].get('severity')!r}, ...}}")
    else:
        print(f"    input    : ai_manager refuses ({short(case_input.get('ai_refuses', ''))})")
    for key, want in expected.items():
        print(f"    {key:<20} expected={short(want)!r:<45} actual={short(actual.get(key))!r}")


def main():
    print("=" * 72)
    print("end-to-end tests (fake AI responses, offline)")
    print("=" * 72)
    for case in CASES:
        run_case(case)
    print("\n" + "=" * 72)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
