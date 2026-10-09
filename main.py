"""Main menu for the Workplace Incident Triage Assistant.

Integrates the four manager modules into one CLI application:

- io_manager    collects and validates the incident report from the user
- ai_manager    analyses the report with the AI and validates its reply
- logic_manager applies the escalation, recurrence and queue rules
- data_manager  persists the finished record and answers queries

Every menu action is wrapped so that one failure (AI outage, corrupt data
file, unexpected error) prints a friendly message and returns to the menu
instead of crashing the application.
"""

import data_manager
import logic_manager
import io_manager as io

# The AI stack needs the `openai` package. The menu still works without it
# (viewing and searching stored incidents), so import failures are deferred
# to the action that actually needs the AI.
try:
    import ai_manager
except ImportError as exc:
    ai_manager = None
    AI_IMPORT_ERROR = str(exc)

MENU_TITLE = "WORKPLACE INCIDENT TRIAGE ASSISTANT"


def print_menu() -> None:
    """Display the main menu options."""
    print("\n" + "=" * 60)
    print(MENU_TITLE)
    print("=" * 60)
    print("1. Report a new incident")
    print("2. View all stored incidents")
    print("3. Search incidents by location")
    print("4. Exit")


def print_stored_incident_summaries(summaries: list) -> None:
    """Print incident summaries produced by query_stored_incident_summaries.

    Args:
        summaries: list of summary dicts, each with description, date,
            location, hazard category, severity, final queue and escalation.
    """
    print("=" * 60)
    print("STORED INCIDENT SUMMARIES")
    print("=" * 60)
    if len(summaries) == 0:
        print("No data is saved yet.")
        print("-" * 60)
    else:
        for summary in summaries:
            print("Incident             : ", summary.get("description"))
            print("Date                 : ", summary.get("incident_date"))
            print("Location             : ", summary.get("location"))
            print("Hazard Category      : ", summary.get("hazard_category"))
            print("Severity             : ", summary.get("severity"))
            print("Final Queue          : ", summary.get("final_queue"))
            print("Escalation Required  : ", summary.get("escalation_required"))
            print("-" * 60)


def collect_incident_input() -> dict | None:
    """Collect one incident report through the I/O manager prompts.

    Returns:
        The validated input section for the shared record, or None when the
        user cancelled by typing 'quit' or interrupting the prompts.
    """
    try:
        description = io.prompt_description()
        if description == "quit":
            return None
        location = io.prompt_location()
        if location == "quit":
            return None
        reporter_role = io.prompt_reporter_role()
        if reporter_role == "quit":
            return None
        incident_datetime = io.prompt_incident_date_time()
        if incident_datetime == "quit":
            return None
        injury_reported = io.prompt_injury_reported()
        if injury_reported == "quit":
            return None
        immediate_action = io.prompt_immediate_action()
        if immediate_action == "quit":
            return None
    except (EOFError, KeyboardInterrupt):
        print("\nIncident report cancelled.")
        return None

    # prompt_incident_date_time returns a datetime object; the shared record
    # stores an ISO string so the logic rules and the data file agree.
    return {
        "description": description,
        "location": location,
        "reporter_role": reporter_role,
        "incident_datetime": incident_datetime.isoformat(timespec="seconds"),
        "injury_reported": injury_reported,
        "immediate_action": immediate_action,
    }


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


def analyse_incident(record: dict) -> dict:
    """Run the AI analysis for one record, with a manual-review fallback.

    Args:
        record: the shared record with the validated input section.

    Returns:
        The AI analysis dict, or a minimal stub when the AI failed so the
        logic manager routes the incident to Manual Review instead of
        silently dropping it.
    """
    if ai_manager is None:
        raise RuntimeError(
            f"the AI dependencies are unavailable ({AI_IMPORT_ERROR}); "
            "run 'pip install -r requirements.txt' first"
        )

    ok, ai_output = ai_manager.ai_manager(record)
    if ok:
        return to_severity_band(ai_output)

    print("\n[Warning] The AI analysis failed and this incident will be "
          "queued for manual review.")
    print(f"[Reason]  {ai_output}")
    return {
        "repeat_pattern_indicators": {
            "datetime": record["input"]["incident_datetime"]
        },
        "ai_error": ai_output,
    }


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


def report_new_incident() -> None:
    """Collect, analyse, triage and store one new incident report."""
    record_input = collect_incident_input()
    if record_input is None:
        print("Incident report cancelled - nothing was saved.")
        return

    record = {"record_id": "", "input": record_input}
    ai_output = analyse_incident(record)
    history = data_manager.load()
    logic_result = logic_manager.determine_final_status(
        record_input, ai_output, history
    )
    data_manager.save({"input": record_input, "ai": ai_output, "logic": logic_result})
    print_triage_summary(logic_result)


def view_stored_incidents() -> None:
    """Show a summary of every stored incident."""
    summaries = data_manager.query_stored_incident_summaries()
    print_stored_incident_summaries(summaries)


def search_by_location() -> None:
    """Show the incident summaries for one location."""
    location = input("Enter the location to search for: ").strip()
    if location == "":
        print("Location cannot be empty.")
        return
    summaries = [
        summary
        for summary in data_manager.query_stored_incident_summaries()
        if str(summary.get("location", "")).lower() == location.lower()
    ]
    print(f"\n{len(summaries)} incident(s) found for location '{location}'.")
    print_stored_incident_summaries(summaries)


def run_action(action) -> None:
    """Run one menu action, converting any failure into a friendly message.

    Args:
        action: a zero-argument callable.
    """
    try:
        action()
    except (EOFError, KeyboardInterrupt):
        print("\nAction cancelled - returning to the menu.")
    except Exception as exc:
        print(f"\n[Error] This action failed: {exc}")
        print("Returning to the main menu. Stored incidents are unaffected.")


def main() -> None:
    """Run the main menu loop until the user chooses to exit."""
    print(f"Welcome to the {MENU_TITLE.title()}.")
    print("A new database file is created automatically if none exists yet.")

    while True:
        print_menu()
        try:
            choice = input("Enter your choice (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return

        if choice == "1":
            run_action(report_new_incident)
        elif choice == "2":
            run_action(view_stored_incidents)
        elif choice == "3":
            run_action(search_by_location)
        elif choice == "4":
            print("Goodbye!")
            return
        else:
            print("Invalid choice. Please enter a number from 1 to 4.")


if __name__ == "__main__":
    main()
