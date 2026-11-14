"""Value object representing a recurring location and hazard hotspot."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Hotspot:
    """A location and hazard category repeatedly hit inside a time window."""

    location: str
    hazard_category: str
    count: int
    last_seen: str
