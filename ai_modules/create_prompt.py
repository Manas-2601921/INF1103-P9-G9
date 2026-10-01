# Fields copied from the input section of the shared record into the
# user prompt
SYSTEM_PROMPT = """You are the classification engine of a workplace incident triage system for
    small and medium-sized companies in Singapore (Workplace Safety and Health
    context). You analyse one incident report at a time. You suggest an initial
    classification and cite the evidence; a rule engine makes the final decision.

    Reply with ONE valid JSON object and nothing else: no markdown fences, no
    commentary before or after the object. Use exactly this schema:

    {
    "severity": "low" | "medium" | "high",
    "confidence": 0.0 ,
    "severity_explanation": "string",
    "hazard_category": "string",
    "incident_type": "string",
    "indicators": {
        "injury": false,
        "immediate_danger": false,
        "exposure": false,
        "equipment_involvement": false,
        "work_stoppage": false,
        "uncontrolled_hazard": false
    },
    "repeat_pattern_indicators": {
        "hazard_category": "string",
        "location": "string",
        "datetime": "string",
        "activity": "string"
    },
    "recommended_immediate_action": "string",
    "supporting_phrase": "string"
    }

    Field rules:
    - "severity": "high" when a person was harmed or serious harm was a real
    possibility; "medium" when the hazard needs attention but harm was
    unlikely; "low" only for minor, well-controlled issues.
    - "confidence": a number from 0.0 to 1.0 showing how sure you are of the
    classification.
    - "severity_explanation": one or two sentences citing the evidence.
    - "hazard_category": exactly one of "electrical", "fire", "chemical",
    "ergonomic", "slip/trip/fall", "mechanical", "biological", "psychosocial",
    "other".
    - "incident_type": exactly one of "near-miss", "injury", "unsafe condition",
    "property damage", "complaint".
    - "indicators": booleans. injury = a person was harmed; immediate_danger =
    someone could be harmed right now; exposure = people were exposed to the
    hazard; equipment_involvement = tools, machines or vehicles were involved;
    work_stoppage = work was paused or stopped; uncontrolled_hazard = no
    effective control is in place yet.
    - "repeat_pattern_indicators": comparison keys used by the rule engine for
    duplicate and recurring-incident detection. hazard_category repeats the
    value above; location and datetime are copied from the report; activity
    names what was being done (e.g. "forklift reversing").
    - "recommended_immediate_action": one short imperative sentence.
    - "supporting_phrase": an exact substring copied word-for-word from the
    description (letter case may differ, wording may not).

    Never invent facts that are not in the report. If something is unclear,
    choose the safest reasonable value and lower "confidence"."""
input_fields =  ("description","location","reporter_role","incident_datetime","injury_reported","immediate_action")

def validate_record_json(record_json: dict) -> dict:
    """Validate the record_json received from the IO manager layer is a dictionary and it contains the incident_json inside the input field
    
    Args:
        record_json: the shared record
        
    Returns:
        The incident_json contained within the input section for the shared record. Returns an error if the shared record is the wrong data type or input field is missing
    """

    if isinstance(record_json,dict) == False:
        # If record_json from io manager is not a dictionary throw error
        raise TypeError(f"record_json is not a dictionary got {type(record_json).__name__} instead")
    
    try:
        incident_json = record_json["input"]
    except KeyError:
        raise KeyError("record_json input section is missing or has empty fields")
    return incident_json

def validate_incident_json(incident_json: dict) -> dict:
    """Validates the incident json inside the record json received from the IO manager layer, ensure that the input is in a dictionary format and all required fields are present
    
    Args:
        incident_json: the input section for the shared record

    Returns:
        The same incident_json is expected however if the json is not a dictionary or contains missing fields
        the function will throw an error
    """
    if isinstance(incident_json,dict) == False:
        # If incident_json from io manager is not a dictionary throw error
        raise TypeError(f"incident_json is not a dictionary got {type(incident_json).__name__} instead")
    missing_key = []
    for key in input_fields:
        if key not in incident_json:
            # If incident_json does not contain all required fields, throw key error
            missing_key.append(key)
    if missing_key:
        raise KeyError(f"incident_json is missing or has empty fields for the {missing_key} required fields")
    return incident_json


def build_user_prompt(incident_json: dict) -> str:
    """Render the incident fields as a labelled list for the model.

    Args:
        incident: the input section of the shared record.

    Returns:
        A plain-text incident brief ending with the reply instruction.
        Missing fields are rendered as "not provided" so a partial record
        still produces a usable prompt instead of a crash.
    """

    lines = ["Incident report to analyse:"]
    for key in incident_json.keys(): 
        lines.append(str({key:incident_json[key]})) # Construct user prompt using incident_json and combined them into a string
    lines.append("Analyse this incident and reply with the JSON object only.")
    return "\n".join(lines)


def build_analysis_messages(USER_PROMPT: str) -> list[dict]:
    """Build the chat messages for a first-pass incident analysis.

    Args:
        USER_PROMPT: from the build_user_prompt function

    Returns:
        A ``messages`` payload in chat-completions format: one system
        message with the schema contract, one user message with the report.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]


def build_retry_messages(
    incident_json: dict, previous_reply: str, errors: list[str]
) -> list[dict]:
    """Build chat messages asking the model to fix a rejected reply.

    Used by ``analyzer.analyze_incident`` when validation fails: the exact
    rule violations and the previous reply are shown so the model can
    correct itself instead of guessing what went wrong.

    Args:
        incident: the ``input`` section of the shared record.
        previous_reply: the raw reply text that failed validation.
        errors: the rule violations reported by ``validator.validate_ai_result``.

    Returns:
        A ``messages`` payload for the retry attempt.
    """
    error_list = "\n".join(f"- {message}" for message in errors)
    content = (
        "Your previous reply was rejected because it broke these rules:\n"
        f"{error_list}\n"
        "\n"
        "Your previous reply was:\n"
        f"{previous_reply}\n"
        "\n"
        "Send a corrected JSON object for the incident below. Reply with the\n"
        "JSON object only.\n"
        "\n"
        f"{build_user_prompt(incident_json)}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
