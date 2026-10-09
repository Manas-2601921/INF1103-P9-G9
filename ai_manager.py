from ai_modules.create_prompt import validate_record_json,validate_incident_json,build_user_prompt,build_analysis_messages,build_retry_messages
from ai_modules.openai_connector import retry_api_call
from ai_modules.validate_ai_output import validate_ai_output
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

    # Validate the reply and reprompt the AI with the schema violations when
    # it fails, up to a maximum of 3 attempts
    max_validation_attempts = 3
    for attempt in range(max_validation_attempts):
        try:
            llm_response = retry_api_call(llm_prompt=llm_prompt,max_attempt=3)
        except ValueError as e:
            return None, f"Malformed API response was returned: {e}"

        parsed_output, validation_errors = validate_ai_output(llm_response)
        if not validation_errors:
            return parsed_output
        llm_prompt = build_retry_messages(incident_json, llm_response, validation_errors)

    return None, f"AI output failed schema validation after {max_validation_attempts} attempts: {validation_errors}"

print(ai_manager(sample_record_json))
