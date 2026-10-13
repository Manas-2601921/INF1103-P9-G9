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
 
    this method returns a tuple of (search_results, description of what was searched for) when a search runs
    (search_results is an empty list if nothing matched).
    It returns False (after printing an error message) if the menu choice or date sub-menu choice is invalid,
    a search value is empty, a datetime format is wrong, or the start datetime is later than the end datetime
    """
    # placeholder for the search results, replaced once a search is run
    search_results = {}
    # show the main menu and read the user's choice as text
    user_search_option = input("What would you like to search by:\n1. Title \n2. Category\n3. Date \n\nEnter your option number here: ")
    # check that the choice is made up of digits only
    if user_search_option.isdigit() == False :
        print("Invalid input. Please enter a valid number based on the options above.")
        return False
    else:
        # convert the choice to an integer; the except catches any digit-like character that int() cannot convert
        try:
            int_search_option = int(user_search_option)
        except ValueError:
            print("Invalid option. Please enter a valid option number.")
            return False
        # check that the number is one of the three menu options (1, 2 or 3)
        if int_search_option != 1 and int_search_option != 2 and int_search_option != 3:
            print("Invalid option. Please enter a valid option number.")
            return False
        else:
            #search option is valid, now we can proceed to search for the incident
            # option 1: search by incident title
            if int_search_option == 1 :
                title_search_value = input("\nEnter the name of the incident you want to search for: ")
                #method to search for the incident by title
                # .strip() removes surrounding spaces, so an entry with only spaces counts as empty
                if not title_search_value.strip():
                    print("Name of the incident is empty.")
                    return False
                else:
                    # find records whose incident_name matches the user's text, ignoring capitalisation and surrounding spaces
                    # ("or ''" treats a missing incident_name as an empty string)
                    search_results = data_manager.query(lambda record: (record.get("input", {}).get("incident_name") or "").strip().lower() == title_search_value.strip().lower())
                    # return the matching records along with the text that was searched for
                    return search_results,title_search_value
 
 
            # option 2: search by incident category
            elif int_search_option == 2 :
                    # show the categories that actually exist in the incident log
                    # so the user knows what can be searched for
                    stored_categories = sorted({
                        (record.get("ai", {}).get("hazard_category") or "").strip()
                        for record in data_manager.query(lambda record: True)
                    } - {""})
                    if stored_categories:
                        print("\nCategories currently in the incident log:")
                        for stored_category in stored_categories:
                            print(f"  - {stored_category}")
                    category_search_value = input("\nEnter the category of the incident you want to search for: ")
                    # an entry with only spaces counts as empty
                    if not category_search_value.strip():
                        print("Category of Incident is empty. No category to search by.")
                        return False
                    else:
                        # match when the typed text appears anywhere in the stored category
                        # (case-insensitive), so 'fire' also finds 'fire/emergency egress'
                        search_results = data_manager.query(lambda record: category_search_value.strip().lower() in (record.get("ai", {}).get("hazard_category") or "").strip().lower())
                        # return the matching records along with the text that was searched for
                        return search_results,category_search_value
 
            # option 3: search by date and time, which opens a second menu
            elif int_search_option == 3 :
                # show the date sub-menu and read the user's choice as text
                datetime_search_type = input("\nSearch incident datetime by \n1. Date and Time Range\n2. Specific Datetime\nEnter your option number here: ")
                # convert the sub-menu choice to an integer; if it isn't a number, show an error and stop
                # (without the return, the code below would use datetime_search_type_int before it was ever set and crash)
                try:
                    datetime_search_type_int = int(datetime_search_type)
                except ValueError:
                    print("Invalid option entered. Enter the option number only.")
                    return False
                # sub-option 1: search between a start and an end datetime
                if datetime_search_type_int == 1 :
                    #user wants to search by date and time
                    search_start_datetime_input = input("\nEnter the start datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                    try:
                        # convert the typed text into a datetime using the format YYYY-MM-DD HH:MM, then into an ISO string to match how records store their datetimes
                        # (a wrong format raises a ValueError, which is caught below)
                        valid_start_datetime = datetime.strptime(search_start_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print("Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False
                    try:
                        search_end_datetime_input = input("Enter the end datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                        # convert the end datetime to an ISO string in the same way as the start datetime
                        valid_end_datetime = datetime.strptime(search_end_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print("Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False
                    # make sure the start is not later than the end (ISO strings sort in time order, so they can be compared directly)
                    if valid_start_datetime > valid_end_datetime :
                        print("start value cannot be greater than end value")
                        return False
                    # find records whose incident_datetime is between the start and end datetimes (inclusive)
                    # ("or ''" treats a missing incident_datetime as an empty string, which sorts before any start value,
                    # so a record with no datetime is skipped instead of crashing the whole search)
                    search_results = data_manager.query(lambda record: valid_start_datetime <= (record.get("input", {}).get("incident_datetime") or "") <= valid_end_datetime)
                    # build a readable description of the search to display with the results
                    search_string = f"incidents between {search_start_datetime_input} and {search_end_datetime_input}"
                    return search_results, search_string
                # sub-option 2: search for one exact datetime
                elif datetime_search_type_int == 2 :
                    search_datetime_input =  input("Enter the datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                    try:
                         # convert the typed text into an ISO string, same as in the range search
                         valid_search_datetime = datetime.strptime(search_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print("Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False
 
                    # find records whose incident_datetime is exactly equal to the datetime entered
                    search_results = data_manager.query(lambda record: record.get("input", {}).get("incident_datetime") == valid_search_datetime)
                    # return the matching records along with the datetime text that was searched for
                    return search_results,search_datetime_input
                # the number entered on the date sub-menu is neither 1 nor 2
                else:
                    print("Invalid option number entered.")
                    return False
            
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
 
    this method prints the results and, if the user picks a valid result number, prints the full incident review.
    It returns False (after printing a message) if there are no results or the user's choice is invalid,
    and returns nothing after showing a report
 
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
 
        # ask which result the user wants to view and convert their typed text to a whole number
        try:
            view_incident_number = int(input("Enter the search result number to view incident details: "))
 
        except ValueError:
            # the user typed something that isn't a whole number, so show an error and stop
            print("Error: invalid search result number")
            return False
 
        # reject a number below 1 or above the number of results, then show an error and stop
        # (this check must come BEFORE the list lookup below: otherwise a number that is too big crashes with an IndexError,
        # and 0 or a negative number would silently pick a record from the end of the list)
        if view_incident_number < 1 or view_incident_number > num_of_search_results:
            print("Error: option entered is not a valid number from the search results")
            return False
 
        # the number is valid, so subtract 1 (the user's numbers start at 1 but the list starts at 0) to get the chosen record, then read its record_id
        view_incident_data_id = search_results_data[view_incident_number-1]['record_id']

        print("\n")
        # print the full incident report for the chosen record
        generate_incident_review(view_incident_data_id)
    