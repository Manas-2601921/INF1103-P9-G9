"""Value object representing a single bucket in a trend time series."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendPoint:
    """One labelled bucket of a time series (e.g. one day's incident count)."""

    label: str
    count: int
