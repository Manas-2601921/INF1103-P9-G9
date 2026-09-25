import data_manager as data
import json

def print_stored_incident_summaries(summaries):
    print("="*60)
    print("STORED INCIDENT SUMMARIES")
    print("="*60)
    if len(summaries) == 0:
        print("No data is saved yet.")
        print("-"*60)
    else:
        for summary in summaries:
            print("Incident             : ", summary.get("description"))
            print("Date                 : ", summary.get("incident_date"))
            print("Location             : ", summary.get("location"))
            print("Hazard Category      : ", summary.get("hazard_category"))
            print("Severity             : ", summary.get("severity"))
            print("Final Queue          : ", summary.get("final_queue"))
            print("Escalation Required  : ", summary.get("escalation_required"))
            print("-"*60)

if __name__ == "__main__":
    print_stored_incident_summaries(data.query_stored_incident_summaries())
