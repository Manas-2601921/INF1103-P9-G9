"""Abstract interface enforced on every manager section object.

Each manager creates its own section object (``InputSection`` from the IO
layer, ``AISection`` from the AI analysis, ``LogicSection`` from the triage
decision) and the ``Incident`` aggregate composes the three. Every section
wraps the dictionary its manager produced in ``manager_json``: declared
``KNOWN_KEYS`` survive the round trip verbatim, excess keys are dropped at
creation, and ``validate()`` reports missing or blank required keys.
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
    field mapping in between. ``validate()`` is the on-demand check pages
    and managers can run before trusting a section: it reports required
    keys that are missing or blank, plus any excess key that reached the
    section without passing through ``from_dict``. Both conversions stay
    abstract: the interface enforces creation as well as storage conversion
    on every section, and the ABC itself cannot be instantiated. Copies are
    shallow: mutating a returned dictionary never changes the section's own
    top-level entries, but nested dictionaries are shared.
    """

    # The declared schema of the manager dictionary. ClassVar so the
    # dataclass subclasses do not turn these into manager_json fields.
    REQUIRED_KEYS: ClassVar[tuple[str, ...]] = ()
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

    def validate(self) -> list[str]:
        """Check the wrapped dictionary against the declared schema.

        Returns:
            list[str]: One message per required key that is missing or
            blank, plus one message listing any excess keys that reached
            the section without passing through ``from_dict``. An empty
            list means the section is valid.
        """
        problems = [
            f"required key '{key}' is missing or blank"
            for key in self._required_keys()
            if key not in self.manager_json or self._is_blank(self.manager_json[key])
        ]
        excess = sorted(set(self.manager_json) - set(self.KNOWN_KEYS))
        if excess:
            problems.append(f"unexpected key(s): {', '.join(excess)}")
        return problems

    def _required_keys(self) -> tuple[str, ...]:
        """Keys that must be present and non-blank. Sections may override
        this hook — AISection accepts the manual-review stub as an
        alternative valid shape instead of the full analysis schema."""
        return self.REQUIRED_KEYS

    @staticmethod
    def _is_blank(value) -> bool:
        """True for None, empty or whitespace-only strings, and empty
        dictionaries; ``False`` and ``0`` are real values, not blanks."""
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, dict):
            return not value
        return False
