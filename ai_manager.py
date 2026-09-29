from ai_modules.create_prompt import validate_record_json,validate_incident_json,build_user_prompt,build_analysis_messages,build_retry_messages

sample_record_json = {
  "record_id": "1",
  "input": {
    "description": "Forklift nearly hit a worker while reversing.",
    "location": "Warehouse",
    "reporter_role": "Employee",
    "incident_datetime": "2026-09-21",
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
    LLM_PROMPT = build_analysis_messages(user_prompt)

    # TODO add processing later on
    return LLM_PROMPT

print(ai_manager(sample_record_json))