"""The logic manager's triage decision for one incident."""

from dataclasses import dataclass, field
from typing import ClassVar

from dashboard.section_object import SectionObject


@dataclass
class LogicSection(SectionObject):
    """The logic manager's triage decision for one incident.

    Wraps the record's ``logic`` dictionary: final_queue,
    escalation_required, recurring, duplicate_possible, risk_score,
    rule_applied, ai_explanation and supporting_phrase. All eight keys are
    required and known; ``False`` and ``0`` values (e.g. risk_score 0) are
    real values, not blanks.
    """

    manager_json: dict = field(default_factory=dict)

    REQUIRED_KEYS: ClassVar[tuple[str, ...]] = (
        "final_queue", "escalation_required", "recurring", "duplicate_possible",
        "risk_score", "rule_applied", "ai_explanation", "supporting_phrase",
    )
    KNOWN_KEYS: ClassVar[tuple[str, ...]] = REQUIRED_KEYS

    @classmethod
    def from_dict(cls, data: dict) -> "LogicSection":
        """Wrap the record's logic dictionary, dropping excess keys."""
        return cls(manager_json=cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped logic dictionary."""
        return dict(self.manager_json)
