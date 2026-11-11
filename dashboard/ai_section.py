"""The AI manager's analysis of one incident."""

from dataclasses import dataclass, field

from dashboard.section_object import SectionObject


@dataclass
class AISection(SectionObject):
    """The AI manager's analysis of one incident.

    Tolerates partial data: the manual-review failure stub carries only
    ``repeat_pattern_indicators`` and ``ai_error``, and ``to_dict`` drops
    unset fields so a stub serialises to exactly what it holds.
    """

    severity: float | str | None = None
    confidence: float | None = None
    severity_explanation: str | None = None
    hazard_category: str | None = None
    incident_type: str | None = None
    indicators: dict = field(default_factory=dict)
    repeat_pattern_indicators: dict = field(default_factory=dict)
    recommended_immediate_action: str | None = None
    supporting_phrase: str | None = None
    severity_score: float | None = None
    ai_error: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "AISection":
        """Build an AISection from the record's ai dictionary."""
        return cls(**cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return the AI fields that are set."""
        return self._without_unset()
