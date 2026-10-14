from datetime import datetime

import data_manager

# {
#   "record_id": "",
#   "input": {
#     "description": "Forklift nearly hit a worker while reversing.",
#     "location": "Warehouse",
#     "reporter_role": "Employee",
#     "incident_date": "2026-09-21",
#     "injury_reported": false,
#     "immediate_action": "Supervisor stopped the forklift"
#   }                                                                           record template

# Input incident information methods

def prompt_description():

    while True:
        newIncidentDescription = input("Enter the description of the incident (or type 'quit' to exit): ")
        if newIncidentDescription.lower() == 'quit':
            return "quit"
        if not newIncidentDescription.strip():
            print("Description cannot be empty. Please describe what happened.")
            continue
        return newIncidentDescription

def prompt_location():
    while True:
        newIncidentLocation = input(f"Enter the location of the incident (or type 'quit' to exit): " + "\nFor example: Warehouse, Office, Factory, etc.")

        if newIncidentLocation.lower() == 'quit':
            return "quit"
        if not newIncidentLocation.strip():
            print("Location cannot be empty. Please enter where the incident happened.")
            continue
        return newIncidentLocation

# Accepted answers for the role prompt: option number or role name (any case)
ROLE_OPTIONS = {
    "1": "Employee", "employee": "Employee",
    "2": "Supervisor", "supervisor": "Supervisor",
    "3": "Manager", "manager": "Manager",
    "4": "Client", "client": "Client",
}

def prompt_reporter_role():

    print("\nSelect your role in the company:")
    print("  1. Employee")
    print("  2. Supervisor")
    print("  3. Manager")
    print("  4. Client")

    while True:
        answer = input("Enter the option number or role name (or type 'quit' to exit): ").strip()

        if answer.lower() == 'quit':
            return "quit"

        role = ROLE_OPTIONS.get(answer.lower())
        if role:
            return role

        print("Invalid input. Please enter a valid role.")
    

def prompt_incident_date_time():
    while True:
        newIncidentDateTime = input("Enter the date and time of the incident (DD-MM-YYYY HH:MM) (or type 'quit' to exit):")
        if newIncidentDateTime.lower() == 'quit':
            return "quit"
        elif newIncidentDateTime is None:
            print("Invalid input. Please enter a valid incident date and time.")
            continue
        else:
            try:
                newIncidentDateTime = datetime.strptime(newIncidentDateTime, "%d-%m-%Y %H:%M")
                return newIncidentDateTime
            except ValueError:
                print("Invalid date and time format. Please enter the date and time in the format DD-MM-YYYY HH:MM.")
                continue

def prompt_injury_reported():
    while True:
        newIncidentInjuryReported = input("Was there any injury reported Y/N (or type 'quit' to exit): ")
        if newIncidentInjuryReported.lower() == 'quit':
            return "quit"
        elif newIncidentInjuryReported.upper() == 'Y' or newIncidentInjuryReported.upper() == 'YES':
            newIncidentInjuryReported = True
            return newIncidentInjuryReported
        elif newIncidentInjuryReported.upper() == 'N' or newIncidentInjuryReported.upper() == 'NO':
            newIncidentInjuryReported = False
            return newIncidentInjuryReported
        else:
            print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
            continue
    return

def prompt_immediate_action():
    while True:
        immediateAction = input("Was there any immediate action taken Y/N (or type 'quit' to exit): ")
        if immediateAction.lower() == 'quit':
            return "quit"
        elif immediateAction.upper() == 'Y' or immediateAction.upper() == 'YES':
            while True:
                newImmediateAction = input("Please describe the immediate action taken: ")
                if newImmediateAction.strip():
                    return newImmediateAction
                print("Description cannot be empty. Please describe the action taken.")
        elif immediateAction.upper() == 'N' or immediateAction.upper() == 'NO':
            immediateAction = "No immediate action was taken"
            return immediateAction
        else:
            print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
            continue

def prompt_incident_name():
    while True:
        newIncidentName = input("Enter the name of the incident (or type 'quit' to exit): ")
        if newIncidentName.lower() == 'quit':
            return "quit"
        if not newIncidentName.strip():
            print("Incident name cannot be empty. Please give the incident a short title.")
            continue
        return newIncidentName

