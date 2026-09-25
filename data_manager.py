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

def query():
    pass

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
