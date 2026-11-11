"""Abstract interface enforced on every manager section object.

Each manager creates its own section object (``InputSection`` from the IO
layer, ``AISection`` from the AI analysis, ``LogicSection`` from the triage
decision); the ``Incident`` aggregate composes the three, and ``to_dict()``
converts a section back into the nested-record dictionary shape the
database and the legacy consumers speak. The ``SectionObject`` ABC is the
contract that enforces both conversions on every section.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, fields


class SectionObject(ABC):
    """Abstract interface enforced on every manager section object.

    Two operations are enforced so the interface covers creation as well as
    storage conversion: ``from_dict`` builds a section from a record
    dictionary (tolerating missing keys), and ``to_dict`` converts it back
    without unset (``None``) fields. Shared concrete behaviour lives on the
    ABC itself — an ABC may define behaviour as well as abstract operations.
    """

    @abstractmethod
    def to_dict(self) -> dict:
        """Return the section as a dictionary without unset fields."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "SectionObject":
        """Build a section object from a dictionary, tolerating missing keys."""

    @classmethod
    def _filter_known(cls, data: dict) -> dict:
        """Keep only the entries whose key names a field of this section.

        Args:
            data: A record dictionary (or None) that may contain extra or
                missing keys, e.g. partial history seeds.

        Returns:
            dict: Only the entries matching this section's dataclass fields.
        """
        known = {info.name for info in fields(cls)}
        return {key: value for key, value in (data or {}).items() if key in known}

    def _without_unset(self) -> dict:
        """Return every dataclass field as a dictionary, minus unset values.

        ``None`` fields and empty dictionary collections count as unset and
        are dropped, so a manual-review stub serialises to exactly the keys
        it holds — while empty strings and ``False``/``0`` values survive.
        Only usable on the dataclass subclasses (the ABC itself is not a
        dataclass and is never instantiated).
        """
        return {
            key: value
            for key, value in asdict(self).items()
            if value is not None and value != {}
        }