#Output Incident Information methods

#function to look up one incident record by its id and print a formatted incident review report to the console
def generate_incident_review(incident_id):
    """
    variables in the function:
    incident_id - the unique id of the incident to look up (compared against each record's "record_id")
    matching_records - the list of records whose record_id matches the incident id (empty if none match)
    incident_record - the record found for that incident (a nested dictionary with "input", "ai", "logic" and "metadata" sections)
    report_created_at - the time the record was created, as a datetime object
    report_processed_at - the time the record finished processing, as a datetime object
    processing_seconds - the number of seconds between creation and processing, as a whole-number string
    report_create_date - the creation date formatted like "05 March 2025"
    report_create_time - the creation time formatted like "14:30"
    LABEL_WIDTH - the number of characters each label is padded to, so the values line up in a column
    indicator - one risk indicator name at a time while looping through the AI's indicators
 
    this method prints the report and returns nothing when it succeeds.
    If the incident id is empty or no record is found, it prints an error message and returns False
    """
    # stop early if no incident id was given
    if(incident_id == ""):
        print("Error: Incident id is missing")
        return False
    # search all records and keep every one whose record_id matches the incident id (the list is empty if none match)
    matching_records = data_manager.query(lambda record: record.get("record_id", {}) == incident_id)
    # stop early if nothing matched, before trying to take the first item (taking [0] of an empty list would crash)
    if len(matching_records) == 0:
        print("Error: No such record exists in our records.")
        return False
    # at least one match exists, so it is now safe to take the first one
    incident_record = matching_records[0]
 
    #processing information
    # convert the ISO timestamp strings into datetime objects so they can be formatted and subtracted
    report_created_at =  datetime.fromisoformat(incident_record["metadata"]["created_at"])
    report_processed_at = datetime.fromisoformat(incident_record["metadata"]["processed_at"])
 
    # subtract the two datetimes to get the time taken, convert it to total seconds, then format it as a whole number string
    processing_seconds = f"{(report_processed_at - report_created_at).total_seconds():.0f}"
 
    # format the creation timestamp as a date, e.g. "05 March 2025"
    report_create_date = report_created_at.strftime("%d %B %Y")
    # format the same timestamp as just the hour and minute, e.g. "14:30"
    report_create_time = report_created_at.strftime("%H:%M")

    formatted_datetime = datetime.fromisoformat(incident_record['input']['incident_datetime']).strftime("%d %B %Y, %H:%M")
 
    # width that every label is padded to in the sections below
    LABEL_WIDTH = 24
 
    # report header
    print("="*20)
    print("Incident Report")
    print("="*20,"\n")
 
    # section 1: the details the person originally submitted
    # ('<{LABEL_WIDTH}' left-aligns each label in a fixed-width space so the values start in the same column)
    print("Incident details")
    print("-"*20)
    print(f"{'Incident Name:':<{LABEL_WIDTH}}{incident_record['input']['incident_name']}")
    print(f"{'Incident Description:':<{LABEL_WIDTH}}{incident_record['input']['description']}")
    print(f"{'Incident DateTime:':<{LABEL_WIDTH}}{formatted_datetime}")
    print(f"{'Incident Location:':<{LABEL_WIDTH}}{incident_record['input']['location']}")
    # converts the True/False value into "Yes"/"No" for readability
    print(f"{'Injury Reported:':<{LABEL_WIDTH}}{'Yes' if incident_record['input']['injury_reported'] else 'No'}")
    print(f"{'Immediate Action:':<{LABEL_WIDTH}}{incident_record['input']['immediate_action']}")
 
    # section 2: what the AI concluded about the incident, plus which review queue it ended up in
    print("\nOur Assessment")
    print("-"*20)
    print(f"{'Severity':<{LABEL_WIDTH}}{incident_record['ai']['severity']}")
    print(f"{'Incident Type':<{LABEL_WIDTH}}{incident_record['ai']['incident_type']}")
    print(f"{'Explanation':<{LABEL_WIDTH}}{incident_record['ai']['severity_explanation']}")
    print(f"{'Review Status':<{LABEL_WIDTH}}{incident_record['logic']['final_queue']}")
 
    # section 3: only the risk indicators the AI flagged as True
    print("\nRisk Indicators")
    print("-"*20)
    # loop through the names of all the indicators (the dictionary's keys)
    for indicator in incident_record['ai']['indicators']:
        # look up this indicator's value and only continue if it is True
        if(incident_record['ai']['indicators'][indicator] == True):
            # make names readable, e.g. "fire_hazard" becomes "fire hazard"
            if("_" in indicator):
                indicator = indicator.replace("_"," ")
            print(indicator)
 
    # section 4: the AI's suggested next step
    print("\nRecommended Immediate Action")
    print("-"*20)
    # ">" is used as the marker instead of "▶" because "▶" cannot be printed on a default Windows console (UnicodeEncodeError)
    print(f"> {incident_record['ai']['recommended_immediate_action']}")

