"""Shared parsing for the incident datetime strings stored in records.

Records hold datetimes in two shapes: the CLI pipeline stores
``datetime.isoformat()`` strings ("2026-11-11T09:00:00") while the IO
manager prompts and the AI replies use "%d-%m-%Y %H:%M"
("22-01-2026 13:10"). Every feature that groups or filters by time parses
through this one helper so both shapes are handled identically.

Ownership note: agreed in the team contracts as the shared datetime
utility — the submission pair takes it over if the form needs extra
formats; consumers (search, trends) only call it.
"""

from datetime import datetime

# The IO manager's prompt format, kept in one place (mirrors
# IOManager.is_valid_dt_format) so the CLI and the web tier agree.
PROMPT_FORMAT = "%d-%m-%Y %H:%M"


def parse_incident_datetime(value):
    """Parse a stored incident datetime string into a datetime.

    Args:
        value: The stored string ("2026-11-11T09:00:00" or
            "22-01-2026 13:10"), an already-parsed datetime, or anything
            else (e.g. None or free text).

    Returns:
        datetime | None: The parsed datetime, the value itself when it is
        already a datetime, or None when the shape is unrecognised.
        Callers decide how to skip unparseable values.
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
    try:
        return datetime.strptime(text, PROMPT_FORMAT)
    except ValueError:
        return None
