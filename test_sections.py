"""Test script for the dashboard section objects: declared key schemas,
excess-key dropping and blank/missing validation.

Fully offline — the sections are plain wrapper objects with no API, no
database and no Flask app involved.

Run with:

    .venv/Scripts/python test_sections.py
"""

from dashboard.ai_section import AISection
from dashboard.input_section import InputSection
from dashboard.logic_section import LogicSection
from dashboard.section_object import SectionObject

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
# Hardcoded sample manager dictionaries (the declared key schemas)
# ---------------------------------------------------------------------------

def make_input(**overrides):
    """Build a valid record input dictionary with selected keys overridden."""
    data = {
        "incident_name": "Forklift near miss",
        "description": "Forklift nearly hit a worker while reversing.",
        "location": "Warehouse",
        "reporter_role": "Employee",
        "incident_datetime": "22-01-2026 13:10",
        "injury_reported": False,
        "immediate_action": "Supervisor stopped the forklift",
    }
    data.update(overrides)
    return data


def make_ai(**overrides):
    """Build a valid record ai dictionary with selected keys overridden."""
    data = {
        "severity": "high",
        "confidence": 0.9,
        "severity_explanation": "A forklift nearly struck a worker.",
        "hazard_category": "mechanical",
        "incident_type": "near-miss",
        "indicators": {"injury": False, "immediate_danger": True},
        "repeat_pattern_indicators": {"datetime": "22-01-2026 13:10"},
        "recommended_immediate_action": "Barricade the reversing lane.",
        "supporting_phrase": "Forklift nearly hit a worker while reversing.",
        "severity_score": 0.75,
    }
    data.update(overrides)
    return data


