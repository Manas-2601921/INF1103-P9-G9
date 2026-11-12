"""The trends page: class-based view serving the analytics dashboard.

Like every page, the view is a ``MethodView`` subclass registered on the
shared blueprint via ``as_view`` — routing carries no decorators. The view
wires the shared ``managers.data_manager`` singleton into ``StatsService``
(dependency injection at the composition point) and serialises the
dataclass results into the JSON payload the Chart.js charts consume.
"""

from dataclasses import asdict

from flask import render_template
from flask.views import MethodView

from dashboard.routes import bp
from dashboard.stats import StatsService


class TrendsView(MethodView):
    """Render the trend statistics for repeated and incoming incidents."""

    def get(self):
        import managers  # lazy: the shared manager singletons

        service = StatsService(managers.data_manager)
        per_day = service.incidents_per_day()
        hotspots = service.recurrence_hotspots()
        rising = service.rising_patterns()
        payload = {
            "total": sum(service.incidents_by_severity().values()),
            "by_severity": service.incidents_by_severity(),
            "by_category": service.incidents_by_hazard_category(),
            "by_queue": service.incidents_by_queue(),
            "per_day": [asdict(point) for point in per_day],
            "hotspots": [asdict(hotspot) for hotspot in hotspots],
            "rising": [asdict(pattern) for pattern in rising],
        }
        return render_template("trends.html", stats=payload,
                               total=payload["total"])


bp.add_url_rule("/trends", view_func=TrendsView.as_view("trends"))
