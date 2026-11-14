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

import managers
import io_manager as io
from IOManager import IOManager
from dashboard.incident import Incident
from dashboard.input_section import InputSection
from dashboard.ai_section import AISection
from dashboard.logic_section import LogicSection
from incident_analyzer import incident_analyzer
#import io_manager as io

analyse_incident = incident_analyzer.analyse_incident
to_severity_band = incident_analyzer.to_severity_band

MENU_TITLE = "WORKPLACE INCIDENT TRIAGE ASSISTANT"


def print_menu() -> None:
    """Display the main menu options."""
    print("\n" + "=" * 60)
    print(MENU_TITLE)
    print("=" * 60)
    print("1. Report a new incident")
    print("2. View all stored incidents")
    print("3. Search for incidents by different categories")
    print("4. Exit")


def print_stored_incident_summaries(summaries: list) -> None:
    """Print incident summaries produced by query_stored_incident_summaries.

    Args:
        summaries: list of summary dicts, each with description, date,
            location, hazard category, severity, final queue, escalation
            and risk score.
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
            print("Risk Score           : ", summary.get("risk_score"))
            print("-" * 60)


def collect_incident_input() -> dict | None:
    """Collect one incident report through the I/O manager prompts.

    Returns:
        The validated input section for the shared record, or None when the
        user cancelled by typing 'quit' or interrupting the prompts.
    """
    try:
        result_collect_incident_details = managers.io_manager.collect_incident_details()
        if not result_collect_incident_details:
            return None
    except (EOFError, KeyboardInterrupt):
        print("\nIncident report cancelled.")
        return None

    # prompt_incident_date_time returns a datetime object; the shared record
    # stores an ISO string so the logic rules and the data file agree.
    return {
        "incident_name": managers.io_manager.incident_name,
        "description": managers.io_manager.incident_description,
        "location": managers.io_manager.location,
        "reporter_role": managers.io_manager.reporter_role,
        "incident_datetime": managers.io_manager.incident_datetime.isoformat(timespec="seconds"),
        "injury_reported": managers.io_manager.injury_reported,
        "immediate_action": managers.io_manager.immediate_action,
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
    print("Risk Score           : ", logic_result.get("risk_score"))
    print("Rule Applied         : ", logic_result.get("rule_applied"))
    print("AI Explanation       : ", logic_result.get("ai_explanation"))
    print("Supporting Phrase    : ", logic_result.get("supporting_phrase"))


def confirm_save(final_queue: str) -> bool:
    """Ask the user to confirm saving the incident after previewing its
    triage queue. Treats blank/invalid input as 'yes' only for 'Y'/'YES'.

    Args:
        final_queue: the queue name produced by LogicManager.route().

    Returns:
        True if the user confirmed, False if they declined or cancelled.
    """
    print(f"\nThis incident would be routed to: {final_queue}")
    try:
        answer = input("Save this incident? Y/N: ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        print("\nSave cancelled.")
        return False
    return answer in ("Y", "YES")


def report_new_incident() -> None:
    """Collect, analyse, triage and store one new incident report."""
    incident = Incident()
    record_input = collect_incident_input()
    if record_input is None:
        print("Incident report cancelled - nothing was saved.")
        return

    incident.input_section = InputSection.from_dict(record_input)
    record = {"record_id": "", "input": record_input}
    ai_output = analyse_incident(record)
    incident.ai_section = AISection.from_dict(ai_output)
    history = [item.to_dict() for item in managers.data_manager.load()]

    previewed_queue = managers.logic_manager.route(record_input, ai_output, history)
    if not confirm_save(previewed_queue):
        print("Incident report cancelled - nothing was saved.")
        return

    logic_result = managers.logic_manager.determine_final_status(
        record_input, ai_output, history
    )
    incident.logic_section = LogicSection.from_dict(logic_result)
    managers.data_manager.save(incident)
    print_triage_summary(logic_result)


def view_stored_incidents() -> None:
    """Show a summary of every stored incident."""
    summaries = managers.data_manager.query_stored_incident_summaries()
    print_stored_incident_summaries(summaries)


def search_by_category(io:IOManager) -> None:
    #io = IOManager(None,None,None,None,None,None,None)
    """Show the incident summaries based on different categories"""
    while True:
        search_option = io.display_search_options()
        if search_option == "quit":
            break
        else:
            search_result = io.handle_search_option(search_option)
            if search_result == "quit":
                continue
            io.display_search_results(search_result[0], search_result[1])
    

    # search_options = io.handle_search_options()
    # if(search_options != False):
    #     io.display_search_results(search_options[0],search_options[1])


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
    print("SQLite storage must be initialized with: python -m flask --app app init-db")

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
            run_action(lambda:search_by_category(managers.io_manager))
        elif choice == "4":
            print("Goodbye!")
            return
        else:
            print("Invalid choice. Please enter a number from 1 to 4.")


if __name__ == "__main__":
    main()
