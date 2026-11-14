"""Abstract contract (interface) for one LLM backend.

Every backend - the real Z.ai API, the retrying wrapper or the offline
test client - implements this interface, so ``AIManager`` only ever calls
the abstract ``complete`` method and never depends on a concrete client.
"""

from abc import ABC, abstractmethod


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
