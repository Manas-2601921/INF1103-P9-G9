from openai import OpenAI, APIError
from dotenv import load_dotenv
import os
import time

load_dotenv()


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
        ValueError: If the API returns a malformed response.
        APIError: If the OpenAI-compatible API raises an error.
    """

    api_key = os.getenv("ZAI_KEY")

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

    Args:
        llm_prompt: Prompt sent to the LLM API.
        max_attempt: Maximum number of attempts.

    Returns:
        LLM response

    Raises:
        APIError: If an API error persists after all retry attempts.
        ValueError: If a malformed API response persists after all attempts.
    """

    for attempt_counter in range(max_attempt):
        try:
            return zai_connector(llm_prompt)

        except (APIError, ValueError) as e:
            if attempt_counter == max_attempt - 1:
                raise ValueError(
                    f"API call failed after {max_attempt} attempts: {e}"
                )
            time.sleep(5 * attempt_counter + 1) # Wait a while before retrying due to possible rate limits, increase wait time each time error occurs

            continue