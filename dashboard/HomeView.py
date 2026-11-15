from dashboard.shared_imports import *
from dashboard.analytics.stats_service import StatsService
from flask import current_app
from data_manager import DataLoadError

class HomeView(MethodView):
    """Main dashboard page serving the incident trends analytics."""

    def get(self):
        import managers  

        try:
            payload = StatsService(managers.data_manager).dashboard_payload()
        except DataLoadError:
            current_app.logger.exception("Failed to load dashboard incidents")
            return render_template("index.html", total=0, stats={}, load_error=True), 500
        if payload["rising"]:
            managers.io_manager.notify(
                f"Warning: {len(payload['rising'])} rising hazard pattern(s) "
                "detected this week (possible incoming incidents).",
                category="warning",
            )
        return render_template("index.html", stats=payload,
                               total=payload["total"])