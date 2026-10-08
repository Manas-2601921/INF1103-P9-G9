from pathlib import Path
from datetime import datetime
import json

incidents_file = Path("data/incidents.json")

def load():
    if incidents_file.exists():
        try:
            with open(incidents_file, "r", encoding="utf-8") as f:
                incidents_data = json.load(f)
                if isinstance(incidents_data, list):
                    return incidents_data
                else:
                    print("\n" + "-"*60 + "\n")
                    print("[Error]   : Fail to load data.")
                    print("[Reason]  : JSON returns a top-level type that is not a list. Please contact the support team.")
                    print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
                    print("\n" + "-"*60 + "\n")
                    return []
        except json.JSONDecodeError:    # if file exists but empty, this error is also raised
            print("\n" + "-"*60 + "\n")
            print("[Error]   : Fail to load data.")
            print("[Reason]  : Invalid JSON format in the database file. Please contact the support team.")
            print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
            print("\n" + "-"*60 + "\n")
            return []
        except Exception as e:
            print("\n" + "-"*60 + "\n")
            print("[Error]   : Fail to load data.")
            print("[Reason]  : An unexpected error occurred while reading the database file. Please contact the support team.")
            print(f"[Details] : {str(e)}")
            print("[Warning] : New incidents will be saved to the new database file if you wish to continue.\n            Manual combination of the old and new database files may be required.")
            print("\n" + "-"*60 + "\n")
            return []
    else:
        print("\n" + "-"*60 + "\n")
        print("Database file not found. The application must be running for the first time.\nA new database file will be created upon adding the first incident.")
        print("\nIf you are sure that you have recently saved data, please contact the Support Team.")
        print("\n" + "-"*60 + "\n")
    return []

def save(record):
    records = load()
    next_id = int(records[-1]["record_id"].split("-")[1]) + 1 if records else 1 # update last ID to next ID otherwise start with 0001
    stored_record = {
        "record_id": f"INC-{next_id:04d}",
        "input": record["input"],
        "ai": record["ai"],
        "logic": record["logic"],
        "metadata": {
            "created_at": record["ai"]["repeat_pattern_indicators"]["datetime"],
            "processed_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    records.append(stored_record)
    content = json.dumps(records, indent=4, ensure_ascii=False)

    # Create the folder "data" if it doesn't exist
    incidents_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(incidents_file, "a", encoding="utf-8") as f:
        f.write(content)
        f.write("\n")
        print("Saved record to data/incidents.json")

def query(filter_fn):
    records = load()
    return [record for record in records if filter_fn(record)]

''' =================== Utility Functions Below ! =================== '''

def query_stored_incident_summaries():  # This function is to load every stored incidents on startup
    records = load()
    summaries = []

    for record in records:
        user_input = record.get("input") or {}
        ai_response = record.get("ai") or {}
        logic = record.get("logic") or {}
        summaries.append({
            "record_id": record.get("record_id", "Unknown"),

            "incident_date": user_input.get("incident_date", "Unknown"),
            "location": user_input.get("location", "Unknown"),
            "description": user_input.get("description", "No description provided."),

            "hazard_category": ai_response.get("hazard_category", "Not assessed"),
            "severity": ai_response.get("severity", "Not assessed"),

            "final_queue": logic.get("final_queue", "Unassigned"),
            "escalation_required": logic.get("escalation_required"),
        })

    return summaries

def query_description(description):
    incidents = query(lambda record: record.get("input", {}).get("description") == description)
    return incidents

def query_location(location):
    incidents = query(lambda record: record.get("input", {}).get("location") == location)
    return incidents

def query_reporter_role(reporter_role):
    incidents = query(lambda record: record.get("input", {}).get("reporter_role") == reporter_role)
    return incidents

def query_incident_date(incident_date):
    incidents = query(lambda record: record.get("input", {}).get("incident_date") == incident_date)
    return incidents
    
def query_injury_reported(injury_reported):
    incidents = query(lambda record: record.get("input", {}).get("injury_reported") == injury_reported)
    return incidents

def query_severity(severity, comparison_operator):
    if comparison_operator == "==":
        incidents = query(lambda record: float(record.get("ai", {}).get("severity")) == severity)
    elif comparison_operator == ">":
        incidents = query(lambda record: float(record.get("ai", {}).get("severity")) > severity)
    elif comparison_operator == "<":
        incidents = query(lambda record: float(record.get("ai", {}).get("severity")) < severity)
    else:
        print("Invalid comparison operator. Use '==', '>', or '<'.")
        return [] # or raise an exception
    return incidents

def query_hazard_category(hazard_category):
    incidents = query(lambda record: record.get("ai", {}).get("hazard_category") == hazard_category)
    return incidents

# And so on...