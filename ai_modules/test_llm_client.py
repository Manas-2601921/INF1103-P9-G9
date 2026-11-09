"""Scripted offline LLMClient used by the test suite."""

from ai_modules.llm_client import LLMClient


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
