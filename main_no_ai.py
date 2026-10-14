"""Test double of main.py with the AI manager removed.

Copied from main.py so the end-to-end tests can drive the real
logic -> data pipeline without the AI layer: analyse_incident takes the
AI result as a parameter (exactly the (True, analysis) / (False, reason)
pair ai_manager.ai_manager would return) instead of calling ai_manager,
and report_new_incident takes the already-collected input section
instead of prompting the terminal.

Removed compared to main.py:
- the ai_manager import and the API-call failure handling
- collect_incident_input and the interactive menu (the tests inject the
  report dictionary and read the stored database directly)

Keep this file in sync with main.py: if main.py changes its flow
(severity banding, the failure stub, the record handed to
data_manager.save), update the matching function here.
"""

import data_manager
import logic_manager


def to_severity_band(ai_output: dict) -> dict:
    """Map the AI's numeric 0.0-1.0 severity score onto the low/medium/high
    bands the logic manager's business rules use.

    The original score is kept under severity_score so no information is
    lost.

    Args:
        ai_output: the validated analysis dict returned by ai_manager.

    Returns:
        The same dict with severity replaced by its band.
    """
    severity = ai_output.get("severity")
    if isinstance(severity, (int, float)) and not isinstance(severity, bool):
        ai_output["severity_score"] = severity
        if severity > 0.7:
            ai_output["severity"] = "high"
        elif severity >= 0.4:
            ai_output["severity"] = "medium"
        else:
            ai_output["severity"] = "low"
    return ai_output


def analyse_incident(record_input: dict, ai_result) -> dict:
    """Handle the AI result for one record, with a manual-review fallback.

    Args:
        record_input: the validated input section of the shared record.
        ai_result: what the AI manager produced - the validated analysis
            dict on success, or (False, reason) when it gave up after its
            attempts.

    Returns:
        The AI analysis dict, or a minimal stub when the AI failed so the
        logic manager routes the incident to Manual Review instead of
        silently dropping it.
    """
    if isinstance(ai_result, tuple):
        print("\n[Warning] The AI analysis failed and this incident will be "
              "queued for manual review.")
        print(f"[Reason]  {ai_result[1]}")
        return {
            "repeat_pattern_indicators": {
                "datetime": record_input["incident_datetime"]
            },
            "ai_error": ai_result[1],
        }
    return to_severity_band(ai_result)


def print_triage_summary(logic_result: dict) -> None:
    """Show the final triage decision for a newly saved incident.

    Args:
        logic_result: the decision dict returned by determine_final_status.
    """
    print("\n" + "-" * 60)
    print("TRIAGE DECISION (saved to the incident log)")
    print("-" * 60)
    print("Final Queue          : ", logic_result.get("final_queue"))
    print("Escalation Required  : ", logic_result.get("escalation_required"))
    print("Recurring            : ", logic_result.get("recurring"))
    print("Possible Duplicate   : ", logic_result.get("duplicate_possible"))
    print("Rule Applied         : ", logic_result.get("rule_applied"))
    print("AI Explanation       : ", logic_result.get("ai_explanation"))
    print("Supporting Phrase    : ", logic_result.get("supporting_phrase"))


def report_new_incident(record_input: dict, ai_result) -> dict:
    """Triage and store one new incident report.

    Args:
        record_input: the validated input section of the shared record.
        ai_result: the AI result to process (dict, or (False, reason)).

    Returns:
        The logic decision stored with the record.
    """
    ai_output = analyse_incident(record_input, ai_result)
    history = data_manager.load()
    logic_result = logic_manager.determine_final_status(
        record_input, ai_output, history
    )
    data_manager.save({"input": record_input, "ai": ai_output, "logic": logic_result})
    print_triage_summary(logic_result)
    return logic_result
