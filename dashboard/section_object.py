"""Abstract interface enforced on every manager section object.

Each manager creates its own section object (``InputSection`` from the IO
layer, ``AISection`` from the AI analysis, ``LogicSection`` from the triage
decision) and the ``Incident`` aggregate composes the three. Every section
is a thin wrapper around the exact dictionary its manager produced, so the
dict-based collaborators (the logic rules, the storage and the legacy
record format) keep speaking plain dictionaries.
"""

from abc import ABC, abstractmethod


class SectionObject(ABC):
    """Abstract interface enforced on every manager section object.

    A concrete section stores the dictionary it receives in its
    ``manager_json`` attribute instead of unpacking it into fields.
    ``from_dict`` wraps a record dictionary into a section object and
    ``to_dict`` unwraps the stored dictionary again, so a section converts
    to and from the dictionary shape its manager already produces with no
    field mapping in between (missing keys stay missing, extra keys are
    preserved). Both operations stay abstract: the interface enforces
    creation as well as storage conversion on every section, and the ABC
    itself cannot be instantiated. Copies are shallow: mutating a returned
    dictionary never changes the section's own top-level entries, but
    nested dictionaries are shared.
    """

    @abstractmethod
    def to_dict(self) -> dict:
        """Return a copy of the wrapped manager dictionary."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "SectionObject":
        """Wrap a manager dictionary into a section object, tolerating missing keys."""
