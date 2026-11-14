"""The incident report as submitted through the IO layer."""

from dataclasses import dataclass, field
from typing import ClassVar

from dashboard.section_object import SectionObject


@dataclass
class InputSection(SectionObject):
    """The incident report as submitted through the IO layer.

    Wraps the record's ``input`` dictionary: incident_name, description,
    location, reporter_role, incident_datetime, injury_reported and
    immediate_action. All seven keys are known, so excess keys are dropped
    while a partial dictionary (a legacy seed) still loads as-is.
    """

    manager_json: dict = field(default_factory=dict)

    KNOWN_KEYS: ClassVar[tuple[str, ...]] = (
        "incident_name", "description", "location", "reporter_role",
        "incident_datetime", "injury_reported", "immediate_action",
    )

    @classmethod
    def from_dict(cls, data: dict) -> "InputSection":
        """Wrap the record's input dictionary, dropping excess keys."""
        return cls(manager_json=cls._filter_known(data))

    def to_dict(self) -> dict:
        """Return a copy of the wrapped input dictionary."""
        return dict(self.manager_json)
