import json
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
        elif newIncidentDescription is None:
            print("Invalid input. Please enter a valid incident description.")
            continue
        return newIncidentDescription
    return

def prompt_location():
    while True:
        newIncidentLocation = input(f"Enter the location of the incident (or type 'quit' to exit): " + "\nFor example: Warehouse, Office, Factory, etc.")

        if newIncidentLocation.lower() == 'quit':
            return "quit"
        elif newIncidentLocation is None:
            print("Invalid input. Please enter a valid incident location.")
            continue
        return newIncidentLocation
    return

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
            newImmediateAction = input("Please describe the immediate action taken: ")
            return newImmediateAction
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
        elif newIncidentName is None:
            print("Invalid input. Please enter a valid incident description.")
            continue
        return newIncidentName
    return

#Output Incident Information methods 
def load_file(file_path, file_permission):
    '''
    This is a method to load files with error handling in place. 

    Refer to the method fields below to understand what the method requires to execute successfully:
    filePath = the path leading to the file storing data
    filePermission = r/w/r+ : how the user wants the file to be loaded.
    
    '''
    try:
        with open(file_path,file_permission, encoding="utf-8")as filehandler:
                    records = json.load(filehandler)
    except FileNotFoundError:
        # print("Data file is not found")
        return "Error: File is not found"
    except json.JSONDecodeError:
        # print("invalid json error")
        return "Error: Invalid JSON error"
    else:
        return records

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
    if incident_id == "":
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

    input_section = incident_record.get("input")
    ai_section = incident_record.get("ai")
    logic_section = incident_record.get("logic")
    metadata_section = incident_record.get("metadata")
    if (
        not isinstance(input_section, dict)
        or not isinstance(ai_section, dict)
        or not isinstance(logic_section, dict)
        or not isinstance(metadata_section, dict)
    ):
        print("Error: The incident record is missing required sections.")
        return False

    try:
        report_created_at = datetime.fromisoformat(metadata_section["created_at"])
        report_processed_at = datetime.fromisoformat(metadata_section["processed_at"])
    except (KeyError, TypeError, ValueError):
        print("Error: The incident record metadata is missing or invalid.")
        return False

    incident_date_time = datetime.fromisoformat(
        incident_record["input"]["incident_datetime"]
    )
    processing_seconds = f"{(report_processed_at - report_created_at).total_seconds():.0f}"

    # format the creation timestamp as a date, e.g. "05 March 2025"
    report_create_date = report_created_at.strftime("%d %B %Y")
    # format the same timestamp as just the hour and minute, e.g. "14:30"
    report_create_time = report_created_at.strftime("%H:%M")
 
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
    print(f"{'Incident Name:':<{LABEL_WIDTH}}{incident_record['input'].get('incident_name', 'Unknown')}")
    print(f"{'Incident Description:':<{LABEL_WIDTH}}{incident_record['input'].get('description', 'No description provided.')}")
    print(f"{'Incident Location:':<{LABEL_WIDTH}}{incident_record['input'].get('location', 'Unknown')}")
    print(f"{'Incident Date and Time:':<{LABEL_WIDTH}}{incident_date_time.strftime('%d %B %Y, %H:%M')}")
    # converts the True/False value into "Yes"/"No" for readability
    print(f"{'Injury Reported:':<{LABEL_WIDTH}}{'Yes' if incident_record['input'].get('injury_reported') else 'No'}")
    print(f"{'Immediate Action:':<{LABEL_WIDTH}}{incident_record['input'].get('immediate_action', 'No immediate action reported.')}")
 
    # section 2: what the AI concluded about the incident, plus which review queue it ended up in
    print("\nOur Assesment")
    print("-"*20)
    print(f"{'Severity':<{LABEL_WIDTH}}{incident_record['ai'].get('severity', 'Not assessed')}")
    print(f"{'Incident Type':<{LABEL_WIDTH}}{incident_record['ai'].get('incident_type', 'Unknown')}")
    print(f"{'Explanation':<{LABEL_WIDTH}}{incident_record['ai'].get('severity_explanation', 'No explanation available.')}")
    print(f"{'Review Status':<{LABEL_WIDTH}}{incident_record['logic'].get('final_queue', 'Not assigned')}")
 
    # section 3: only the risk indicators the AI flagged as True
    print("\nRisk Indicators")
    print("-"*20)
    # loop through the names of all the indicators (the dictionary's keys)
    indicators = ai_section.get("indicators", {})
    if isinstance(indicators, dict):
        for indicator in indicators:
            # look up this indicator's value and only continue if it is True
            if indicators.get(indicator) is True:
                # make names readable, e.g. "fire_hazard" becomes "fire hazard"
                if("_" in indicator):
                    indicator = indicator.replace("_"," ")
                print(indicator)
 
    # section 4: the AI's suggested next step
    print("\nRecommended Immediate Action")
    print("-"*20)
    # ">" is used as the marker instead of "▶" because "▶" cannot be printed on a default Windows console (UnicodeEncodeError)
    print(f"> {incident_record['ai'].get('recommended_immediate_action', 'No recommended action available.')}")

