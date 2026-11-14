"""Shared parsing for the incident datetime strings stored in records.

Records hold datetimes in two shapes: the CLI pipeline stores
``datetime.isoformat()`` strings ("2026-11-11T09:00:00") while the IO
manager prompts and the AI replies use "%d-%m-%Y %H:%M"
("22-01-2026 13:10"), with "%d-%m-%Y" accepted as a date-only fallback
matching ``LogicManager._parse_date``. Every feature that groups or
filters by time parses through ``IncidentDatetimeParser`` so all layers
handle these shapes identically.

Ownership note: agreed in the team contracts as the shared datetime
utility — the submission pair takes it over if the form needs extra
formats; consumers (search, trends) only call it.
"""

from datetime import datetime


class IncidentDatetimeParser:
    """Parse stored incident datetime values into ``datetime`` instances."""

    # The IO manager's prompt format, kept in one place (mirrors
    # IOManager.is_valid_dt_format) so the CLI and the web tier agree.
    PROMPT_FORMAT = "%d-%m-%Y %H:%M"
    DEFAULT_FORMATS = (PROMPT_FORMAT, "%d-%m-%Y")

    def __init__(self, formats: tuple[str, ...] | None = None):
        self._formats = formats if formats is not None else self.DEFAULT_FORMATS

    def parse(self, value) -> datetime | None:
        """Parse a stored incident datetime string into a ``datetime``.

        Args:
            value: The stored string ("2026-11-11T09:00:00",
                "22-01-2026 13:10", or "22-01-2026"), an already-parsed
                ``datetime``, or anything else (e.g. ``None`` or free text).

        Returns:
            datetime | None: The parsed datetime, the value itself when it is
            already a ``datetime``, or ``None`` when unrecognised.
        """
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in self._formats:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None
