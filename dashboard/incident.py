"""Incident aggregate and conversions between dictionaries and database rows.

Conversions never add rows to a session or commit. The storage layer owns
transactions and supplies timestamps for newly processed incidents.
"""

from copy import deepcopy
import re

from dashboard.input_section import InputSection
from dashboard.ai_section import AISection
from dashboard.logic_section import LogicSection
from dashboard.models import IncidentModel, IOManagerModel, AIManagerModel, LogicManagerModel


class Incident:
    def __init__(self, input_section=None, ai_section=None, logic_section=None,
                 record_id=None, metadata=None):
        self.input_section = input_section
        self.ai_section = ai_section
        self.logic_section = logic_section
        self.record_id = record_id
        self.metadata = metadata

    @property
    def input_section(self) -> InputSection | None:
        """Return the editable input section."""
        return self._input_section

    @input_section.setter
    def input_section(self, value: InputSection | None):
        if value is not None and not isinstance(value, InputSection):
            raise TypeError("input_section must be an InputSection or None.")
        self._input_section = value

    @property
    def ai_section(self) -> AISection | None:
        """Return the editable AI section."""
        return self._ai_section

    @ai_section.setter
    def ai_section(self, value: AISection | None):
        if value is not None and not isinstance(value, AISection):
            raise TypeError("ai_section must be an AISection or None.")
        self._ai_section = value

    @property
    def logic_section(self) -> LogicSection | None:
        """Return the editable logic section."""
        return self._logic_section

    @logic_section.setter
    def logic_section(self, value: LogicSection | None):
        if value is not None and not isinstance(value, LogicSection):
            raise TypeError("logic_section must be a LogicSection or None.")
        self._logic_section = value

    @property
    def record_id(self) -> str | None:
        return self._record_id

    @record_id.setter
    def record_id(self, value: str | None):
        if value is not None and (
            not isinstance(value, str)
            or re.fullmatch(r"INC-[0-9]+", value) is None
            or int(value[4:]) < 1
        ):
            raise ValueError("record_id must be a positive INC- identifier or None.")
        self._record_id = value

    @property
    def metadata(self) -> dict:
        """Return a copy; assign a dictionary to replace metadata."""
        return deepcopy(self._metadata)

    @metadata.setter
    def metadata(self, value: dict | None):
        if value is not None and not isinstance(value, dict):
            raise TypeError("metadata must be a dictionary.")
        self._metadata = deepcopy(value or {})

    @classmethod
    def from_dict(cls, record):
        """Accept the existing record shape and filter through each section's schema."""
        if not isinstance(record, dict) or any(
            not isinstance(record.get(key), dict) for key in ("input", "ai", "logic")
        ):
            raise ValueError("Incident must contain input, ai, and logic dictionaries.")
        return cls(
            InputSection.from_dict(deepcopy(record["input"])),
            AISection.from_dict(deepcopy(record["ai"])),
            LogicSection.from_dict(deepcopy(record["logic"])),
            record_id=record.get("record_id") or None,
            metadata=record.get("metadata"),
        )

    def to_dict(self):
        """Return the shared record shape using the section serialization rules."""
        return {
            "record_id": self._record_id,
            "input": self._input_section.to_dict() if self._input_section is not None else None,
            "ai": self._ai_section.to_dict() if self._ai_section is not None else None,
            "logic": self._logic_section.to_dict() if self._logic_section is not None else None,
            "metadata": deepcopy(self._metadata),
        }

    def convert_to_db_model(self):
        """Return an unsaved parent model with all three section rows attached."""
        self.validate_complete()
        model = IncidentModel(
            created_at=self._metadata.get("created_at"),
            processed_at=self._metadata.get("processed_at"),
            input_section=IOManagerModel(**self._input_section.to_dict()),
            ai_section=AIManagerModel(**self._ai_section.to_dict()),
            logic_section=LogicManagerModel(**self._logic_section.to_dict()),
        )
        if self._record_id is not None:
            model.id = int(self._record_id[4:])
        return model

    def validate_complete(self):
        """Require each layer to attach its section before persistence."""
        missing = [name for name in ("input_section", "ai_section", "logic_section")
                   if getattr(self, name) is None]
        if missing:
            raise ValueError(f"Incident is incomplete; missing: {', '.join(missing)}.")

    @classmethod
    def from_db_model(cls, model):
        """Read relationships while the caller's database session is active."""
        sections = []
        for row, section_type in (
            (model.input_section, InputSection), (model.ai_section, AISection),
            (model.logic_section, LogicSection),
        ):
            if row is None:
                raise ValueError(f"Incident is missing its {section_type.__name__} row.")
            # Sections wrap manager_json now; the relational tables still have
            # one column per declared manager key. Omit unset SQL defaults so
            # partial AI failure stubs retain their original dictionary shape.
            values = {key: deepcopy(getattr(row, key))
                      for key in section_type.KNOWN_KEYS
                      if getattr(row, key) is not None and getattr(row, key) != {}}
            sections.append(section_type.from_dict(values))
        metadata = {key: getattr(model, key) for key in ("created_at", "processed_at")
                    if getattr(model, key) is not None}
        return cls(*sections, record_id=f"INC-{model.id:04d}" if model.id is not None else None,
                   metadata=metadata)