#function to ask the user how they want to search incidents (title, category or date/time), validate what they type, run the search and return the matching records
def handle_search_options():
    """
    variables in the function:
    search_results - the records returned by data_manager.query() for the chosen search
    user_search_option - the raw text the user typed for the main menu (1 = Title, 2 = Category, 3 = Date)
    int_search_option - user_search_option converted to an integer
    title_search_value - the incident name the user wants to search for
    category_search_value - the incident category the user wants to search for
    datetime_search_type - the raw text the user typed for the date sub-menu (1 = range, 2 = specific datetime)
    datetime_search_type_int - datetime_search_type converted to an integer
    search_start_datetime_input - the start datetime exactly as the user typed it, e.g. "2023-10-25 14:30"
    valid_start_datetime - the start datetime converted to an ISO string, e.g. "2023-10-25T14:30:00"
    search_end_datetime_input - the end datetime exactly as the user typed it
    valid_end_datetime - the end datetime converted to an ISO string
    search_string - a readable description of the date range search, returned for display with the results
    search_datetime_input - the single datetime exactly as the user typed it
    valid_search_datetime - the single datetime converted to an ISO string

    This method returns (search_results, search_description) when a search runs.
    Invalid answers are reported and re-prompted. Typing "quit" at any prompt
    prints a cancellation message and returns False.
    """
    # Repeat the menu until it is valid, or the user cancels.
    while True:
        user_search_option = input(
            "What would you like to search by:\n1. Title \n2. Category\n3. Date "
            "\n\nEnter your option number here (or type 'quit' to exit): "
        ).strip()
        if user_search_option.lower() == "quit":
            print("Search cancelled. Returning to the previous menu.")
            return False
        if user_search_option in ("1", "2", "3"):
            int_search_option = int(user_search_option)
            break
        print("Invalid option. Please enter 1, 2, or 3 (or type 'quit' to exit).")

    # Search by title.
    if int_search_option == 1:
        while True:
            title_search_value = input(
                "\nEnter the name of the incident you want to search for "
                "(or type 'quit' to exit): "
            ).strip()
            if title_search_value.lower() == "quit":
                print("Search cancelled. Returning to the previous menu.")
                return False
            if title_search_value:
                search_results = data_manager.query(
                    lambda record: (record.get("input", {}).get("incident_name") or "")
                    .strip().lower() == title_search_value.lower()
                )
                return search_results, title_search_value
            print("Name of the incident is empty. Please enter a name.")

    # Search by category.
    elif int_search_option == 2:
        while True:
            category_search_value = input(
                "Enter the category of the incident you want to search for "
                "(or type 'quit' to exit): "
            ).strip()
            if category_search_value.lower() == "quit":
                print("Search cancelled. Returning to the previous menu.")
                return False
            if category_search_value:
                search_results = data_manager.query(
                    lambda record: (record.get("ai", {}).get("hazard_category") or "")
                    .strip().lower() == category_search_value.lower()
                )
                return search_results, category_search_value
            print("Category is empty. Please enter a category.")

    else:
        while True:
            datetime_search_type = input(
                "\nSearch incident datetime by \n1. Date and Time Range"
                "\n2. Specific Datetime\nEnter your option number here "
                "(or type 'quit' to exit): "
            ).strip()
            if datetime_search_type.lower() == "quit":
                print("Search cancelled. Returning to the previous menu.")
                return False
            if datetime_search_type in ("1", "2"):
                datetime_search_type_int = int(datetime_search_type)
                break
            print("Invalid option. Please enter 1 or 2 (or type 'quit' to exit).")

        def ask_valid_datetime(prompt):
            while True:
                value = input(prompt).strip()
                if value.lower() == "quit":
                    return None
                try:
                    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
                    return parsed.isoformat(timespec="seconds"), value
                except ValueError:
                    print(
                        "Invalid format. Please enter YYYY-MM-DD HH:MM "
                        "(e.g., 2023-10-25 14:30), or type 'quit' to exit."
                    )

        if datetime_search_type_int == 1:
            start = ask_valid_datetime(
                "\nEnter the start datetime you want to search by "
                "(YYYY-MM-DD HH:MM, or type 'quit' to exit): "
            )
            if start is None:
                print("Search cancelled. Returning to the previous menu.")
                return False
            valid_start_datetime, search_start_datetime_input = start

            while True:
                end = ask_valid_datetime(
                    "Enter the end datetime you want to search by "
                    "(YYYY-MM-DD HH:MM, or type 'quit' to exit): "
                )
                if end is None:
                    print("Search cancelled. Returning to the previous menu.")
                    return False
                valid_end_datetime, search_end_datetime_input = end
                if valid_end_datetime >= valid_start_datetime:
                    break
                print("End datetime cannot be earlier than the start datetime. Please try again.")

            search_results = data_manager.query(
                lambda record: valid_start_datetime
                <= (record.get("input", {}).get("incident_datetime") or "")
                <= valid_end_datetime
            )
            search_string = (
                f"incidents between {search_start_datetime_input} and {search_end_datetime_input}"
            )
            return search_results, search_string

        exact = ask_valid_datetime(
            "\nEnter the datetime you want to search for "
            "(YYYY-MM-DD HH:MM, or type 'quit' to exit): "
        )
        if exact is None:
            print("Search cancelled. Returning to the previous menu.")
            return False
        valid_search_datetime, search_datetime_input = exact
        search_results = data_manager.query(
            lambda record: record.get("input", {}).get("incident_datetime")
            == valid_search_datetime
        )
        return search_results, search_datetime_input


