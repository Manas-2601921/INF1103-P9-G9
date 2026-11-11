"""The incident report as submitted through the IO layer."""

from dataclasses import dataclass, field

from dashboard.section_object import SectionObject


@dataclass
class InputSection(SectionObject):
    """The incident report as submitted through the IO layer.

    Wraps the record's ``input`` dictionary: incident_name, description,
    location, reporter_role, incident_datetime, injury_reported and
    immediate_action.
    """

    manager_json: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "InputSection":
        """Wrap the record's input dictionary into an InputSection."""
        return cls(manager_json=dict(data or {}))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped input dictionary."""
        return dict(self.manager_json)
