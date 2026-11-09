"""Concrete LLMClient for the Z.ai OpenAI-compatible endpoint."""

import os

from dotenv import load_dotenv
from openai import OpenAI

from ai_modules.llm_client import LLMClient
from ai_modules.missing_api_key_error import MissingAPIKeyError

# Load ZAI_KEY and friends from a local .env file at import time, matching
# the timing the old openai_connector module used.
load_dotenv()


class ZaiLLMClient(LLMClient):
    """Concrete client for the Z.ai OpenAI-compatible endpoint.

    Utilizes the Z.ai endpoint to query the GLM model. The API key is read
    at call time (or injected for testing) so a missing key behaves exactly
    like before: the failure surfaces when the AI is actually used, not at
    application start.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.z.ai/api/coding/paas/v4/",
        model: str = "glm-5.3-flash",
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def complete(self, messages: list) -> str:
        """Send one analysis prompt to the Z.ai endpoint.

        Raises:
            MissingAPIKeyError: If ZAI_KEY is missing.
            ValueError: If the API returns a malformed response.
            APIError: If the OpenAI-compatible API raises an error.
        """
        api_key = self._api_key or os.getenv("ZAI_KEY")
        if not api_key:
            raise MissingAPIKeyError("ZAI_KEY is not set, add it to the .env file")

        client = OpenAI(
            api_key=api_key,
            base_url=self._base_url,
            max_retries=0,
        )

        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )

        # Validate API response
        if not response.choices:
            raise ValueError("Malformed response was returned from API")

        if response.choices[0].message.content is None:
            raise ValueError("Malformed response was returned from API")

        return response.choices[0].message.content
