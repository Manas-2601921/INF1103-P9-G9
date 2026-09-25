from pathlib import Path
import json

incidents = Path("data/incidents.json")

def load():
    if incidents.exists():
        with open(incidents, "r") as f:
            return json.load(f)
    return {}

def save(dict):
    pass

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
