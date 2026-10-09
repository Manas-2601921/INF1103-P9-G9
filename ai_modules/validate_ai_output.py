"""Validate the raw AI reply against the JSON schema defined in SYSTEM_PROMPT."""

import json
import re

# Schema contract copied from the SYSTEM_PROMPT in create_prompt.py:
# field name -> expected python type
TOP_LEVEL_TYPES = {
    "severity": (int, float),
    "confidence": (int, float),
    "severity_explanation": str,
    "hazard_category": str,
    "incident_type": str,
    "indicators": dict,
    "repeat_pattern_indicators": dict,
    "recommended_immediate_action": str,
    "supporting_phrase": str,
}

INDICATOR_TYPES = {
    "injury": bool,
    "immediate_danger": bool,
    "exposure": bool,
    "equipment_involvement": bool,
    "work_stoppage": bool,
    "uncontrolled_hazard": bool,
}

REPEAT_PATTERN_TYPES = {
    "hazard_category": str,
    "location": str,
    "datetime": str,
    "activity": str,
}

# Fields whose value must be one of a fixed set of strings
HAZARD_CATEGORIES = (
    "electrical", "fire", "chemical", "ergonomic", "slip/trip/fall",
    "mechanical", "biological", "psychosocial", "other",
)

INCIDENT_TYPES = ("near-miss", "injury", "unsafe condition", "property damage", "complaint")

TOP_LEVEL_ENUM_FIELDS = {
    "hazard_category": HAZARD_CATEGORIES,
    "incident_type": INCIDENT_TYPES,
}

REPEAT_PATTERN_ENUM_FIELDS = {"hazard_category": HAZARD_CATEGORIES}

SCORE_FIELDS = ("severity", "confidence")

# Human readable type names for error messages
TYPE_NAMES = {
    str: "string",
    bool: "boolean",
    dict: "object",
    (int, float): "number",
}


def parse_reply(raw_reply: str) -> dict:
    """Parse the raw reply text from the AI into a JSON object.

    Strips the markdown code fences the model may add despite being told
    not to.

    Args:
        raw_reply: the raw reply text returned by the LLM.

    Returns:
        The parsed JSON object as a dictionary.

    Raises:
        ValueError: if the reply is empty, is not valid JSON, or is not a
            JSON object.
    """
    if isinstance(raw_reply, str) == False or raw_reply.strip() == "":
        raise ValueError("reply is empty or is not text")

    text = raw_reply.strip()
    # Strip optional markdown fences (``` or ```json ... ```)
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"reply is not valid JSON: {exc}") from exc

    if isinstance(parsed, dict) == False: # Basically checks if output is a dict as json.loads also returns array sometimes
        raise ValueError(f"reply is not a JSON object, got {type(parsed).__name__} instead")
    return parsed


def check_fields(section: dict, schema: dict, section_name: str, errors: list) -> None:
    """Check every field in the schema exists in the section with the right type.

    Args:
        section: the JSON section to check.
        schema: field name -> expected python type.
        section_name: name used in error messages.
        errors: list the error messages are appended to.
    """
    for field, expected_type in schema.items():
        if field not in section:
            errors.append(f"'{section_name}' is missing required field '{field}'")
            continue
        value = section[field]
        # bool is a subclass of int, so reject it where a bool is not expected
        wrong_type = (expected_type is not bool and isinstance(value, bool)) or (
            not isinstance(value, expected_type)
        )
        if wrong_type:
            if expected_type in TYPE_NAMES:
                expected_name = TYPE_NAMES[expected_type]
            else:
                expected_name = expected_type.__name__
            errors.append(
                f"'{section_name}.{field}' must be a {expected_name}, "
                f"got {type(value).__name__} instead"
            )


def check_scores(parsed: dict, errors: list) -> None:
    """Check the severity and confidence scores are between 0.0 and 1.0.

    Args:
        parsed: the parsed reply JSON.
        errors: list the error messages are appended to.
    """
    for field in SCORE_FIELDS:
        value = parsed.get(field)
        is_number = isinstance(value, (int, float)) and isinstance(value, bool) == False
        if is_number and (value < 0.0 or value > 1.0):
            errors.append(f"'{field}' must be between 0.0 and 1.0, got {value} instead")


def check_enums(section: dict, enum_fields: dict, section_name: str, errors: list) -> None:
    """Check each enum field holds one of its allowed values.

    Args:
        section: the JSON section to check.
        enum_fields: field name -> tuple of allowed values.
        section_name: name used in error messages.
        errors: list the error messages are appended to.
    """
    for field, allowed_values in enum_fields.items():
        value = section.get(field)
        if isinstance(value, str) and value not in allowed_values:
            errors.append(
                f"'{section_name}.{field}' must be one of {list(allowed_values)}, "
                f"got '{value}' instead"
            )


def validate_ai_output(raw_reply: str) -> tuple[dict, list]:
    """Validate the raw AI reply against the JSON schema in the system prompt.

    Args:
        raw_reply: the raw reply text returned by the LLM.

    Returns:
        A tuple (parsed_json, errors). parsed_json is the parsed reply, or an
        empty dict when the reply could not be parsed. errors is a list of
        human readable rule violations and is empty when the reply is valid,
        so it can be passed straight into build_retry_messages.
    """
    try:
        parsed = parse_reply(raw_reply)
    except ValueError as exc:
        return {}, [str(exc)]

    errors = []
    check_fields(parsed, TOP_LEVEL_TYPES, "reply", errors)

    indicators = parsed.get("indicators")
    if isinstance(indicators, dict):
        check_fields(indicators, INDICATOR_TYPES, "indicators", errors)

    repeat_pattern = parsed.get("repeat_pattern_indicators")
    if isinstance(repeat_pattern, dict):
        check_fields(repeat_pattern, REPEAT_PATTERN_TYPES, "repeat_pattern_indicators", errors)
        check_enums(repeat_pattern, REPEAT_PATTERN_ENUM_FIELDS, "repeat_pattern_indicators", errors)

    check_scores(parsed, errors)
    check_enums(parsed, TOP_LEVEL_ENUM_FIELDS, "reply", errors)
    return parsed, errors
