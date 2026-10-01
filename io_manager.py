import json
from datetime import datetime
#from data_manager import *

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
def generate_record_id():
    print("generate_record_id called")

    return 

def prompt_description():
    print("prompt_description called")
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
    print("prompt_location called")
    while True:
        newIncidentLocation = input("Enter the location of the incident (or type 'quit' to exit): ")
        if newIncidentLocation.lower() == 'quit':
            return "quit"
        elif newIncidentLocation is None:
            print("Invalid input. Please enter a valid incident location.")
            continue
        return newIncidentLocation
    return

def prompt_reporter_role():
    print("prompt_reporter_role called")
    return

def prompt_incident_date():
    print("prompt_incident_date called")
    return 

def prompt_injury_reported():
    print("prompt_injury_reported called")
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
    records = load_file('testdata/incidentDummyRecords.json','r+')
    for record in records:
        if(record["record_id"] == incident_id):
            record_to_get = record
        if record_to_get is None:
            return "Error: No such record exists in our records."
    incident_review = f"""Here is the information for the incident reported:\nIncident: {record_to_get["input"]["description"]}\nIncident location: {record_to_get["input"]["location"]}\nIncident date: {record_to_get["input"]["incident_date"]}\nFrom our application's analysis.. this incident needs {record_to_get["logic"]["final_queue"]}\nThis is serious because \n {record_to_get["ai"]["severity_explanation"]}"""
    return incident_review

def handle_search_options():
    search_results = {}
    user_search_option = input("What would you like to search by:\n1. Title \n2. Category\n3. Date \nEnter your option number here: ")
    if(user_search_option.isdigit() == False):
        print("Invalid input. Please enter a valid option number.")
    else:
        int_search_option = int(user_search_option)
        if(int_search_option != 1 and int_search_option != 2 and int_search_option != 3):
            print("Invalid input. Please enter a valid option number.")
        else:
            #search option is valid, now we can proceed to search for the incident
            if(int_search_option == 1):
                title_search_value = input("Enter the name of the incident you want to search for: ")
                #method to search for the incident by title
                return search_results,title_search_value
            elif(int_search_option == 2):
                category_search_value = input("Enter the category of the incident you want to search for: ")
                #method to search for the incident by category
                return search_results,category_search_value
            elif(int_search_option == 3):
                date_search_value = input("Enter the date of the incident you want to search for. Follow the format (YYYY-MM-DD): ")
                #convert string to datetime object
                #handle the case where the user enters an invalid date format
                try:
                    date_search_value = datetime.strptime(date_search_value, "%Y-%m-%d")
                except ValueError:
                    print("Invalid date format. Please enter the date in the format (YYYY-MM-DD).")
                #method to search for the incident by date
                return search_results,date_search_value
            
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
    print(f"{num_of_search_results} Search Results for '{user_search_query}':")
    for data in search_results_data:
        formated_data = f"#{str(incident_number)}\t{data['input']['incident_name']}\n{data['input']['description']}\n{data['input']['incident_datetime']}\t{data['input']['location']}"
        print(formated_data)
        incident_number += 1
    user_view_details = input("Would you like to view the details of any particular incident? If yes, please enter the number that the incident is listed as in the search results: ")
    if user_view_details.isdigit():
        user_view_details = int(user_view_details)
        if user_view_details < 0 or user_view_details >= num_of_search_results:
            print("Invalid input. Please enter a valid incident number.")
        else:
            return
            #need to fetch the incident data based on incidentId and display the details of the incident


print(generate_incident_review("INC-2026-0001"))