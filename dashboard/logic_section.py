"""The logic manager's triage decision for one incident."""

from dataclasses import dataclass

from dashboard.section_object import SectionObject


@dataclass
class LogicSection(SectionObject):
    """The logic manager's triage decision for one incident."""

    final_queue: str | None = None
    escalation_required: bool | None = None
    recurring: bool | None = None
    duplicate_possible: bool | None = None
    risk_score: int | None = None
    rule_applied: str | None = None
    ai_explanation: str | None = None
    supporting_phrase: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "LogicSection":
        """Build a LogicSection from the record's logic dictionary."""
        return cls(**cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return the logic fields that are set."""
        return self._without_unset()
