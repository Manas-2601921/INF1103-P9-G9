"""The AI manager's analysis of one incident."""

from dataclasses import dataclass, field
from typing import ClassVar

from dashboard.section_object import SectionObject


@dataclass
class AISection(SectionObject):
    """The AI manager's analysis of one incident.

    Wraps the record's ``ai`` dictionary: severity, confidence,
    severity_explanation, hazard_category, incident_type, indicators,
    repeat_pattern_indicators, recommended_immediate_action and
    supporting_phrase, plus the optional ``severity_score`` the AI manager
    adds alongside the banded severity and the optional ``ai_error`` that
    marks the manual-review failure stub. Storing the filtered dictionary
    verbatim keeps a stub serialising to exactly the keys it holds.
    """

    manager_json: dict = field(default_factory=dict)

    KNOWN_KEYS: ClassVar[tuple[str, ...]] = (
        "severity", "confidence", "severity_explanation", "hazard_category",
        "incident_type", "indicators", "repeat_pattern_indicators",
        "recommended_immediate_action", "supporting_phrase",
        "severity_score", "ai_error",
    )

    @classmethod
    def from_dict(cls, data: dict) -> "AISection":
        """Wrap the record's ai dictionary, dropping excess keys."""
        return cls(manager_json=cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped ai dictionary."""
        return dict(self.manager_json)
