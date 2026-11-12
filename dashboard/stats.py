"""Trend statistics for the analytics dashboard, computed in Python.

``StatsService`` aggregates over the incidents the data manager loads —
no extra SQL: the storage layer stays query-shaped, the analytics layer
stays a pure aggregation service with the data manager injected. Every
method tolerates partial records (a missing AI section or an unparseable
datetime skips that incident from that statistic) so legacy rows and
manual-review stubs never crash the dashboard.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from dashboard.datetime_utils import parse_incident_datetime
from dashboard.incident import Incident


@dataclass(frozen=True)
class TrendPoint:
    """One labelled bucket of a time series (e.g. one day's incident count)."""

    label: str
    count: int


@dataclass(frozen=True)
class Hotspot:
    """A location and hazard category repeatedly hit inside a time window."""

    location: str
    hazard_category: str
    count: int
    last_seen: str


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


class StatsService:
    """Aggregate stored incidents into the dashboard's trend statistics.

    The data manager is injected, so any storage backend (or a test double
    over a temporary database) can feed the same statistics.
    """

    # The severity bands the pipeline assigns; thresholds mirror the
    # CLI pipeline's banding (>0.7 high, >=0.4 medium, else low).
    SEVERITY_BANDS = ("low", "medium", "high")

    def __init__(self, data_manager):
        self._data_manager = data_manager

    # ------------------------------------------------------------------
    # Distribution statistics
    # ------------------------------------------------------------------

    def incidents_by_severity(self) -> dict[str, int]:
        """Count incidents per severity band, all three bands always present.

        Numeric severities (raw scores or legacy rows) are banded with the
        pipeline thresholds; already-banded strings count as-is; records
        without a usable severity are skipped.
        """
        counts = {band: 0 for band in self.SEVERITY_BANDS}
        for incident in self._data_manager.load():
            band = self._severity_band(incident)
            if band is not None:
                counts[band] += 1
        return counts

    def incidents_by_hazard_category(self) -> dict[str, int]:
        """Count incidents per AI hazard category, highest count first."""
        counts: dict[str, int] = defaultdict(int)
        for incident in self._data_manager.load():
            category = self._ai_field(incident, "hazard_category")
            if category:
                counts[category] += 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def incidents_by_queue(self) -> dict[str, int]:
        """Count incidents per final triage queue, highest count first."""
        counts: dict[str, int] = defaultdict(int)
        for incident in self._data_manager.load():
            queue = self._logic_field(incident, "final_queue")
            if queue:
                counts[queue] += 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    # ------------------------------------------------------------------
    # Time-window statistics
    # ------------------------------------------------------------------

    def incidents_per_day(self, days: int = 14, today: date | None = None) -> list[TrendPoint]:
        """Count incidents for each of the last ``days`` days, zero-filled.

        The series always contains one point per day (including empty days)
        so the chart shows quiet periods instead of skipping them.
        """
        today = today or date.today()
        first_day = today - timedelta(days=days - 1)
        daily: dict[date, int] = {first_day + timedelta(days=i): 0 for i in range(days)}
        for incident in self._data_manager.load():
            occurred = self._incident_date(incident)
            if occurred in daily:
                daily[occurred] += 1
        return [TrendPoint(day.isoformat(), daily[day]) for day in daily]

    def recurrence_hotspots(self, window_days: int = 30, min_count: int = 2,
                            today: date | None = None) -> list[Hotspot]:
        """Location + hazard pairs hit at least ``min_count`` times in the window.

        This is the stored-data view of the logic manager's recurrence rule:
        the same hazard repeating at the same location inside the window.
        """
        today = today or date.today()
        window_start = today - timedelta(days=window_days - 1)
        groups: dict[tuple[str, str], list[date]] = defaultdict(list)
        for incident in self._data_manager.load():
            occurred = self._incident_date(incident)
            location = self._input_field(incident, "location")
            category = self._ai_field(incident, "hazard_category")
            if occurred and occurred >= window_start and location and category:
                groups[(location, category)].append(occurred)
        hotspots = [
            Hotspot(location, category, len(dates), max(dates).isoformat())
            for (location, category), dates in groups.items()
            if len(dates) >= min_count
        ]
        hotspots.sort(key=lambda hotspot: (-hotspot.count, hotspot.last_seen))
        return hotspots

    def rising_patterns(self, recent_days: int = 7, today: date | None = None) -> list[RisingPattern]:
        """Location + hazard pairs whose last week outnumbers the prior week.

        The recent window is the ``recent_days`` days ending today; the prior
        window is the equally sized stretch right before it. A pair counts as
        rising when it happened at least twice this week (a single new report
        is not a trend) and more often than in the prior window.
        """
        today = today or date.today()
        recent_start = today - timedelta(days=recent_days - 1)
        prior_start = recent_start - timedelta(days=recent_days)
        recent: dict[tuple[str, str], int] = defaultdict(int)
        prior: dict[tuple[str, str], int] = defaultdict(int)
        for incident in self._data_manager.load():
            occurred = self._incident_date(incident)
            location = self._input_field(incident, "location")
            category = self._ai_field(incident, "hazard_category")
            if not (occurred and location and category):
                continue
            pair = (location, category)
            if occurred >= recent_start:
                recent[pair] += 1
            elif occurred >= prior_start:
                prior[pair] += 1
        rising = [
            RisingPattern(location, category, recent[(location, category)],
                          prior.get((location, category), 0))
            for location, category in recent
            if recent[(location, category)] >= 2
            and recent[(location, category)] > prior.get((location, category), 0)
        ]
        rising.sort(key=lambda pattern: -(pattern.recent_count - pattern.prior_count))
        return rising

    # ------------------------------------------------------------------
    # Private extraction helpers
    # ------------------------------------------------------------------

    @classmethod
    def _severity_band(cls, incident: Incident) -> str | None:
        """Return the incident's severity band, or None when unusable.

        ``severity_score`` (the pipeline's raw 0-1 score) wins; a numeric
        legacy ``severity`` is banded with the same thresholds; a banded
        string passes through when it names a known band.
        """
        if incident.ai_section is None:
            return None
        ai = incident.ai_section.manager_json
        score = ai.get("severity_score")
        severity = ai.get("severity")
        value = score if isinstance(score, (int, float)) and not isinstance(score, bool) else severity
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value > 0.7:
                return "high"
            if value >= 0.4:
                return "medium"
            return "low"
        if isinstance(value, str) and value.strip().lower() in cls.SEVERITY_BANDS:
            return value.strip().lower()
        return None

    @staticmethod
    def _ai_field(incident: Incident, key: str):
        """Read a key from the AI section dictionary, tolerating a missing section."""
        if incident.ai_section is None:
            return None
        return incident.ai_section.manager_json.get(key)

    @staticmethod
    def _logic_field(incident: Incident, key: str):
        """Read a key from the logic section dictionary, tolerating a missing section."""
        if incident.logic_section is None:
            return None
        return incident.logic_section.manager_json.get(key)

    @staticmethod
    def _input_field(incident: Incident, key: str):
        """Read a key from the input section dictionary, tolerating a missing section."""
        if incident.input_section is None:
            return None
        return incident.input_section.manager_json.get(key)

    @staticmethod
    def _incident_date(incident: Incident) -> date | None:
        """Return the incident's occurrence date, or None when unparseable."""
        occurred = parse_incident_datetime(StatsService._input_field(incident, "incident_datetime"))
        return occurred.date() if occurred else None
