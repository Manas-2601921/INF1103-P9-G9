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

    # data.save(dictionary object)
    print_stored_incident_summaries(data.query_stored_incident_summaries())


'''

Possible Failures:

general:
    - programming errors (use Exceptions)

load():
    - File does not exist
    - Empty File
    - Invalid / Corrupted JSON Format
    - Valid JSON but wrong top level type (not a list)
    - Permission denied to read the file
    - Disk / Read errors

save():
    - argument is not a dictionary
    - "data" folder does not exist (already solved)
    - load() fails
    - arugment contains non-JSON-serializable data
    - Permission denied to write the file
    - Disk / IO failures

query():
    - no records exist (just retrun empty list)
    - `filter_fn` is invalid
    - record is missing major fields (e.g. record_id, input, ai, logic)
    - stored record is not a dictionary

'''
    
