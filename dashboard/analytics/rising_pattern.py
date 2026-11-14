"""Value object representing a week-over-week rising hazard pattern."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RisingPattern:
    """A location and hazard category whose recent week outnumbers the prior one.

    These mark "possible incoming incidents": the same hazard is now
    happening more often than it did the week before.
    """

    location: str
    hazard_category: str
    recent_count: int
    prior_count: int
