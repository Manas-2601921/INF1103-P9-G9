"""The AI manager's analysis of one incident."""

from dataclasses import dataclass, field

from dashboard.section_object import SectionObject


@dataclass
class AISection(SectionObject):
    """The AI manager's analysis of one incident.

    Wraps the record's ``ai`` dictionary: severity, confidence,
    severity_explanation, hazard_category, incident_type, indicators,
    repeat_pattern_indicators, recommended_immediate_action and
    supporting_phrase. The AI manager adds the banded severity plus the raw
    ``severity_score``, and the manual-review failure stub carries only
    ``repeat_pattern_indicators`` and ``ai_error`` — storing the dictionary
    verbatim keeps a stub serialising to exactly the keys it holds.
    """

    manager_json: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "AISection":
        """Wrap the record's ai dictionary into an AISection."""
        return cls(manager_json=dict(data or {}))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped ai dictionary."""
        return dict(self.manager_json)