def make_logic(**overrides):
    """Build a valid record logic dictionary with selected keys overridden."""
    data = {
        "final_queue": "Supervisor Review",
        "escalation_required": False,
        "recurring": False,
        "duplicate_possible": False,
        "risk_score": 0,
        "rule_applied": "default",
        "ai_explanation": "No escalation triggers matched.",
        "supporting_phrase": "No triggers matched.",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# [1] interface enforcement
# ---------------------------------------------------------------------------

def test_interface():
    print("\n--- [1] interface enforcement ---")
    try:
        SectionObject()
        check("the SectionObject ABC cannot be instantiated", False,
              "SectionObject() did not raise")
    except TypeError:
        check("the SectionObject ABC cannot be instantiated", True)

    for cls in (InputSection, AISection, LogicSection):
        section = cls.from_dict({"any": "dict"})
        check(f"{cls.__name__} satisfies the SectionObject interface",
              isinstance(section, SectionObject)
              and issubclass(cls, SectionObject)
              and callable(getattr(section, "to_dict", None))
              and callable(getattr(section, "validate", None)))


# ---------------------------------------------------------------------------
# [2] valid sections validate clean
# ---------------------------------------------------------------------------

def test_valid_sections():
    print("\n--- [2] valid sections validate clean ---")
    check("a complete InputSection validates clean",
          InputSection.from_dict(make_input()).validate() == [],
          f"got: {InputSection.from_dict(make_input()).validate()}")

    ai_section = AISection.from_dict(make_ai())
    check("a complete AISection validates clean",
          ai_section.validate() == [], f"got: {ai_section.validate()}")

    logic_section = LogicSection.from_dict(make_logic())
    check("a complete LogicSection validates clean "
          "(False and 0 are real values, not blanks)",
          logic_section.validate() == [], f"got: {logic_section.validate()}")


# ---------------------------------------------------------------------------
# [3] excess keys are dropped at creation
# ---------------------------------------------------------------------------

def test_excess_keys_dropped():
    print("\n--- [3] excess keys dropped at creation ---")
    noisy_input = dict(make_input(), weather="raining", witness_count=2)
    section = InputSection.from_dict(noisy_input)
    check("InputSection.from_dict keeps only the declared known keys",
          "weather" not in section.manager_json
          and "witness_count" not in section.manager_json
          and section.manager_json == make_input(),
          f"got: {section.manager_json}")
    check("the excess keys never reach to_dict",
          "weather" not in section.to_dict() and "witness_count" not in section.to_dict(),
          f"got: {section.to_dict()}")

    noisy_ai = dict(make_ai(), weather="raining")
    ai_section = AISection.from_dict(noisy_ai)
    check("AISection drops excess keys but keeps the optional severity_score",
          "weather" not in ai_section.manager_json
          and ai_section.manager_json.get("severity_score") == 0.75,
          f"got: {ai_section.manager_json}")
    check("excess keys still round-trip away: to_dict has only known keys",
          set(ai_section.to_dict()) <= set(AISection.KNOWN_KEYS),
          f"got: {set(ai_section.to_dict())}")


# ---------------------------------------------------------------------------
# [4] blank and missing required keys are reported by validate()
# ---------------------------------------------------------------------------

def test_blank_and_missing():
    print("\n--- [4] blank and missing required keys reported ---")
    partial = InputSection.from_dict(
        {k: v for k, v in make_input().items() if k != "description"})
    problems = partial.validate()
    check("a missing required key is reported with its name",
          len(problems) == 1 and "required key 'description'" in problems[0],
          f"got: {problems}")

    for value, label in (("", "empty string"), ("   ", "whitespace-only string"),
                         (None, "None value")):
        section = InputSection.from_dict(make_input(location=value))
        problems = section.validate()
        check(f"a {label} for a required key is reported",
              len(problems) == 1 and "required key 'location'" in problems[0],
              f"got: {problems}")

    section = AISection.from_dict(make_ai(indicators={}))
    problems = section.validate()
    check("an empty dictionary for a required key is reported",
          len(problems) == 1 and "required key 'indicators'" in problems[0],
          f"got: {problems}")

    empty = InputSection.from_dict(None)
    check("from_dict(None) still loads an empty section without raising",
          empty.manager_json == {} and len(empty.validate()) == 7,
          f"got: {empty.manager_json} / {empty.validate()}")


# ---------------------------------------------------------------------------
# [5] the manual-review stub is an alternative valid shape
# ---------------------------------------------------------------------------

def test_stub_shape():
    print("\n--- [5] manual-review stub tolerance ---")
    stub_data = {"repeat_pattern_indicators": {"datetime": "22-01-2026 13:10"},
                 "ai_error": "AI output failed schema validation after 3 attempts"}
    stub = AISection.from_dict(stub_data)
    check("the failure stub validates clean instead of the full schema",
          stub.validate() == [], f"got: {stub.validate()}")
    check("the stub serialises to exactly the keys it holds",
          stub.to_dict() == stub_data, f"got: {stub.to_dict()}")

    stub_with_blank = AISection.from_dict(
        {"repeat_pattern_indicators": {}, "ai_error": "failed"})
    check("a blank key inside the stub is still reported",
          len(stub_with_blank.validate()) == 1
          and "repeat_pattern_indicators" in stub_with_blank.validate()[0],
          f"got: {stub_with_blank.validate()}")

    direct = AISection(manager_json=dict(stub_data, weather="raining"))
    problems = direct.validate()
    check("excess keys built without from_dict are reported by validate()",
          len(problems) == 1 and "unexpected key(s): weather" in problems[0],
          f"got: {problems}")


# ---------------------------------------------------------------------------
# [6] copy semantics and round trips
# ---------------------------------------------------------------------------

def test_round_trips():
    print("\n--- [6] copy semantics and round trips ---")
    ai = make_ai()
    section = AISection.from_dict(ai)
    returned = section.to_dict()
    returned["severity"] = "low"
    returned["planted"] = True
    check("to_dict returns a copy; mutating it never changes the section",
          section.to_dict()["severity"] == "high" and "planted" not in section.to_dict(),
          f"got: {section.to_dict()}")

    check("from_dict(to_dict(x)) preserves the known dictionary exactly",
          AISection.from_dict(section.to_dict()).to_dict() == ai,
          f"got: {AISection.from_dict(section.to_dict()).to_dict()}")


def main():
    print("=" * 64)
    print("dashboard section object tests (offline)")
    print("=" * 64)

    test_interface()
    test_valid_sections()
    test_excess_keys_dropped()
    test_blank_and_missing()
    test_stub_shape()
    test_round_trips()

    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
