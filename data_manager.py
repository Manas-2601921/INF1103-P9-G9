from pathlib import Path
from datetime import datetime
import json

incidents = Path("data/incidents.json")

def load():
    if incidents.exists():
        with open(incidents, "r", encoding="utf-8") as f:
            return json.load(f)
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
    incidents.parent.mkdir(parents=True, exist_ok=True)
    
    with open(incidents, "w", encoding="utf-8") as f:
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