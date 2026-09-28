import json

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
def generate_record_id():
    print("generate_record_id called")
    return 

def query_description():
    print("query_description called")
    return

def query_location():
    print("query_location called")
    return

def query_reporter_role():
    print("query_reporter_role called")
    return

def query_incident_date():
    print("query_incident_date called")
    return 

def query_injury_reported():
    print("query_injury_reported called")
    return

def query_immediate_action():
    print("query_immediate_action called")
    return

#Output Incident Information methods 
def load_file(filepath, filePermission):
    '''
    This is a method to load files with error handling in place. 

    Refer to the method fields below to understand what the method requires to execute successfully:
    filePath = the path leading to the file storing data
    filePermission = r/w/r+ : how the user wants the file to be loaded.
    
    '''
    try:
        with open(filepath,filePermission, encoding="utf-8")as filehandler:
                    records = json.load(filehandler)
    except FileNotFoundError:
        # print("Data file is not found")
        return "Error: File is not found"
    except json.JSONDecodeError:
        # print("invalid json error")
        return "Error: Invalid JSON error"
    else:
        return records

def generate_incident_review(incidentId):
    if(incidentId == ""):
        return "Error: Incident id is missing"
    records = load_file('testdata/incidentDummyRecords.json','r+')
    for record in records:
        if(record["record_id"] == incidentId):
            recordToGet = record
        if recordToGet is None:
            return "Error: No such record exists in our records."
    incidentReview = f"""Here is the information for the incident reported:\nIncident: {recordToGet["input"]["description"]}\nIncident location: {recordToGet["input"]["location"]}\nIncident date: {recordToGet["input"]["incident_date"]}\nFrom our application's analysis.. this incident needs {recordToGet["logic"]["final_queue"]}\nThis is serious because \n {recordToGet["ai"]["severity_explanation"]}"""
    return incidentReview

print(generate_incident_review("INC-2026-0001"))