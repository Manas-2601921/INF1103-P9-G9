from openai import (
    OpenAI,
    APIError,
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
    NotFoundError,
    UnprocessableEntityError,
)
from dotenv import load_dotenv
import os
import time

load_dotenv()

# API errors that can never succeed on retry (invalid key, malformed request),
# retry_api_call raises them immediately instead of wasting attempts
NON_RETRYABLE_ERRORS = (
    AuthenticationError,      # 401: API key is invalid
    PermissionDeniedError,    # 403: key lacks access to the model
    BadRequestError,          # 400: request is malformed
    NotFoundError,            # 404: endpoint or model does not exist
    UnprocessableEntityError, # 422: request failed validation
)


def zai_connector(prompt: list) -> str:
    """
    Utilize Z.ai OpenAI-compatible endpoint to query the GLM 5.3 Flash model.

    Args:
        prompt: User and system prompt in the format:
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

    Returns:
        LLM response

    Raises:
        ValueError: If ZAI_KEY is missing or the API returns a malformed response.
        APIError: If the OpenAI-compatible API raises an error.
    """

    api_key = os.getenv("ZAI_KEY")
    if not api_key:
        raise ValueError("ZAI_KEY is not set, add it to the .env file")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.z.ai/api/coding/paas/v4/",
        max_retries=0
    )

    response = client.chat.completions.create(
        model="glm-5.3-flash",
        messages=prompt
    )

    # Validate API response
    if not response.choices:
        raise ValueError("Malformed response was returned from API")

    if response.choices[0].message.content is None:
        raise ValueError("Malformed response was returned from API")

    return response.choices[0].message.content


def retry_api_call(llm_prompt: list, max_attempt: int) -> str:
    """
    Retry the LLM API call for a defined maximum number of attempts
    before throwing an error.

    Non-retryable API errors (invalid key, malformed request, missing
    endpoint) are raised immediately instead of consuming retry attempts.

    Args:
        llm_prompt: Prompt sent to the LLM API.
        max_attempt: Maximum number of attempts.

    Returns:
        LLM response

    Raises:
        ValueError: If ZAI_KEY is missing, if a non-retryable API error
            occurs, or if an API error or malformed API response persists
            after all attempts.
    """

    if not os.getenv("ZAI_KEY"):
        raise ValueError("ZAI_KEY is not set, add it to the .env file")

    for attempt_counter in range(max_attempt):
        try:
            return zai_connector(llm_prompt)

        except NON_RETRYABLE_ERRORS as e:
            # 4xx errors cannot succeed on retry, raise immediately
            raise ValueError(f"API call failed with a non-retryable error: {e}") from e

        except (APIError, ValueError) as e:
            if attempt_counter == max_attempt - 1:
                raise ValueError(
                    f"API call failed after {max_attempt} attempts: {e}"
                )
            time.sleep(5 * attempt_counter + 1) # Wait a while before retrying due to possible rate limits, increase wait time each time error occurs

            continue