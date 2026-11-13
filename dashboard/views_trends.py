"""The trends page: class-based view serving the analytics dashboard.

Like every page, the view is a ``MethodView`` subclass registered on the
shared blueprint via ``as_view`` — routing carries no decorators. The view
wires the shared ``managers.data_manager`` singleton into ``StatsService``
(dependency injection at the composition point) and renders the aggregated
payload for Chart.js.
"""

from flask import render_template
from flask.views import MethodView

from dashboard.routes import bp
from dashboard.stats import StatsService


class TrendsView(MethodView):
    """Render the trend statistics for repeated and incoming incidents."""

    def get(self):
        import managers  # lazy: the shared manager singletons

        payload = StatsService(managers.data_manager).dashboard_payload()
        return render_template("trends.html", stats=payload,
                               total=payload["total"])


bp.add_url_rule("/trends", view_func=TrendsView.as_view("trends"))
