import json
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

def display_search_results(search_results_data): 
    incident_number = 0
    for data in search_results_data:
        formated_data = f"#{str(incident_number)}\t{data['input']['incident_name']}\n{data['input']['description']}\n{data['input']['incident_datetime']}\t{data['input']['location']}"
        print(formated_data)
        incident_number+1

print(generate_incident_review("INC-2026-0001"))