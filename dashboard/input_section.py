"""The incident report as submitted through the IO layer."""

from dataclasses import dataclass

from dashboard.section_object import SectionObject


@dataclass
class InputSection(SectionObject):
    """The incident report as submitted through the IO layer."""

    incident_name: str = ""
    description: str = ""
    location: str = ""
    reporter_role: str = ""
    incident_datetime: str = ""
    injury_reported: bool = False
    immediate_action: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "InputSection":
        """Build an InputSection from the record's input dictionary."""
        return cls(**cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return all seven input fields (defaults included)."""
        return self._without_unset()
