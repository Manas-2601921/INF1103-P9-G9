"""Retry wrapper for any LLMClient (decorator pattern)."""

import time

from openai import (
    APIError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    UnprocessableEntityError,
)

from ai_modules.llm_client import LLMClient
from ai_modules.missing_api_key_error import MissingAPIKeyError

# API errors that can never succeed on retry (invalid key, malformed request),
# RetryableLLMClient raises them immediately instead of wasting attempts
NON_RETRYABLE_ERRORS = (
    AuthenticationError,      # 401: API key is invalid
    PermissionDeniedError,    # 403: key lacks access to the model
    BadRequestError,          # 400: request is malformed
    NotFoundError,            # 404: endpoint or model does not exist
    UnprocessableEntityError, # 422: request failed validation
)


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