#function to display a numbered list of search results, ask the user to pick one, and then show that incident's full review report
def display_search_results(search_results_data, user_search_query):
    #SEARCH RESULTS DATA MUST RETURN INCIDENTID
    # (every record in search_results_data must contain a "record_id", because it is used below to open the full report)
    """
    variables in the function:
    search_results_data - the list of matching records returned by the search (each record is a nested dictionary with "input" and "record_id")
    user_search_query - the text describing what was searched for, shown in the heading
    num_of_search_results - how many records were found
    i - the position of the current result in the list, starting from 1 (shown to the user as [1], [2], ...)
    data - one record at a time while looping through the results
    formatted_datetime - the incident's date and time formatted like "16 September 2026, 14:30"
    view_incident_number - the result number the user typed in to view in detail
    view_incident_data_id - the record_id of the incident the user chose

    This method prints results and shows the selected incident review.
    It re-prompts after invalid selections, returns False if there are no results
    or the user types "quit", and returns None after showing a report.

    intended layout of the output (as originally written):
    3 incident(s) found for ''

    Incident Name   :   Falling of ladder
    Incident Date and Time: 16 September 2026
    Location    :   Clarke Quay
    -----------------------------------------------
    """
    # count how many records were found
    num_of_search_results = len(search_results_data)
    # if nothing matched, tell the user and stop the method
    if(num_of_search_results == 0):
        print(f"No Search Results for '{user_search_query}'")
        return False
    else:
        # heading showing how many incidents were found and what was searched for
        print(f"\n{num_of_search_results} incident(s) for '{user_search_query}':\n")
        # loop through the results; enumerate(..., start=1) numbers them from 1 instead of 0
        for i,data in enumerate(search_results_data, start=1):
            # convert the stored ISO datetime string into a readable format, e.g. "16 September 2026, 14:30"
            formatted_datetime = datetime.fromisoformat(data['input']['incident_datetime']).strftime("%d %B %Y, %H:%M")

            # print one result: its number and name, then its date/time and location
            # ('<22' pads each label to 22 characters so the colons line up)
            print(f"[{i}] {data['input']['incident_name']}")
            print(f"{'Incident Date and Time':<22}: {formatted_datetime}")
            print(f"{'Location':<22}: {data['input']['location']}")
            # a divider line between results ("\n" adds a blank line after it)
            print("-" * 47, "\n")

        while True:
            selection = input(
                "Enter the search result number to view incident details "
                "(or type 'quit' to exit): "
            ).strip()
            if selection.lower() == "quit":
                print("Search cancelled. Returning to the previous menu.")
                return False
            try:
                view_incident_number = int(selection)
            except ValueError:
                print("Error: invalid search result number. Please enter a whole number (or type 'quit' to exit).")
                continue

            if not 1 <= view_incident_number <= num_of_search_results:
                print("Error: please enter a number shown in the search results (or type 'quit' to exit).")
                continue
            break

        view_incident_data_id = search_results_data[view_incident_number - 1]['record_id']
        print("\n")
        generate_incident_review(view_incident_data_id)

#print(generate_incident_review("INC-2026-0001"))
if __name__ == "__main__":
    # importing this module (e.g. from main.py) must not start the
    # interactive search session
    searchOptions = handle_search_options()
    if(searchOptions != False):
         display_search_results(searchOptions[0],searchOptions[1])
