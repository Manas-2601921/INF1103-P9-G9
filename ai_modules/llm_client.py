"""LLM client hierarchy used by the AI manager.

``LLMClient`` is the abstract contract (interface) every backend implements;
the concrete subclasses supply the transport:

- ``ZaiLLMClient``      talks to the Z.ai OpenAI-compatible endpoint.
- ``RetryableLLMClient`` wraps any other client and retries transient failures.
- ``TestLLMClient``     replays scripted replies so tests run fully offline.

``AIManager`` only ever calls the abstract ``complete`` method, so the real
API, the retry wrapper and the offline test client are interchangeable
without any type-specific branching in the calling code.
"""

import os
import time
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from openai import (
    APIError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    UnprocessableEntityError,
)

# Load ZAI_KEY and friends from a local .env file at import time, matching
# the timing the old openai_connector module used.
load_dotenv()

# API errors that can never succeed on retry (invalid key, malformed request),
# RetryableLLMClient raises them immediately instead of wasting attempts
NON_RETRYABLE_ERRORS = (
    AuthenticationError,      # 401: API key is invalid
    PermissionDeniedError,    # 403: key lacks access to the model
    BadRequestError,          # 400: request is malformed
    NotFoundError,            # 404: endpoint or model does not exist
    UnprocessableEntityError, # 422: request failed validation
)


class MissingAPIKeyError(ValueError):
    """Raised when the API credentials are missing from the environment.

    Subclasses ValueError so the AI manager's existing
    ``except ValueError`` handling keeps working, while
    ``RetryableLLMClient`` can recognise it as non-retryable and fail fast
    instead of re-attempting a call that can never succeed.
    """


class LLMClient(ABC):
    """Abstract base class defining the contract for one LLM backend.

    Every backend receives a chat-completions ``messages`` payload and
    returns the raw reply text. Concrete subclasses implement ``complete``
    against a real API, or a scripted test client for offline runs.
    """

    @abstractmethod
    def complete(self, messages: list) -> str:
        """Send one chat-completion request and return the raw reply text.

        Args:
            messages: chat-completions payload, e.g.
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ]

        Returns:
            The raw reply text from the backend.

        Raises:
            ValueError: when the backend cannot produce a usable reply
                (missing credentials, malformed response).
            APIError: when the underlying API raises an error.
        """


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


class RetryableLLMClient(LLMClient):
    """Retry wrapper around any other ``LLMClient``.

    Being itself a ``LLMClient``, it can stand in wherever the wrapped
    client is expected. Transient failures are retried with an increasing
    wait; non-retryable API errors and missing credentials are raised
    immediately instead of consuming attempts.
    """

    def __init__(
        self,
        client: LLMClient,
        max_attempts: int = 3,
        backoff_seconds: float = 5,
    ):
        self._client = client
        self._max_attempts = max_attempts
        # backoff_seconds <= 0 disables the waits, which keeps tests fast
        self._backoff_seconds = backoff_seconds

    def complete(self, messages: list) -> str:
        """Call the wrapped client, retrying transient failures.

        Raises:
            ValueError: If a non-retryable error occurs, or if an API error
                or malformed API response persists after all attempts.
        """
        for attempt_counter in range(self._max_attempts):
            try:
                return self._client.complete(messages)

            except NON_RETRYABLE_ERRORS as e:
                # 4xx errors cannot succeed on retry, raise immediately
                raise ValueError(f"API call failed with a non-retryable error: {e}") from e

            except MissingAPIKeyError as e:
                # A missing key can never succeed on retry, raise immediately
                raise ValueError(f"API call failed with a non-retryable error: {e}") from e

            except (APIError, ValueError) as e:
                if attempt_counter == self._max_attempts - 1:
                    raise ValueError(
                        f"API call failed after {self._max_attempts} attempts: {e}"
                    )
                self._sleep_before_retry(attempt_counter)

                continue

    def _sleep_before_retry(self, attempt_counter: int) -> None:
        """Wait a while before retrying due to possible rate limits,
        increasing the wait each time an error occurs."""
        if self._backoff_seconds <= 0:
            return
        time.sleep(self._backoff_seconds * attempt_counter + 1)


class TestLLMClient(LLMClient):
    """Scripted offline client used by the test suite.

    Replays queued replies and counts the calls, so tests can assert how
    often the AI manager queried the LLM and which prompt it last sent
    without any network or API key.
    """

    DEFAULT_REPLY = "TEST CLIENT ERROR: no scripted AI reply was queued for this test case"

    def __init__(self, replies: list | None = None):
        self._replies = list(replies or [])
        self.calls = 0
        self.last_messages = None

    def queue(self, *replies: str) -> None:
        """Queue the replies to return and reset the call counter."""
        self._replies = list(replies)
        self.calls = 0

    def complete(self, messages: list) -> str:
        self.calls += 1
        self.last_messages = messages
        if self._replies:
            return self._replies.pop(0)
        return self.DEFAULT_REPLY
