"""Abstract interface enforced on every manager section object.

Each manager creates its own section object (``InputSection`` from the IO
layer, ``AISection`` from the AI analysis, ``LogicSection`` from the triage
decision) and the ``Incident`` aggregate composes the three. Every section
wraps the dictionary its manager produced in ``manager_json``: declared
``KNOWN_KEYS`` survive the round trip verbatim and excess keys are dropped
at creation. Missing or blank values are the managers' concern — the
sections never reject what they are given.
"""

from abc import ABC, abstractmethod
from typing import ClassVar


class SectionObject(ABC):
    """Abstract interface enforced on every manager section object.

    A concrete section stores the dictionary it receives in its
    ``manager_json`` attribute instead of unpacking it into fields.
    ``from_dict`` keeps only the declared ``KNOWN_KEYS`` — excess keys are
    dropped and missing keys are tolerated, so creation never raises — and
    ``to_dict`` unwraps the stored dictionary again, so a section converts
    to and from the dictionary shape its manager already produces with no
    field mapping in between. Both conversions stay abstract: the interface
    enforces creation as well as storage conversion on every section, and
    the ABC itself cannot be instantiated. Copies are shallow: mutating a
    returned dictionary never changes the section's own top-level entries,
    but nested dictionaries are shared.
    """

    # The declared schema of the manager dictionary. ClassVar so the
    # dataclass subclasses do not turn these into manager_json fields.
    KNOWN_KEYS: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def to_dict(self) -> dict:
        """Return a copy of the wrapped manager dictionary."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "SectionObject":
        """Wrap a manager dictionary into a section object, dropping excess keys."""

    @classmethod
    def _filter_known(cls, data: dict) -> dict:
        """Keep only the entries whose keys are declared in ``KNOWN_KEYS``.

        Args:
            data: A manager dictionary (or None) that may contain extra or
                missing keys, e.g. the manual-review stub or a partial
                legacy seed.

        Returns:
            dict: Only the declared entries. Excess keys are dropped and
            missing keys are simply absent — creation never raises.
        """
        known = set(cls.KNOWN_KEYS)
        return {key: value for key, value in (data or {}).items() if key in known}
