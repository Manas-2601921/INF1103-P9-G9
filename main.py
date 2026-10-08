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

# Just a Testing scripte below
if __name__ == "__main__":
    incident_location = "Warehouse A"
    reporter_role = "Employee"
    severity = 0.5

    matching_incidents = data.query_severity(severity, ">")
    matching_ids = {record["record_id"] for record in matching_incidents}

    summaries = [
        summary for summary in data.query_stored_incident_summaries()
        if summary["record_id"] in matching_ids
    ]
    summaries.sort(key=lambda summary: float(summary["severity"]), reverse=True)

    print(f"\nINCIDENT QUERY: severity > {severity}")
    print(f"Matching incidents: {len(summaries)}\n")

    if summaries:
        print_stored_incident_summaries(summaries)
    else:
        print("No incidents found for the specified reporter role.")


'''

Possible Failures:

general:
    - programming errors (use Exceptions)

load():
    - ✅File does not exist   - right now, showing the message and returning empty list
    - ✅Empty File            - catched by JSONDecodeError - showing the message and returning empty list
    - ✅Invalid / Corrupted JSON Format - JSONDecodeError - showing the message and returning empty list
    - ✅Valid JSON but wrong top level type (not a list) - need to manually check
    - (what if it still returns a list but the list contains non-dictionary items? - need to manually check))
    - Permission denied to read the file
    - Disk / Read errors

save():
    - argument is not a dictionary
    - missing expected fields in a dictionary (e.g. input, ai, logic) or having extra fields
    - ✅"data" folder does not exist (already solved)
    - load() fails
    - argument contains non-JSON-serializable data
    - Permission denied to write the file
    - Disk / IO failures

query():
    - no records exist (just retrun empty list)
    - `filter_fn` is invalid
    - record is missing major fields (e.g. record_id, input, ai, logic)
    - stored record is not a dictionary

'''
    