#function to ask the user how they want to search incidents (title, category or date/time), validate what they type, run the search and return the matching records
QUIT_MESSAGE = "Search cancelled. Returning to the previous menu."
DATETIME_PROMPT_HINT = "(e.g. DD-MM-YYYY HH:MM, 25-10-2023 14:30)"


def ask_choice(prompt, valid_options):
    """Re-asks until the user enters one of valid_options. Returns the choice, or None if the user typed 'quit'."""
    while True:
        answer = input(prompt).strip()
        if answer.lower() == "quit":
            return None
        if answer in valid_options:
            return answer
        print(f"Invalid option. Please enter one of: {', '.join(valid_options)} (or type 'quit' to exit).")


def ask_text(prompt, error_message):
    """Re-asks until the user enters non-empty text. Returns the text, or None if the user typed 'quit'."""
    while True:
        user_text_input = input(prompt).strip()
        if user_text_input.lower() == "quit":
            return None
        if user_text_input:
            return user_text_input
        print(error_message)


def ask_datetime(prompt):
    """
    Re-asks until the user enters a datetime as DD-MM-YYYY HH:MM.
    Returns (iso_string, typed_text), or None if the user typed 'quit'.
    """
    while True:
        user_datetime_input = input(prompt).strip()
        if user_datetime_input.lower() == "quit":
            return None
        try:
            iso_value = datetime.strptime(user_datetime_input, "%d-%m-%Y %H:%M").isoformat(timespec="seconds")
            return iso_value, user_datetime_input
        except ValueError:
            print("Invalid format. Please follow the format: DD-MM-YYYY HH:MM (e.g., 25-10-2023 14:30)")


