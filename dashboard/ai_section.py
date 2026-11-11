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
    marks the manual-review failure stub. The stub carries only
    ``repeat_pattern_indicators`` and ``ai_error`` — ``validate()`` accepts
    it as the alternative valid shape instead of the full analysis schema.
    """

    manager_json: dict = field(default_factory=dict)

    REQUIRED_KEYS: ClassVar[tuple[str, ...]] = (
        "severity", "confidence", "severity_explanation", "hazard_category",
        "incident_type", "indicators", "repeat_pattern_indicators",
        "recommended_immediate_action", "supporting_phrase",
    )
    KNOWN_KEYS: ClassVar[tuple[str, ...]] = (
        *REQUIRED_KEYS, "severity_score", "ai_error",
    )

    # the manual-review failure stub satisfies this alternative contract
    _STUB_REQUIRED_KEYS: ClassVar[tuple[str, ...]] = (
        "repeat_pattern_indicators", "ai_error",
    )

    @classmethod
    def from_dict(cls, data: dict) -> "AISection":
        """Wrap the record's ai dictionary, dropping excess keys."""
        return cls(manager_json=cls._filter_known(data))

    def _required_keys(self) -> tuple[str, ...]:
        """The stub's two keys when ``ai_error`` marks a manual-review
        section, the full analysis schema otherwise."""
        if "ai_error" in self.manager_json:
            return self._STUB_REQUIRED_KEYS
        return self.REQUIRED_KEYS

    def to_dict(self) -> dict:
        """Return a copy of the wrapped ai dictionary."""
        return dict(self.manager_json)
