from ai_modules.create_prompt import validate_record_json,validate_incident_json,build_user_prompt,build_analysis_messages,build_retry_messages
from ai_modules.openai_connector import retry_api_call
from openai import APIError

sample_record_json = {
  "record_id": "1",
  "input": {
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "incident_datetime": "22-01-2026 13:10",
    "injury_reported": False,
    "immediate_action": "Supervisor stopped the forklift"
  }
}

def ai_manager(record_json: dict) -> list:
    try:
        incident_json = validate_record_json(sample_record_json)
        incident_json = validate_incident_json(incident_json)
    except (TypeError,KeyError) as exc:
        return None, f"Invalid record or incident json input: {exc}"
    user_prompt = build_user_prompt(incident_json)
    llm_prompt = build_analysis_messages(user_prompt)
    try:
      llm_response = retry_api_call(llm_prompt=llm_prompt,max_attempt=3)
    except ValueError as e:
      return None, f"Malformed API response was returned: {e}"


    # TODO add JSON validation
    return llm_response

print(ai_manager(sample_record_json))
