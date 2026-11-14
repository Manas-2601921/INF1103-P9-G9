"""Trend statistics for the analytics dashboard, computed in Python.

``StatsService`` aggregates over the incidents the data manager loads —
no extra SQL: the storage layer stays query-shaped, the analytics layer
stays a pure aggregation service with the data manager injected. Every
method tolerates partial records (a missing AI section or an unparseable
datetime skips that incident from that statistic) so legacy rows and
manual-review stubs never crash the dashboard.
"""

from collections import defaultdict
from dataclasses import asdict
from datetime import date, timedelta

from dashboard.analytics.hotspot import Hotspot
from dashboard.analytics.incident_datetime_parser import IncidentDatetimeParser
from dashboard.analytics.rising_pattern import RisingPattern
from dashboard.analytics.trend_point import TrendPoint
from dashboard.incident import Incident


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
        self._datetime_parser = IncidentDatetimeParser()

    # ------------------------------------------------------------------
    # Distribution statistics
    # ------------------------------------------------------------------

    def incidents_by_severity(self) -> dict[str, int]:
        """Count incidents per severity band, all three bands always present."""
        return self._count_by_severity(self._data_manager.load())

    def incidents_by_hazard_category(self) -> dict[str, int]:
        """Count incidents per AI hazard category, highest count first."""
        return self._count_by_hazard_category(self._data_manager.load())

    def incidents_by_queue(self) -> dict[str, int]:
        """Count incidents per final triage queue, highest count first."""
        return self._count_by_queue(self._data_manager.load())

    # ------------------------------------------------------------------
    # Time-window statistics
    # ------------------------------------------------------------------

    def incidents_per_day(self, days: int = 14, today: date | None = None) -> list[TrendPoint]:
        """Count incidents for each of the last ``days`` days, zero-filled."""
        return self._count_per_day(self._data_manager.load(), days, today)

    def recurrence_hotspots(self, window_days: int = 30, min_count: int = 2,
                            today: date | None = None) -> list[Hotspot]:
        """Location + hazard pairs hit at least ``min_count`` times in the window."""
        return self._find_hotspots(self._data_manager.load(), window_days, min_count, today)

    def rising_patterns(self, recent_days: int = 7, today: date | None = None) -> list[RisingPattern]:
        """Location + hazard pairs whose last week outnumbers the prior week."""
        return self._find_rising_patterns(self._data_manager.load(), recent_days, today)

    def dashboard_payload(self, today: date | None = None) -> dict:
        """Compute all trend statistics from a single data-manager load."""
        incidents = self._data_manager.load()
        return {
            "total": len(incidents),
            "by_severity": self._count_by_severity(incidents),
            "by_category": self._count_by_hazard_category(incidents),
            "by_queue": self._count_by_queue(incidents),
            "per_day": [asdict(point) for point in self._count_per_day(incidents, 14, today)],
            "hotspots": [asdict(spot) for spot in self._find_hotspots(incidents, 30, 2, today)],
            "rising": [asdict(pattern) for pattern in self._find_rising_patterns(incidents, 7, today)],
        }

    # ------------------------------------------------------------------
    # Private aggregation helpers (operate on a single loaded snapshot)
    # ------------------------------------------------------------------

    def _count_by_severity(self, incidents: list[Incident]) -> dict[str, int]:
        counts = {band: 0 for band in self.SEVERITY_BANDS}
        for incident in incidents:
            band = self._severity_band(incident)
            if band is not None:
                counts[band] += 1
        return counts

    def _count_by_hazard_category(self, incidents: list[Incident]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for incident in incidents:
            category = self._section_field(incident.ai_section, "hazard_category")
            if category:
                counts[category] += 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def _count_by_queue(self, incidents: list[Incident]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for incident in incidents:
            queue = self._section_field(incident.logic_section, "final_queue")
            if queue:
                counts[queue] += 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def _count_per_day(self, incidents: list[Incident], days: int,
                       today: date | None) -> list[TrendPoint]:
        today = today or date.today()
        first_day = today - timedelta(days=days - 1)
        daily: dict[date, int] = {first_day + timedelta(days=i): 0 for i in range(days)}
        for incident in incidents:
            occurred = self._incident_date(incident)
            if occurred in daily:
                daily[occurred] += 1
        return [TrendPoint(day.isoformat(), daily[day]) for day in daily]

    def _find_hotspots(self, incidents: list[Incident], window_days: int,
                       min_count: int, today: date | None) -> list[Hotspot]:
        today = today or date.today()
        window_start = today - timedelta(days=window_days - 1)
        groups: dict[tuple[str, str], list[date]] = defaultdict(list)
        for incident in incidents:
            occurred = self._incident_date(incident)
            location = self._section_field(incident.input_section, "location")
            category = self._section_field(incident.ai_section, "hazard_category")
            if occurred and window_start <= occurred <= today and location and category:
                groups[(location, category)].append(occurred)
        hotspots = [
            Hotspot(location, category, len(dates), max(dates).isoformat())
            for (location, category), dates in groups.items()
            if len(dates) >= min_count
        ]
        hotspots.sort(key=lambda hotspot: (-hotspot.count, hotspot.last_seen))
        return hotspots

    def _find_rising_patterns(self, incidents: list[Incident], recent_days: int,
                              today: date | None) -> list[RisingPattern]:
        today = today or date.today()
        recent_start = today - timedelta(days=recent_days - 1)
        prior_start = recent_start - timedelta(days=recent_days)
        recent: dict[tuple[str, str], int] = defaultdict(int)
        prior: dict[tuple[str, str], int] = defaultdict(int)
        for incident in incidents:
            occurred = self._incident_date(incident)
            location = self._section_field(incident.input_section, "location")
            category = self._section_field(incident.ai_section, "hazard_category")
            if not (occurred and location and category) or occurred > today:
                continue
            pair = (location, category)
            if occurred >= recent_start:
                recent[pair] += 1
            elif occurred >= prior_start:
                prior[pair] += 1
        rising = []
        for (location, category), recent_count in recent.items():
            prior_count = prior.get((location, category), 0)
            if recent_count >= 2 and recent_count > prior_count:
                rising.append(RisingPattern(location, category, recent_count, prior_count))
        rising.sort(key=lambda pattern: -(pattern.recent_count - pattern.prior_count))
        return rising

    # ------------------------------------------------------------------
    # Private extraction helpers
    # ------------------------------------------------------------------

    def _severity_band(self, incident: Incident) -> str | None:
        """Return the incident's severity band, or None when unusable."""
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
        if isinstance(value, str) and value.strip().lower() in self.SEVERITY_BANDS:
            return value.strip().lower()
        return None

    def _section_field(self, section, key: str):
        """Read a key from a section's JSON payload, tolerating a missing section."""
        if section is None:
            return None
        return section.manager_json.get(key)

    def _incident_date(self, incident: Incident) -> date | None:
        """Return the incident's occurrence date, or None when unparseable."""
        raw_dt = self._section_field(incident.input_section, "incident_datetime")
        occurred = self._datetime_parser.parse(raw_dt)
        return occurred.date() if occurred else None
