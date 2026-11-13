"""Dashboard routes as class-based views.

Every page is a ``MethodView`` subclass registered on the blueprint via
``as_view`` — the Flask object-oriented pattern: views are classes, routing
carries no decorators. The HTTP verb becomes a method name (``get``,
``post``, ...).
"""

from flask import Blueprint, render_template
from flask.views import MethodView

from dashboard.stats import StatsService

bp = Blueprint("dashboard", __name__)


class HomeView(MethodView):
    """Main dashboard page serving the incident trends analytics."""

    def get(self):
        import managers  # lazy: the shared manager singletons

        payload = StatsService(managers.data_manager).dashboard_payload()
        if payload["rising"]:
            managers.io_manager.notify(
                f"Warning: {len(payload['rising'])} rising hazard pattern(s) "
                "detected this week (possible incoming incidents).",
                category="warning",
            )
        return render_template("index.html", stats=payload,
                               total=payload["total"])


bp.add_url_rule("/", view_func=HomeView.as_view("home"))
