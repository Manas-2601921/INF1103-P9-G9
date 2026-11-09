"""AI manager for the Workplace Incident Triage Assistant.

``AIManager`` is the orchestrator of the AI stack: it validates the shared
record from the IO manager layer, builds the analysis prompt, queries the
LLM through the ``LLMClient`` abstraction and validates the reply against
the schema contract, reprompting the model with the exact violations until
the reply passes or the attempt limit is reached.

Its collaborators are composed in ``__init__``:

- ``PromptBuilder``      renders the incident and builds the chat prompts
- ``ResponseValidator``  checks every reply against the JSON schema
- ``LLMClient``          the transport (Z.ai API wrapped in retries, or an
                         injected test client for offline runs)
"""

from ai_modules.llm_client import LLMClient, RetryableLLMClient, ZaiLLMClient
from ai_modules.prompt_builder import PromptBuilder
from ai_modules.response_validator import ResponseValidator

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


class AIManager:
    """Analyse incident reports with the AI and validate its replies.

    The manager owns its prompt builder and response validator (created in
    ``__init__``), while the LLM client is supplied from outside so tests
    can inject a ``TestLLMClient`` and alternative backends can be added
    without touching this class. Whatever client is passed, it is wrapped
    in a ``RetryableLLMClient`` so transient API failures are retried.
    """

    # Fields the incident input section must contain for an analysis to run
    _REQUIRED_INPUT_FIELDS = (
        "description", "location", "reporter_role",
        "incident_datetime", "injury_reported", "immediate_action",
    )

    def __init__(
        self,
        client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        validator: ResponseValidator | None = None,
        max_validation_attempts: int = 3,
        max_api_attempts: int = 3,
        backoff_seconds: float = 5,
    ):
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._validator = validator or ResponseValidator()
        base_client = client or ZaiLLMClient()
        self._client = RetryableLLMClient(
            base_client,
            max_attempts=max_api_attempts,
            backoff_seconds=backoff_seconds,
        )
        self._max_validation_attempts = max_validation_attempts

    def analyze(self, record_json: dict) -> tuple[bool, dict] | tuple[None, str]:
        """Analyse one incident report with the AI and return its classified result.

        Validates the shared record and its incident fields, builds the analysis
        prompt, then queries the LLM. The reply is checked against the JSON
        schema in the system prompt; when it breaks the rules the AI is
        reprompted with the exact violations, up to the configured attempt
        limit.

        Args:
            record_json: the shared record from the IO manager layer. Must be a
                dictionary with an "input" section containing all the required
                incident fields (description, location, reporter_role,
                incident_datetime, injury_reported, immediate_action).

        Returns:
            (True, parsed_output) when the AI reply passes schema validation,
            where parsed_output is the classified analysis dict. Otherwise
            (None, message) explaining the failure: an invalid record or
            incident json, a malformed API response, or schema validation still
            failing after the configured attempts.
        """
        try:
            incident_json = self._validate_record_json(record_json)
            incident_json = self._validate_incident_json(incident_json)
        except (TypeError, KeyError) as exc:
            return None, f"Invalid record or incident json input: {exc}"

        user_prompt = self._prompt_builder.build_user_prompt(incident_json)
        llm_prompt = self._prompt_builder.build_analysis_messages(user_prompt)

        # Validate the reply and reprompt the AI with the schema violations
        # when it fails, up to the configured attempt limit
        for attempt in range(self._max_validation_attempts):
            try:
                llm_response = self._client.complete(llm_prompt)
            except ValueError as e:
                return None, f"Malformed API response was returned: {e}"

            parsed_output, validation_errors = self._validator.validate(llm_response)
            if not validation_errors:
                return True, parsed_output
            llm_prompt = self._prompt_builder.build_retry_messages(
                incident_json, llm_response, validation_errors
            )

        return None, (
            f"AI output failed schema validation after "
            f"{self._max_validation_attempts} attempts: {validation_errors}"
        )

    def _validate_record_json(self, record_json: dict) -> dict:
        """Validate the record_json received from the IO manager layer is a dictionary and it contains the incident_json inside the input field

        Args:
            record_json: the shared record

        Returns:
            The incident_json contained within the input section for the shared record. Returns an error if the shared record is the wrong data type or input field is missing
        """

        if isinstance(record_json, dict) == False:
            # If record_json from io manager is not a dictionary throw error
            raise TypeError(f"record_json is not a dictionary got {type(record_json).__name__} instead")

        try:
            incident_json = record_json["input"]
        except KeyError:
            raise KeyError("record_json input section is missing or has empty fields")
        return incident_json

    def _validate_incident_json(self, incident_json: dict) -> dict:
        """Validates the incident json inside the record json received from the IO manager layer, ensure that the input is in a dictionary format and all required fields are present

        Args:
            incident_json: the input section for the shared record

        Returns:
            The same incident_json is expected however if the json is not a dictionary or contains missing fields
            the function will throw an error
        """
        if isinstance(incident_json, dict) == False:
            # If incident_json from io manager is not a dictionary throw error
            raise TypeError(f"incident_json is not a dictionary got {type(incident_json).__name__} instead")
        missing_key = []
        for key in self._REQUIRED_INPUT_FIELDS:
            if key not in incident_json:
                # If incident_json does not contain all required fields, throw key error
                missing_key.append(key)
        if missing_key:
            raise KeyError(f"incident_json is missing or has empty fields for the {missing_key} required fields")
        return incident_json


if __name__ == "__main__":
    print(AIManager().analyze(sample_record_json))
