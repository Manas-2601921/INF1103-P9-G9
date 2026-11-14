"""Exception signalling missing API credentials.

Lives in its own module so the concrete client that raises it and the
retry wrapper that recognises it can both import it without depending on
each other.
"""


class MissingAPIKeyError(ValueError):
    """Raised when the API credentials are missing from the environment.

    Subclasses ValueError so the AI manager's existing
    ``except ValueError`` handling keeps working, while
    ``RetryableLLMClient`` can recognise it as non-retryable and fail fast
    instead of re-attempting a call that can never succeed.
    """
