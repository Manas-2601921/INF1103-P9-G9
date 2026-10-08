import json
from datetime import datetime
import datamanager #temporary data manager file import to test workability with data manager

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

def prompt_reporter_role():

    while True:
        newIncidentReporterRole = input(f"Enter your role in the company (or type 'quit' to exit): " + "\n1. Employee\n2. Supervisor\n3. Manager\n4. Client")

        if newIncidentReporterRole.lower() == 'quit':
            return "quit"
        elif newIncidentReporterRole is None:
            print("Invalid input. Please enter a valid role.")
            continue
        elif newIncidentReporterRole == "1" or newIncidentReporterRole.lower() == "employee":
            newIncidentReporterRole = "Employee"
            return newIncidentReporterRole
        elif newIncidentReporterRole == "2" or newIncidentReporterRole.lower() == "supervisor":
            newIncidentReporterRole = "Supervisor"
            return newIncidentReporterRole
        elif newIncidentReporterRole == "3" or newIncidentReporterRole.lower() == "manager":
            newIncidentReporterRole = "Manager"
            return newIncidentReporterRole
        elif newIncidentReporterRole == "4" or newIncidentReporterRole.lower() == "client":
            newIncidentReporterRole = "Client"
            return newIncidentReporterRole
        else:
            print("Invalid input. Please enter a valid role.")
            continue
    

def prompt_incident_date_time():
    while True:
        print("prompt_incident_date_time called")
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
    print("prompt_injury_reported called")
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
    print("prompt_immediate_action called")
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

def generate_incident_review(incident_id):
    if(incident_id == ""):
        return "Error: Incident id is missing"
    records = datamanager.load()
    record_to_get = None
    for record in records:
        if(record["record_id"] == incident_id):
            record_to_get = record
            display_datetime = datetime.fromisoformat(record_to_get["input"]["incident_datetime"]).strftime("%d %B %Y, %H:%M")
            incident_review = f"""\n\nHere is the information for the incident reported:\nIncident: {record_to_get["input"]["description"]}\nIncident location: {record_to_get["input"]["location"]}\nIncident timestamp: {display_datetime}\nFrom our application's analysis.. this incident needs {record_to_get["logic"]["final_queue"]}\nThis is serious because\n{record_to_get["ai"]["severity_explanation"]}"""
    if record_to_get is None:
                return "Error: No such record exists in our records."
    return incident_review

def handle_search_options():
    search_results = {}
    user_search_option = input("What would you like to search by:\n1. Title \n2. Category\n3. Date \n\nEnter your option number here: ")
    if(user_search_option.isdigit() == False):
        print("Invalid input. Please enter a valid option number.")
    else:
        int_search_option = int(user_search_option)
        if(int_search_option != 1 and int_search_option != 2 and int_search_option != 3):
            print("Invalid input. Please enter a valid option number.")
        else:
            #search option is valid, now we can proceed to search for the incident
            if(int_search_option == 1):
    
                title_search_value = input("\n\nEnter the name of the incident you want to search for: ")
                #method to search for the incident by title
                if not title_search_value.strip():
                    print("Name of the incident is empty.")
                    return False
                else:
                    search_results = datamanager.query(lambda record: record.get("input", {}).get("incident_name") == title_search_value)
                    return search_results,title_search_value

            
            elif(int_search_option == 2):
                    category_search_value = input("Enter the category of the incident you want to search for: ")
                    if not category_search_value.strip():
                        print("Category of Incident is empty. No category to search by.")
                        return False
                    else:
                        search_results = datamanager.query(lambda record: record.get("ai", {}).get("hazard_category") == category_search_value)
                        #method to search for the incident by category
                        return search_results,category_search_value
            
            elif(int_search_option == 3):
                datetime_search_type = input("\nSearch incident datetime by \n1. Date and Time Range\n2.Specific Datetime\nEnter your option number here: ")
                datetime_search_type_int = int(datetime_search_type)
                if(datetime_search_type_int == 1):
                    #user wants to search by date and time
                    search_start_datetime_input = input("\nEnter the start datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                    try:
                        valid_start_datetime = datetime.strptime(search_start_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print(f"Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False
                    try:
                        search_end_datetime_input = input("Enter the end datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                        valid_end_datetime = datetime.strptime(search_end_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print(f"Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False
                    if(valid_start_datetime > valid_end_datetime):
                        print("start value cannot be greater than end value")
                        return False
                    search_results = datamanager.query(lambda record: valid_start_datetime <= record.get("input", {}).get("incident_datetime") <= valid_end_datetime)
                    search_string = f"incidents betweeen {search_start_datetime_input} and {search_end_datetime_input}"
                    return search_results, search_string
                elif(datetime_search_type_int == 2):
                    search_datetime_input =  input("Enter the datetime you want to search by (e.g. YYYY-MM-DD HH:MM, 2023-10-25 14:30): ")
                    try:
                         valid_search_datetime = datetime.strptime(search_datetime_input, "%Y-%m-%d %H:%M").isoformat(timespec="seconds")
                    except ValueError:
                        print(f"Invalid format. Please follow the format: YYYY-MM-DD HH:MM (e.g., 2023-10-25 14:30)")
                        return False

                    search_results = datamanager.query(lambda record: record.get("input", {}).get("incident_datetime") == valid_search_datetime)
                    return search_results,search_datetime_input
                else:
                    print("Invalid option number entered.")
                    return False
                
                # #convert string to datetime object
                # #handle the case where the user enters an invalid date format
                # try:
                #     date_search_value = datetime.strptime(date_search_value, "%Y-%m-%d")
                # except ValueError:
                #     print("Invalid date format. Please enter the date in the format (YYYY-MM-DD).")
                # #method to search for the incident by date
                # search_results = datamanager.query(lambda record: record.get("input", {}).get("incident_datetime") == date_search_value)
                # return search_results,date_search_value
            
def display_search_results(search_results_data, user_search_query): 
    #SEARCH RESULTS DATA MUST RETURN INCIDENTID 
    """12 Search Results for 'user_search_query':

#1 Falling of ladder
A worker was painting the building when he fell off the lader
Incident Date: 16/09/2004 Location: Clarke Quay

#1 Falling of ladder
A worker was painting the building when he fell off the lader
Incident Date: 16/09/2004 Location: Clarke Quay

#1 Falling of ladder
A worker was painting the building when he fell off the lader
Incident Date: 16/09/2004 Location: Clarke Quay"""

    incident_number = 0
    num_of_search_results = len(search_results_data)
    if(search_results_data == 0):
        print(f" No Search Results for '{user_search_query}':")
    else:
        print(f"\n\n{num_of_search_results} Search Results for '{user_search_query}':")
        for data in search_results_data:

            formated_data = f"#{str(incident_number)}\t{data['input']['incident_name']}\n{data['input']['description']}\n{datetime.fromisoformat(data['input']['incident_datetime']).strftime("%d %B %Y, %H:%M")}\t{data['input']['location']}\n"
            print(formated_data)
            incident_number += 1

        try:
            view_incident_number = int(input("Enter the search result number to view incident details: "))
        except ValueError:
            print("Error: invalid search result number")

        view_incident_data_id = search_results_data[view_incident_number]['record_id']
        review = generate_incident_review(view_incident_data_id)
        print(review)



#print(generate_incident_review("INC-2026-0001"))
searchOptions = handle_search_options()
if(searchOptions != False):
    display_search_results(searchOptions[0],searchOptions[1])
    