def handle_search_options():
    """
    Asks the user how they want to search incidents (title, category or date/time), re-prompting
    until every answer is valid, runs the search and returns the matching records.

    Returns a tuple of (search_results, description of what was searched for) when a search runs
    (search_results is an empty list if nothing matched).
    If the user types 'quit' at any prompt, prints a message and returns False.
    """
    # main menu
    search_option = ask_choice(
        "What would you like to search by:\n1. Title \n2. Category\n3. Date \n\n"
        "Enter your option number here (or type 'quit' to exit): ",
        ("1", "2", "3"),
    )
    if search_option is None:
        print(QUIT_MESSAGE)
        return False

    # option 1: search by incident title
    if search_option == "1":
        title_search_value = ask_text(
            "\nEnter the name of the incident you want to search for (or type 'quit' to exit): ",
            "Name of the incident is empty. Please enter a name.",
        )
        if title_search_value is None:
            print(QUIT_MESSAGE)
            return False
        search_results = data_manager.query(
            lambda record: (record.get("input", {}).get("incident_name") or "").strip().lower() == title_search_value.lower()
        )
        return search_results, title_search_value

    # option 2: search by incident category
    if search_option == "2":
        incident_categories = sorted({
            (record.get("ai", {}).get("hazard_category") or "").strip()
            for record in data_manager.query(lambda record: True)
            if (record.get("ai", {}).get("hazard_category") or "").strip()
        })

        if incident_categories:
            print("\nCategories related to all your incidents:")
            for incident_category in incident_categories:
                print(f"  - {incident_category}")
        else:
            print("No categories found.")
            return False
        while True:
            category_search_value = ask_text(
                "\nEnter the category of the incident you want to search for (or type 'quit' to exit): ",
                "Category of the incident is empty. Please enter a category.",
            )
            if category_search_value is None:
                print(QUIT_MESSAGE)
                return False
            search_results = data_manager.query(
                lambda record: (record.get("ai", {}).get("hazard_category") or "").strip().lower() == category_search_value.lower()
            )
            if len(search_results) == 0:
                print(f"Error: Invalid category input. Please re-enter a valid category.")
                continue
            else:
                break
        return search_results, category_search_value

    # option 3: search by date and time, which opens a second menu
    datetime_search_type = ask_choice(
        "\nSearch incident datetime by \n1. Date and Time Range\n2. Specific Datetime\n"
        "Enter your option number here (or type 'quit' to exit): ",
        ("1", "2"),
    )
    if datetime_search_type is None:
        print(QUIT_MESSAGE)
        return False

    # sub-option 1: search between a start and an end datetime
    if datetime_search_type == "1":
        start = ask_datetime(f"\nEnter the start datetime you want to search by {DATETIME_PROMPT_HINT} (or type 'quit' to exit): ")
        if start is None:
            print(QUIT_MESSAGE)
            return False
        valid_start_datetime, search_start_datetime_input = start

        # re-ask for the end datetime until it is valid AND not earlier than the start
        while True:
            end = ask_datetime(f"Enter the end datetime you want to search by {DATETIME_PROMPT_HINT} (or type 'quit' to exit): ")
            if end is None:
                print(QUIT_MESSAGE)
                return False
            valid_end_datetime, search_end_datetime_input = end
            # ISO strings sort in time order, so they can be compared directly
            if valid_start_datetime > valid_end_datetime:
                print("End datetime cannot be earlier than the start datetime. Please try again.")
                continue
            break

        # "or ''" treats a missing incident_datetime as an empty string, so that record is skipped instead of crashing
        search_results = data_manager.query(
            lambda record: valid_start_datetime <= (record.get("input", {}).get("incident_datetime") or "") <= valid_end_datetime
        )
        search_string = f"incidents between {search_start_datetime_input} and {search_end_datetime_input}"
        return search_results, search_string

    # sub-option 2: search for one exact datetime
    exact = ask_datetime(f"\nEnter the datetime you want to search by {DATETIME_PROMPT_HINT} (or type 'quit' to exit): ")
    if exact is None:
        print(QUIT_MESSAGE)
        return False
    valid_search_datetime, search_datetime_input = exact
    search_results = data_manager.query(
        lambda record: record.get("input", {}).get("incident_datetime") == valid_search_datetime
    )
    return search_results, search_datetime_input
            
#function to display a numbered list of search results, ask the user to pick one, and then show that incident's full review report
def display_search_results(search_results_data, user_search_query):
    """
    Prints a numbered list of search results, asks the user to pick one, and shows that incident's
    full review report. Every record in search_results_data must contain a "record_id".

    Returns False if there are no results or the user types 'quit'. Returns nothing after showing a report.
    """
    num_of_search_results = len(search_results_data)
    if num_of_search_results == 0:
        print(f"No Search Results for '{user_search_query}'")
        return False

    print(f"\n{num_of_search_results} incident(s) for '{user_search_query}':\n")
    for i, data in enumerate(search_results_data, start=1):
        formatted_datetime = datetime.fromisoformat(data['input']['incident_datetime']).strftime("%d %B %Y, %H:%M")
        print(f"[{i}] {data['input']['incident_name']}")
        print(f"{'Incident Date and Time':<22}: {formatted_datetime}")
        print(f"{'Location':<22}: {data['input']['location']}")
        print("-" * 47, "\n")

    # keep asking until the user enters a valid result number, or types 'quit'
    while True:
        search_result_input = input(
            "Enter the search result number to view incident details (or type 'quit' to exit): "
        ).strip()

        if search_result_input.lower() == "quit":
            print("Search cancelled. Returning to the previous menu.")
            return False

        try:
            view_incident_number = int(search_result_input)
        except ValueError:
            print("Error: invalid search result number. Please enter a whole number (or type 'quit' to exit).")
            continue

        if view_incident_number < 1 or view_incident_number > num_of_search_results:
            print(f"Error: please enter a number number thats shown in the search results (or type 'quit' to exit).")
            continue

        break

    # view_incident_data_id = search_results_data[view_incident_number - 1]['record_id']

    # print("\n")
    # generate_incident_review(view_incident_data_id)
    