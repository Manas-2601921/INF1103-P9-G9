"""Prompt construction for the AI manager.

``PromptBuilder`` encapsulates the schema contract sent to the model (the
system prompt) and builds the chat-completions payloads for a first-pass
analysis and for a retry after a rejected reply.
"""


class PromptBuilder:
    """Build the chat-completions payloads for one incident analysis.

    The system prompt is the schema contract the model must reply with; the
    response validator mirrors the same schema, so both classes must stay
    in sync when a field is added.
    """

    SYSTEM_PROMPT = """You are the classification engine of a workplace incident triage system for
small and medium-sized companies in Singapore (Workplace Safety and Health
context). You analyse one incident report at a time. You suggest an initial
classification and cite the evidence; a rule engine makes the final decision.

Reply with ONE valid JSON object and nothing else: no markdown fences, no
commentary before or after the object. Use exactly this schema:

{
    "severity": 0.0,
    "confidence": 0.0,
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
- "severity": a FLOAT from 0.0 to 1.0 representing the potential severity of
  the incident or hazard. Do not return a string or categorical label.
  Use the following guidance:
    - 0.00-0.30: minor, well-controlled issue where injury or serious harm is
      unlikely.
    - 0.31-0.60: meaningful hazard requiring attention, but serious harm is
      unlikely under the reported circumstances.
    - 0.61-0.80: significant hazard where injury or serious harm was a realistic
      possibility.
    - 0.81-1.00: very serious incident or hazard involving actual injury,
      immediate danger, or a realistic possibility of severe harm.
  Choose the value based only on facts contained in the report.
- "confidence": a FLOAT from 0.0 to 1.0 showing how sure you are of the
  classification. Do not confuse confidence with severity.
- "severity_explanation": one or two sentences citing the evidence that
  justifies the severity score.
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

    def build_user_prompt(self, incident_json: dict) -> str:
        """Render the incident fields as a labelled list for the model.

        Args:
            incident_json: the input section of the shared record.

        Returns:
            A plain-text incident brief ending with the reply instruction.
            Missing fields are rendered as "not provided" so a partial record
            still produces a usable prompt instead of a crash.
        """

        lines = ["Incident report to analyse:"]
        for key in incident_json.keys():
            lines.append(str({key: incident_json[key]})) # Construct user prompt using incident_json and combined them into a string
        lines.append("Analyse this incident and reply with the JSON object only.")
        return "\n".join(lines)

    def build_analysis_messages(self, user_prompt: str) -> list[dict]:
        """Build the chat messages for a first-pass incident analysis.

        Args:
            user_prompt: from the build_user_prompt method

        Returns:
            A ``messages`` payload in chat-completions format: one system
            message with the schema contract, one user message with the report.
        """
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def build_retry_messages(
        self, incident_json: dict, previous_reply: str, errors: list[str]
    ) -> list[dict]:
        """Build chat messages asking the model to fix a rejected reply.

        Used by ``AIManager.analyze`` when validation fails: the exact rule
        violations and the previous reply are shown so the model can correct
        itself instead of guessing what went wrong.

        Args:
            incident_json: the ``input`` section of the shared record.
            previous_reply: the raw reply text that failed validation.
            errors: the rule violations reported by the response validator.

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
            f"{self.build_user_prompt(incident_json)}"
        )
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
