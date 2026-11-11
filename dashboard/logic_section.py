"""The logic manager's triage decision for one incident."""

from dataclasses import dataclass, field

from dashboard.section_object import SectionObject


@dataclass
class LogicSection(SectionObject):
    """The logic manager's triage decision for one incident.

    Wraps the record's ``logic`` dictionary: final_queue,
    escalation_required, recurring, duplicate_possible, risk_score,
    rule_applied, ai_explanation and supporting_phrase.
    """

    manager_json: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "LogicSection":
        """Wrap the record's logic dictionary into a LogicSection."""
        return cls(manager_json=dict(data or {}))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped logic dictionary."""
        return dict(self.manager_json)
